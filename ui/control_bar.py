"""Recording control bar - Snipping Tool-style floating UI.

Appears above the selected region in READY state.
Switches layout for READY / RECORDING / PAUSED modes.

Layout reference (from Windows 11 Snipping Tool):
  READY:     [● スタート]  00:00:00  🎤  🖥  ✕
  RECORDING: ⏸  🔴  00:00:02  🎤  🖥  🗑
  PAUSED:    ▶  🔴  00:01:23  🎤  🖥  🗑
"""

import time
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw
from typing import Callable, Optional
import logging

from ui.theme import Colors, Fonts
from config import AppConfig
from i18n import t, available_languages, current_language

logger = logging.getLogger(__name__)

_BAR_WIDTH = 340
_BAR_HEIGHT = 42
_BAR_RADIUS = 14  # Moderately rounded — not pill, not sharp
_ICON_FONT = "Segoe MDL2 Assets"
_ICON_MIC = "\uE720"
_ICON_SPEAKER = "\uE767"
_ICON_CLOSE = "\uE711"
_ICON_DELETE = "\uE74D"
_ICON_PAUSE = "\uE769"
_ICON_PLAY = "\uE768"
_ICON_SIZE = 15


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
    """Floating control bar — the primary UI for InstaRec.

    Modes:
        idle      — [● Record]  🎤  🖥  ⋯
        ready     — [● Start]   00:00:00  🎤  🖥  ✕
        recording — ⏸  🔴  00:00:02  🎤  🖥  🗑
        paused    — ▶  🔴  00:01:23  🎤  🖥  🗑
    """

    def __init__(
        self,
        master,
        config: AppConfig,
        on_new: Optional[Callable] = None,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_pause: Optional[Callable] = None,
        on_resume: Optional[Callable] = None,
        on_discard: Optional[Callable] = None,
        on_mic_toggle: Optional[Callable[[bool], None]] = None,
        on_audio_toggle: Optional[Callable[[bool], None]] = None,
        on_mic_device_change: Optional[Callable[[Optional[str]], None]] = None,
        on_quit: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_language_change: Optional[Callable[[str], None]] = None,
        region: Optional[dict] = None,
    ):
        super().__init__(master)

        self._region = region
        self._config = config
        self._on_new = on_new
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_discard = on_discard
        self._on_mic_toggle = on_mic_toggle
        self._on_audio_toggle = on_audio_toggle
        self._on_mic_device_change = on_mic_device_change
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._on_language_change = on_language_change

        self._timer = _Timer()
        self._tick_id = None
        self._blink_id = None
        self._blink_visible = True
        self._mode = "idle"
        self._mic_on = config.microphone
        self._audio_on = config.system_audio

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        # Window setup
        self.title(t("control_bar.title"))
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
        self.set_mode("idle" if region is None else "ready")

        logger.info("ControlBar created")

    def update_region(self, region: dict):
        """Update the selection region and reposition."""
        self._region = region
        self._position_bar()

    def _position_bar(self):
        """Position the bar. If no region, center at top of screen."""
        r = self._region
        bar_w = _BAR_WIDTH
        bar_h = _BAR_HEIGHT

        if r is None:
            # Idle mode: top-center of screen
            screen_w = self.winfo_screenwidth()
            bar_x = (screen_w - bar_w) // 2
            bar_y = 50
            self.geometry(f"{bar_w}x{bar_h}+{bar_x}+{bar_y}")
            return

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
            inner, text=t("control.start"),
            image=rec_dot, compound="left",
            width=120, height=30, corner_radius=15,
            fg_color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER,
            text_color="#FFFFFF",
            font=(Fonts.FAMILY_JP, 13),
            command=self._handle_start,
        )
        self._rec_dot_img = rec_dot  # prevent GC

        # --- Pause/Resume button (RECORDING/PAUSED) --- MDL2 icon
        self._pause_btn = ctk.CTkButton(
            inner, text=_ICON_PAUSE, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=(_ICON_FONT, _ICON_SIZE),
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

        # --- Mic toggle (MDL2 icon, right-click for device selection) ---
        self._mic_btn = ctk.CTkButton(
            inner, text=_ICON_MIC, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            font=(_ICON_FONT, _ICON_SIZE),
            command=self._handle_mic_toggle,
        )
        self._mic_btn.bind("<Button-3>", self._show_mic_menu)

        # --- Speaker toggle (MDL2 icon) ---
        self._audio_btn = ctk.CTkButton(
            inner, text=_ICON_SPEAKER, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            font=(_ICON_FONT, _ICON_SIZE),
            command=self._handle_audio_toggle,
        )

        # --- Close button (READY) ---
        self._close_btn = ctk.CTkButton(
            inner, text=_ICON_CLOSE, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=(_ICON_FONT, _ICON_SIZE),
            command=self._handle_discard,
        )

        # --- Discard button (RECORDING/PAUSED) ---
        self._discard_btn = ctk.CTkButton(
            inner, text=_ICON_DELETE, width=28, height=28,
            corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=(_ICON_FONT, _ICON_SIZE),
            command=self._handle_discard,
        )

        # --- Record button (IDLE) --- ring style with inner dot
        rec_ring_img = self._make_ring_icon(30, Colors.RED, 12)
        self._rec_btn = ctk.CTkButton(
            inner, text="",
            image=rec_ring_img, compound="center",
            width=32, height=32, corner_radius=16,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            command=self._handle_new,
        )
        self._rec_ring_img = rec_ring_img

        # --- Menu button (IDLE) ---
        self._menu_btn = ctk.CTkButton(
            inner, text="\u22ef",
            font=(Fonts.FAMILY, 16),
            width=28, height=28, corner_radius=6,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            command=self._show_main_menu,
        )

        self._update_toggle_visuals()

    def set_mode(self, mode: str, start_timer: bool = True):
        """Switch bar layout: 'idle', 'ready', 'recording', 'paused'."""
        self._mode = mode

        for w in [
            self._rec_btn, self._menu_btn,
            self._start_btn, self._pause_btn, self._stop_btn,
            self._timer_label,
            self._mic_btn, self._audio_btn,
            self._close_btn, self._discard_btn,
        ]:
            w.pack_forget()

        sp = 4  # spacing between items

        if mode == "idle":
            self._rec_btn.pack(side="left", padx=(0, 8))
            self._mic_btn.pack(side="left", padx=sp)
            self._audio_btn.pack(side="left", padx=sp)
            self._menu_btn.pack(side="left", padx=(8, 0))
            self._stop_tick()
            self._stop_blink()

        elif mode == "ready":
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
            self._pause_btn.configure(text=_ICON_PAUSE, command=self._handle_pause_resume)
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

            if start_timer:
                if self._timer.elapsed() == 0:
                    self._timer.start()
                else:
                    self._timer.resume()
                self._start_tick()

        elif mode == "paused":
            self._pause_btn.configure(text=_ICON_PLAY, command=self._handle_pause_resume)
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
    def _make_ring_icon(size: int, ring_color: str, inner_size: int) -> ctk.CTkImage:
        """Create a ring icon with inner filled circle (record button style)."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Outer ring
        draw.ellipse((0, 0, size - 1, size - 1), outline=ring_color, width=2)
        # Inner dot
        pad = (size - inner_size) // 2
        draw.ellipse((pad, pad, pad + inner_size - 1, pad + inner_size - 1), fill=ring_color)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

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

    def _handle_new(self):
        if self._on_new:
            self._on_new()

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
    # Main menu (idle mode)
    # ------------------------------------------------------------------

    def _show_main_menu(self):
        """Show the main menu (settings, language, quit)."""
        menu = tk.Menu(self, tearoff=0, bg="#2A2A2A", fg="white",
                       activebackground="#3A3A3A", activeforeground="white",
                       relief="flat", borderwidth=0)

        # Language submenu
        langs = available_languages()
        cur = current_language()
        lang_menu = tk.Menu(menu, tearoff=0, bg="#2A2A2A", fg="white",
                            activebackground="#3A3A3A", activeforeground="white",
                            relief="flat", borderwidth=0)
        for code, name in langs.items():
            prefix = "\u2713 " if code == cur else "    "
            lang_menu.add_command(
                label=prefix + name,
                command=lambda c=code: self._change_language(c),
            )
        menu.add_cascade(label=t("menu.language"), menu=lang_menu)
        menu.add_command(label=t("menu.settings"), command=self._handle_settings)
        menu.add_separator()
        menu.add_command(label=t("menu.quit"), command=self._handle_quit)

        x = self._menu_btn.winfo_rootx()
        y = self._menu_btn.winfo_rooty() + self._menu_btn.winfo_height() + 4
        menu.post(x, y)

    def _change_language(self, lang_code: str):
        if self._on_language_change:
            self._on_language_change(lang_code)

    def _handle_settings(self):
        if self._on_settings:
            self._on_settings()

    def _handle_quit(self):
        if self._on_quit:
            self._on_quit()

    # ------------------------------------------------------------------
    # Mic device selection
    # ------------------------------------------------------------------

    def _show_mic_menu(self, event=None):
        """Show microphone device selection popup (right-click)."""
        from core.audio_capture import list_microphones

        devices = list_microphones()
        if not devices:
            return

        menu = tk.Menu(
            self, tearoff=0,
            bg=Colors.SURFACE_HOVER, fg=Colors.TEXT_PRIMARY,
            activebackground=Colors.SURFACE_PRESSED,
            activeforeground=Colors.TEXT_PRIMARY,
            relief="flat", borderwidth=1,
            font=(Fonts.FAMILY_JP, 11),
        )

        menu.add_command(
            label=t("mic.default_device"),
            command=lambda: self._select_mic_device(None),
        )
        menu.add_separator()

        for dev in devices:
            label = dev["name"][:40]
            did = dev["id"]
            menu.add_command(
                label=label,
                command=lambda d=did: self._select_mic_device(d),
            )

        x = self._mic_btn.winfo_rootx()
        y = self._mic_btn.winfo_rooty() + self._mic_btn.winfo_height() + 4
        menu.post(x, y)

    def _select_mic_device(self, device_id: str | None):
        if self._on_mic_device_change:
            self._on_mic_device_change(device_id)

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

    def set_enabled(self, enabled: bool):
        """Enable/disable the record button (idle mode)."""
        self._rec_btn.configure(
            state="normal" if enabled else "disabled",
            fg_color=Colors.RED if enabled else Colors.TEXT_TERTIARY,
        )

    def destroy(self):
        self._stop_tick()
        self._stop_blink()
        super().destroy()
        logger.info("ControlBar destroyed")
