"""InstaRecApp - Top-level application controller."""

import sys
import logging
import customtkinter as ctk
from state import StateMachine, AppState
from config import AppConfig
from ui.main_toolbar import MainToolbar
from ui.selection_overlay import SelectionOverlay
from ui.control_bar import ControlBar
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


class InstaRecApp(ctk.CTk):
    """Root application window (hidden). Manages state and UI components."""

    def __init__(self):
        super().__init__()

        # Setup
        setup_logging()
        logger.info("InstaRec starting")

        ctk.set_appearance_mode("dark")

        # Hide root window - MainToolbar is the visible UI
        self.withdraw()

        # Config & State
        self.config = AppConfig.load()
        self.state_machine = StateMachine()

        # Recording state
        self._selected_region = None
        self._overlay = None
        self._control_bar = None

        # Register state callbacks
        self._register_state_callbacks()

        # Create main toolbar
        self.toolbar = MainToolbar(
            self,
            on_new=self._on_new,
            on_quit=self._on_quit,
        )

        logger.info("InstaRec ready (IDLE)")

    def _register_state_callbacks(self):
        sm = self.state_machine

        sm.on_enter(AppState.SELECTING, self._enter_selecting)
        sm.on_enter(AppState.IDLE, self._enter_idle)
        sm.on_enter(AppState.READY, self._enter_ready)
        sm.on_enter(AppState.COUNTDOWN, self._enter_countdown)
        sm.on_enter(AppState.RECORDING, self._enter_recording)
        sm.on_enter(AppState.PAUSED, self._enter_paused)

    def _enter_idle(self, old_state, new_state):
        """Return to idle - show toolbar, cleanup."""
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None
        if self._control_bar:
            self._control_bar.destroy()
            self._control_bar = None

        self.toolbar.set_enabled(True)
        self.toolbar.deiconify()
        self._selected_region = None
        logger.info("Returned to IDLE")

    def _enter_selecting(self, old_state, new_state):
        """Start region selection overlay."""
        self.toolbar.set_enabled(False)
        self.toolbar.withdraw()

        self._overlay = SelectionOverlay(
            master=self,
            on_selection_drawn=self._on_selection_drawn,
            on_cancelled=self._on_selection_cancelled,
        )
        self._overlay.show()
        logger.info("Entering SELECTING")

    def _on_selection_drawn(self, region):
        """Called when user first draws a selection. Show control bar."""
        self._selected_region = region
        if not self._control_bar:
            self._control_bar = ControlBar(
                master=self,
                region=region,
                config=self.config,
                on_start=self._on_start,
                on_stop=self._on_stop,
                on_pause=self._on_pause,
                on_resume=self._on_resume,
                on_discard=self._on_discard,
                on_mic_toggle=self._on_mic_toggle,
                on_audio_toggle=self._on_audio_toggle,
            )
        logger.info(f"Selection drawn, control bar shown: {region}")

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
        """Countdown before recording. Phase 4 placeholder."""
        self.after(100, lambda: self.state_machine.transition(AppState.RECORDING))

    def _enter_recording(self, old_state, new_state):
        """Recording started or resumed."""
        if self._control_bar:
            self._control_bar.set_mode("recording")
        logger.info("RECORDING")

    def _enter_paused(self, old_state, new_state):
        """Recording paused."""
        if self._control_bar:
            self._control_bar.set_mode("paused")
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
        self.state_machine.transition(AppState.IDLE)

    def _on_pause(self):
        self.state_machine.transition(AppState.PAUSED)

    def _on_resume(self):
        self.state_machine.transition(AppState.RECORDING)

    def _on_discard(self):
        """Discard: clean up and return to IDLE from any state."""
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None
        self.state_machine.transition(AppState.IDLE)

    def _on_mic_toggle(self, enabled: bool):
        self.config.microphone = enabled

    def _on_audio_toggle(self, enabled: bool):
        self.config.system_audio = enabled

    def _on_new(self):
        """Handle 'New' button click."""
        self.state_machine.transition(AppState.SELECTING)

    def _on_quit(self):
        """Handle quit request."""
        logger.info("InstaRec shutting down")
        self.config.save()
        self.toolbar.destroy()
        self.quit()
        sys.exit()

    def mainloop(self, *args, **kwargs):
        """Override to handle clean shutdown."""
        try:
            super().mainloop(*args, **kwargs)
        except KeyboardInterrupt:
            self._on_quit()
