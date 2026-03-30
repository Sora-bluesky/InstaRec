"""InstaRecApp - Top-level application controller."""

import os
import sys
import logging
import customtkinter as ctk
from state import StateMachine, AppState
from config import AppConfig
from core import Recorder
from ui.selection_overlay import SelectionOverlay
from ui.control_bar import ControlBar
from ui.recording_overlay import CountdownOverlay, RecordingBorder
from ui.preview_window import PreviewWindow
from ui.settings_window import SettingsWindow
from utils.logger import setup_logging
import i18n

logger = logging.getLogger(__name__)


class InstaRecApp(ctk.CTk):
    """Root application window (hidden). Manages state and UI components."""

    def __init__(self):
        super().__init__()

        # Setup
        setup_logging()
        logger.info("InstaRec starting")

        ctk.set_appearance_mode("dark")

        # Hide root window - ControlBar is the visible UI
        self.withdraw()
        self.protocol("WM_DELETE_WINDOW", self._on_quit)

        # Config & State
        self.config = AppConfig.load()

        # Initialize i18n (default: English, user can switch via menu)
        if not self.config.language:
            self.config.language = "en"
            self.config.save()
        i18n.init(self.config.language)

        self.state_machine = StateMachine()

        # Recording state
        self._selected_region = None
        self._overlay = None
        self._control_bar = None
        self._countdown_overlay = None
        self._recording_border = None
        self._recorder: Recorder | None = None
        self._preview_window: PreviewWindow | None = None
        self._mic_device_id: str | None = None

        # Register state callbacks
        self._register_state_callbacks()

        # Create control bar (primary UI)
        self._control_bar = self._create_control_bar()

        # Global hotkey
        self._setup_hotkey()

        logger.info("InstaRec ready (IDLE)")

    def _register_state_callbacks(self):
        sm = self.state_machine

        sm.on_enter(AppState.SELECTING, self._enter_selecting)
        sm.on_enter(AppState.IDLE, self._enter_idle)
        sm.on_enter(AppState.READY, self._enter_ready)
        sm.on_enter(AppState.COUNTDOWN, self._enter_countdown)
        sm.on_enter(AppState.RECORDING, self._enter_recording)
        sm.on_enter(AppState.PAUSED, self._enter_paused)
        sm.on_enter(AppState.PROCESSING, self._enter_processing)
        sm.on_enter(AppState.PREVIEW, self._enter_preview)

    def _create_control_bar(self, region=None) -> ControlBar:
        """Create or recreate the control bar."""
        return ControlBar(
            master=self,
            config=self.config,
            region=region,
            on_new=self._on_new,
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_pause=self._on_pause,
            on_resume=self._on_resume,
            on_discard=self._on_discard,
            on_mic_toggle=self._on_mic_toggle,
            on_audio_toggle=self._on_audio_toggle,
            on_mic_device_change=self._on_mic_device_change,
            on_quit=self._on_quit,
            on_settings=self._on_settings,
            on_language_change=self._on_language_change,
        )

    def _enter_idle(self, old_state, new_state):
        """Return to idle - show control bar, cleanup."""
        for attr in ("_countdown_overlay", "_recording_border", "_overlay"):
            obj = getattr(self, attr, None)
            if obj:
                obj.destroy()
                setattr(self, attr, None)

        if self._recorder:
            self._recorder.cleanup()
            self._recorder = None

        # Destroy recording control bar and recreate in idle mode
        if self._control_bar:
            self._control_bar.destroy()
        self._control_bar = self._create_control_bar()

        self._selected_region = None
        logger.info("Returned to IDLE")

    def _enter_selecting(self, old_state, new_state):
        """Start region selection overlay."""
        self._control_bar.set_enabled(False)
        self._control_bar.withdraw()

        self._overlay = SelectionOverlay(
            master=self,
            on_selection_drawn=self._on_selection_drawn,
            on_cancelled=self._on_selection_cancelled,
        )
        self._overlay.show()
        logger.info("Entering SELECTING")

    def _on_selection_drawn(self, region):
        """Called when user first draws a selection. Switch to ready mode."""
        self._selected_region = region
        self._control_bar.update_region(region)
        self._control_bar.set_mode("ready")
        self._control_bar.deiconify()
        logger.info(f"Selection drawn: {region}")

    def _on_selection_cancelled(self):
        """Called when user presses Escape."""
        self._overlay = None
        logger.info("Selection cancelled")
        self.state_machine.transition(AppState.IDLE)

    def _enter_ready(self, old_state, new_state):
        """Selection confirmed via Start button. Destroy overlay."""
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None
        logger.info(f"READY: region={self._selected_region}")

    def _enter_countdown(self, old_state, new_state):
        """Show 3→2→1 countdown, then transition to RECORDING."""
        if self._control_bar:
            self._control_bar.set_mode("recording", start_timer=False)

        self._countdown_overlay = CountdownOverlay(
            master=self,
            region=self._selected_region,
            seconds=self.config.countdown_seconds,
            on_complete=self._on_countdown_complete,
        )
        self._countdown_overlay.start()

        # Keep control bar above countdown overlay
        if self._control_bar:
            self._control_bar.lift()
        logger.info("COUNTDOWN started")

    def _on_countdown_complete(self):
        """Countdown finished. Start recording."""
        if self._countdown_overlay:
            self._countdown_overlay.destroy()
            self._countdown_overlay = None
        self.state_machine.transition(AppState.RECORDING)

    def _enter_recording(self, old_state, new_state):
        """Recording started or resumed."""
        if self._control_bar:
            self._control_bar.set_mode("recording")

        if not self._recording_border:
            self._recording_border = RecordingBorder(
                master=self,
                region=self._selected_region,
            )
        self._recording_border.show()

        # Keep control bar above recording border
        if self._control_bar:
            self._control_bar.lift()

        # Start or resume actual recording
        if old_state == AppState.COUNTDOWN:
            self._recorder = Recorder(
                region=self._selected_region,
                config=self.config,
                root=self,
                on_error=self._on_recording_error,
            )
            if self._mic_device_id:
                self._recorder.set_mic_device(self._mic_device_id)
            self._recorder.start()
        elif old_state == AppState.PAUSED and self._recorder:
            self._recorder.resume()

        logger.info("RECORDING")

    def _enter_paused(self, old_state, new_state):
        """Recording paused."""
        if self._control_bar:
            self._control_bar.set_mode("paused")
        if self._recorder:
            self._recorder.pause()
        logger.info("PAUSED")

    def _on_start(self):
        """Start button: confirm selection + begin countdown."""
        # Capture final selection from overlay
        if self._overlay:
            region = self._overlay.get_region()
            if region:
                self._selected_region = region
        # SELECTING → READY → COUNTDOWN
        self.state_machine.transition(AppState.READY)
        self.state_machine.transition(AppState.COUNTDOWN)

    def _on_stop(self):
        self.state_machine.transition(AppState.PROCESSING)

    def _on_pause(self):
        self.state_machine.transition(AppState.PAUSED)

    def _on_resume(self):
        self.state_machine.transition(AppState.RECORDING)

    def _on_discard(self):
        """Discard: stop recording, clean up, return to IDLE."""
        if self._recorder:
            self._recorder.cleanup()
            self._recorder = None
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None
        self.state_machine.transition(AppState.IDLE)

    def _on_mic_toggle(self, enabled: bool):
        self.config.microphone = enabled

    def _on_audio_toggle(self, enabled: bool):
        self.config.system_audio = enabled

    def _on_mic_device_change(self, device_id: str | None):
        self._mic_device_id = device_id
        if self._recorder:
            self._recorder.set_mic_device(device_id)

    def _on_recording_error(self, message: str):
        logger.error(f"Recording error: {message}")

    def _enter_processing(self, old_state, new_state):
        """Stop recording and finalize output."""
        if self._recorder:
            self._recorder.stop(on_complete=self._on_finalize_complete)
        else:
            # No recorder (shouldn't happen), go to IDLE via PREVIEW
            self.state_machine.transition(AppState.PREVIEW)
        logger.info("PROCESSING: finalizing recording...")

    def _on_finalize_complete(self, output_path: str | None):
        """Called on main thread when finalization completes."""
        if output_path:
            logger.info(f"Recording saved to: {output_path}")
            # Store for Phase 6 (preview window)
            self._last_output_path = output_path
        else:
            logger.error("Recording finalization failed")
        self.state_machine.transition(AppState.PREVIEW)

    def _enter_preview(self, old_state, new_state):
        """Show preview window with recorded video."""
        path = getattr(self, "_last_output_path", None)
        if path and os.path.exists(path):
            self._preview_window = PreviewWindow(
                master=self,
                video_path=path,
                on_close=self._on_preview_close,
            )
        else:
            logger.error("No video file for preview")
            self.state_machine.transition(AppState.IDLE)

    def _on_preview_close(self):
        """Called when preview window is closed."""
        self._preview_window = None
        self.state_machine.transition(AppState.IDLE)

    def _on_language_change(self, lang_code: str):
        """Handle language change from control bar menu."""
        self.config.language = lang_code
        self.config.save()
        i18n.init(lang_code)
        # Rebuild control bar with new language
        if self._control_bar:
            self._control_bar.destroy()
        self._control_bar = self._create_control_bar()
        logger.info(f"Language changed to: {lang_code}")

    def _on_settings(self):
        """Open settings window (single instance)."""
        if not self.state_machine.is_state(AppState.IDLE):
            return
        # Prevent multiple settings windows
        if hasattr(self, "_settings_window") and self._settings_window:
            try:
                self._settings_window.focus_force()
                return
            except Exception:
                pass
        self._settings_window = SettingsWindow(
            self, self.config,
            on_close=lambda: setattr(self, "_settings_window", None),
        )

    def _setup_hotkey(self):
        """Register global hotkey for recording."""
        try:
            import keyboard
            hotkey = self.config.hotkey
            keyboard.add_hotkey(hotkey, self._on_hotkey)
            logger.info(f"Global hotkey registered: {hotkey}")
        except Exception as e:
            logger.warning(f"Failed to register hotkey: {e}")

    def _on_hotkey(self):
        """Handle global hotkey press (runs on keyboard listener thread)."""
        # Schedule on main thread via after()
        self.after(0, self._hotkey_action)

    def _hotkey_action(self):
        """Execute hotkey action on main thread."""
        if self.state_machine.is_state(AppState.IDLE):
            self._on_new()
        elif self.state_machine.is_state(AppState.RECORDING):
            self._on_stop()

    def _on_new(self):
        """Handle 'New' button click."""
        self.state_machine.transition(AppState.SELECTING)

    def _on_quit(self):
        """Handle quit request."""
        logger.info("InstaRec shutting down")
        try:
            import keyboard
            keyboard.unhook_all()
        except Exception:
            pass
        self.config.save()
        if self._control_bar:
            self._control_bar.destroy()
        self.quit()
        sys.exit()

    def mainloop(self, *args, **kwargs):
        """Override to handle clean shutdown."""
        try:
            super().mainloop(*args, **kwargs)
        except KeyboardInterrupt:
            self._on_quit()
