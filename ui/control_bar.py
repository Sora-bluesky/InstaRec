"""Recording control bar - Snipping Tool-style floating UI.

Appears above the selected region in READY state.
Switches layout for READY / RECORDING / PAUSED modes.

Layout reference (from Windows 11 Snipping Tool):
  READY:     [● スタート]  00:00:00  🎤  🖥  ✕
  RECORDING: ⏸  🔴  00:00:02  🎤  🖥  🗑
  PAUSED:    ▶  🔴  00:01:23  🎤  🖥  🗑
"""

import time
import customtkinter as ctk
from PIL import Image, ImageDraw
from typing import Callable
import logging

from ui.theme import Colors, Fonts
from config import AppConfig

logger = logging.getLogger(__name__)

_BAR_WIDTH = 360
_BAR_HEIGHT = 36
_BAR_RADIUS = 8
_ICON_FONT = "Segoe MDL2 Assets"
_ICON_MIC = "\uE720"
_ICON_SPEAKER = "\uE767"
_ICON_CLOSE = "\uE711"
_ICON_DELETE = "\uE74D"


class _Timer:
    """Elapsed time tracker using time.perf_counter()."""

    def __init__(self):
        self._start_time = 0.0
        self._pause_offset = 0.0
        self._running = False

    def start(self):
        self._start_time = time.perf_counter()
        self._pause_offset = 0.0
        self._running = True

    def pause(self):
        if self._running:
            self._pause_offset += time.perf_counter() - self._start_time
            self._running = False

    def resume(self):
        if not self._running:
            self._start_time = time.perf_counter()
            self._running = True

    def elapsed(self) -> float:
        if self._running:
            return self._pause_offset + (time.perf_counter() - self._start_time)
        return self._pause_offset

    def formatted(self) -> str:
        total = int(self.elapsed())
        h, r = divmod(total, 3600)
        m, s = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def reset(self):
        self._start_time = 0.0
        self._pause_offset = 0.0
        self._running = False


class ControlBar(ctk.CTkToplevel):
    """Floating control bar for recording operations."""

    def __init__(
        self,
        master,
        region: dict,
        config: AppConfig,
        on_start: Callable,
        on_stop: Callable,
        on_pause: Callable,
        on_resume: Callable,
        on_discard: Callable,
        on_mic_toggle: Callable[[bool], None],
        on_audio_toggle: Callable[[bool], None],
    ):
        super().__init__(master)

        self._region = region
        self._config = config
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_discard = on_discard
        self._on_mic_toggle = on_mic_toggle
        self._on_audio_toggle = on_audio_toggle

        self._timer = _Timer()
        self._tick_id = None
        self._blink_id = None
        self._blink_visible = True
        self._mode = "ready"
        self._mic_on = config.microphone
        self._audio_on = config.system_audio

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        # Window setup
        self.title("InstaRec Control")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=Colors.SURFACE)

        try:
            self.attributes("-alpha", 0.92)
        except Exception:
            pass

        try:
            import pywinstyles
            pywinstyles.apply_style(self, "dark")
        except Exception:
            pass

        self._build_ui()
        self._position_bar()
        self.set_mode("ready")

        logger.info("ControlBar created")

    def _position_bar(self):
        """Position the bar centered above the selection region."""
        r = self._region
        bar_w = _BAR_WIDTH
        bar_h = _BAR_HEIGHT

        bar_x = r["x"] + (r["w"] - bar_w) // 2
        bar_y = r["y"] - bar_h - 8

        if bar_y < 0:
            bar_y = r["y"] + r["h"] + 8

        screen_w = self.winfo_screenwidth()
        bar_x = max(0, min(bar_x, screen_w - bar_w))

        self.geometry(f"{bar_w}x{bar_h}+{bar_x}+{bar_y}")

    def _build_ui(self):
        """Build all UI elements matching Snipping Tool layout."""
        # Main container
        self._frame = ctk.CTkFrame(
            self, fg_color=Colors.SURFACE, corner_radius=_BAR_RADIUS,
        )
        self._frame.pack(fill="both", expand=True, padx=2, pady=2)
        self._frame.bind("<Button-1>", self._start_drag)
        self._frame.bind("<B1-Motion>", self._do_drag)

        inner = ctk.CTkFrame(self._frame, fg_color="transparent")
        inner.pack(expand=True, padx=10, pady=0)

        # --- Start button (READY) --- Windows blue pill with circle icon
        rec_dot = self._make_circle_icon(10, "#FFFFFF")
        self._start_btn = ctk.CTkButton(
            inner, text="\u30b9\u30bf\u30fc\u30c8",
            image=rec_dot, compound="left",
            width=120, height=30, corner_radius=15,
            fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
            text_color="#FFFFFF",
            font=(Fonts.FAMILY_JP, 13),
            command=self._handle_start,
        )
        self._rec_dot_img = rec_dot  # prevent GC

        # --- Pause/Resume button (RECORDING/PAUSED) --- flat icon
        self._pause_btn = ctk.CTkButton(
            inner, text="\u23f8", width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=(Fonts.FAMILY, 15),
            command=self._handle_pause_resume,
        )

        # --- Stop button (RECORDING/PAUSED) --- red circle ●
        self._stop_btn = ctk.CTkButton(
            inner, text="\u25cf", width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.RED,
            font=(Fonts.FAMILY, 18),
            command=self._handle_stop,
        )

        # --- Timer ---
        self._timer_label = ctk.CTkLabel(
            inner, text="00:00:00",
            font=(Fonts.FAMILY, 13),
            text_color=Colors.TEXT_SECONDARY, width=65,
        )

        # --- Mic toggle (MDL2 icon) ---
        self._mic_btn = ctk.CTkButton(
            inner, text=_ICON_MIC, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            font=(_ICON_FONT, 13),
            command=self._handle_mic_toggle,
        )

        # --- Speaker toggle (MDL2 icon) ---
        self._audio_btn = ctk.CTkButton(
            inner, text=_ICON_SPEAKER, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            font=(_ICON_FONT, 13),
            command=self._handle_audio_toggle,
        )

        # --- Close button (READY) ---
        self._close_btn = ctk.CTkButton(
            inner, text=_ICON_CLOSE, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            font=(_ICON_FONT, 12),
            command=self._handle_discard,
        )

        # --- Discard button (RECORDING/PAUSED) ---
        self._discard_btn = ctk.CTkButton(
            inner, text=_ICON_DELETE, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            font=(_ICON_FONT, 13),
            command=self._handle_discard,
        )

        self._update_toggle_visuals()

    def set_mode(self, mode: str):
        """Switch bar layout: 'ready', 'recording', 'paused'."""
        self._mode = mode

        for w in [
            self._start_btn, self._pause_btn, self._stop_btn,
            self._timer_label,
            self._mic_btn, self._audio_btn,
            self._close_btn, self._discard_btn,
        ]:
            w.pack_forget()

        sp = 4  # spacing between items

        if mode == "ready":
            self._start_btn.pack(side="left", padx=(0, sp * 2))
            self._timer_label.configure(text_color=Colors.TEXT_SECONDARY)
            self._timer_label.pack(side="left", padx=(0, sp * 2))
            self._mic_btn.pack(side="left", padx=sp)
            self._audio_btn.pack(side="left", padx=sp)
            self._close_btn.pack(side="left", padx=(sp, 0))

            self._stop_tick()
            self._stop_blink()
            self._timer.reset()
            self._timer_label.configure(text="00:00:00")

        elif mode == "recording":
            self._pause_btn.configure(text="\u23f8", command=self._handle_pause_resume)
            self._pause_btn.pack(side="left", padx=sp)
            self._stop_btn.pack(side="left", padx=sp)
            self._timer_label.configure(text_color=Colors.TEXT_PRIMARY)
            self._timer_label.pack(side="left", padx=(sp, sp * 2))
            self._mic_btn.pack(side="left", padx=sp)
            self._audio_btn.pack(side="left", padx=sp)
            self._discard_btn.pack(side="left", padx=(sp, 0))

            self._stop_blink()
            self._blink_visible = True
            self._timer_label.configure(text=self._timer.formatted())

            if self._timer.elapsed() == 0:
                self._timer.start()
            else:
                self._timer.resume()
            self._start_tick()

        elif mode == "paused":
            self._pause_btn.configure(text="\u25b6", command=self._handle_pause_resume)
            self._pause_btn.pack(side="left", padx=sp)
            self._stop_btn.pack(side="left", padx=sp)
            self._timer_label.configure(text_color=Colors.TEXT_PRIMARY)
            self._timer_label.pack(side="left", padx=(sp, sp * 2))
            self._mic_btn.pack(side="left", padx=sp)
            self._audio_btn.pack(side="left", padx=sp)
            self._discard_btn.pack(side="left", padx=(sp, 0))

            self._timer.pause()
            self._stop_tick()
            self._start_blink()

    # ------------------------------------------------------------------
    # Timer tick / blink
    # ------------------------------------------------------------------

    def _start_tick(self):
        self._stop_tick()
        self._do_tick()

    def _do_tick(self):
        if self._mode == "recording":
            self._timer_label.configure(text=self._timer.formatted())
            self._tick_id = self.after(100, self._do_tick)

    def _stop_tick(self):
        if self._tick_id is not None:
            self.after_cancel(self._tick_id)
            self._tick_id = None

    def _start_blink(self):
        self._stop_blink()
        self._blink_visible = True
        self._do_blink()

    def _do_blink(self):
        if self._mode == "paused":
            self._blink_visible = not self._blink_visible
            color = Colors.TEXT_PRIMARY if self._blink_visible else Colors.SURFACE
            self._timer_label.configure(text_color=color)
            self._blink_id = self.after(500, self._do_blink)

    def _stop_blink(self):
        if self._blink_id is not None:
            self.after_cancel(self._blink_id)
            self._blink_id = None

    # ------------------------------------------------------------------
    # Toggle visuals
    # ------------------------------------------------------------------

    def _update_toggle_visuals(self):
        self._mic_btn.configure(
            text_color=Colors.TEXT_PRIMARY if self._mic_on else Colors.TEXT_TERTIARY,
        )
        self._audio_btn.configure(
            text_color=Colors.TEXT_PRIMARY if self._audio_on else Colors.TEXT_TERTIARY,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_circle_icon(size: int, color: str) -> ctk.CTkImage:
        """Create a small filled circle icon."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, size - 1, size - 1), fill=color)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _handle_start(self):
        if self._on_start:
            self._on_start()

    def _handle_stop(self):
        if self._on_stop:
            self._on_stop()

    def _handle_pause_resume(self):
        if self._mode == "recording" and self._on_pause:
            self._on_pause()
        elif self._mode == "paused" and self._on_resume:
            self._on_resume()

    def _handle_discard(self):
        if self._on_discard:
            self._on_discard()

    def _handle_mic_toggle(self):
        self._mic_on = not self._mic_on
        self._update_toggle_visuals()
        if self._on_mic_toggle:
            self._on_mic_toggle(self._mic_on)

    def _handle_audio_toggle(self):
        self._audio_on = not self._audio_on
        self._update_toggle_visuals()
        if self._on_audio_toggle:
            self._on_audio_toggle(self._audio_on)

    # ------------------------------------------------------------------
    # Drag
    # ------------------------------------------------------------------

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def destroy(self):
        self._stop_tick()
        self._stop_blink()
        super().destroy()
        logger.info("ControlBar destroyed")
