"""Settings window with recording, audio, and behavior configuration.

Reads and writes AppConfig. Changes are saved immediately.
"""

import os
import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional
import logging

from ui.theme import Colors, Fonts
from config import AppConfig
from i18n import t

logger = logging.getLogger(__name__)

_ICON_FONT = "Segoe MDL2 Assets"
_ICON_CLOSE = "\uE711"
_ICON_SIZE = 15

_WIN_WIDTH = 500
_WIN_HEIGHT = 480


class SettingsWindow(ctk.CTkToplevel):
    """Settings panel with Recording / Audio / Behavior sections."""

    def __init__(
        self,
        master,
        config: AppConfig,
        on_close: Optional[Callable] = None,
    ):
        super().__init__(master)

        self._config = config
        self._on_close = on_close

        # Window setup
        self.title(t("settings.title"))
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=Colors.SURFACE)

        try:
            import pywinstyles
            pywinstyles.apply_style(self, "dark")
        except Exception:
            pass

        # Center on screen
        sx = self.winfo_screenwidth()
        sy = self.winfo_screenheight()
        self.geometry(f"{_WIN_WIDTH}x{_WIN_HEIGHT}+{(sx-_WIN_WIDTH)//2}+{(sy-_WIN_HEIGHT)//2}")

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()
        self.grab_set()
        self.focus_force()

    def _build_ui(self):
        # Title bar
        title_bar = ctk.CTkFrame(self, fg_color=Colors.SURFACE, height=44)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        title_bar.bind("<Button-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._do_drag)

        title_label = ctk.CTkLabel(
            title_bar, text=t("settings.title"),
            font=(Fonts.FAMILY_JP, 16, "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title_label.pack(side="left", padx=20)
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._do_drag)

        close_btn = ctk.CTkButton(
            title_bar, text=_ICON_CLOSE,
            font=(_ICON_FONT, _ICON_SIZE),
            width=28, height=28, corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            command=self._handle_close,
        )
        close_btn.pack(side="right", padx=12)

        # Separator
        ctk.CTkFrame(self, fg_color=Colors.SEPARATOR, height=1).pack(fill="x")

        # Scrollable content
        content = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
        )
        content.pack(fill="both", expand=True, padx=0, pady=0)

        # === RECORDING SECTION ===
        self._section_header(content, t("settings.recording"))

        # Save Location
        self._value_row(
            content, t("settings.save_location"),
            self._config.save_directory,
            self._browse_save_dir,
        )

        # Output Format
        self._dropdown_row(
            content, t("settings.output_format"),
            self._config.output_format,
            ["mp4"],
            self._on_format_change,
        )

        # Frame Rate
        self._dropdown_row(
            content, t("settings.frame_rate"),
            f"{self._config.fps} fps",
            ["15 fps", "24 fps", "30 fps", "60 fps"],
            self._on_fps_change,
        )

        # Countdown
        self._dropdown_row(
            content, t("settings.countdown"),
            f"{self._config.countdown_seconds} {t('settings.seconds')}",
            [f"{s} {t('settings.seconds')}" for s in [0, 1, 2, 3, 5]],
            self._on_countdown_change,
        )

        self._separator(content)

        # === AUDIO SECTION ===
        self._section_header(content, t("settings.audio"))

        self._sys_audio_switch = self._toggle_row(
            content, t("settings.system_audio"),
            self._config.system_audio,
            self._on_system_audio_toggle,
        )

        self._mic_switch = self._toggle_row(
            content, t("settings.microphone"),
            self._config.microphone,
            self._on_mic_toggle,
        )

        self._separator(content)

        # === BEHAVIOR SECTION ===
        self._section_header(content, t("settings.behavior"))

        self._auto_copy_switch = self._toggle_row(
            content, t("settings.auto_copy"),
            self._config.auto_copy,
            self._on_auto_copy_toggle,
        )

        self._auto_save_switch = self._toggle_row(
            content, t("settings.auto_save"),
            self._config.auto_save,
            self._on_auto_save_toggle,
        )

        # Hotkey
        self._value_row(
            content, t("settings.hotkey"),
            self._config.hotkey,
        )

    # ----------------------------------------------------------
    # UI Helpers
    # ----------------------------------------------------------

    def _section_header(self, parent, text):
        label = ctk.CTkLabel(
            parent, text=text,
            font=(Fonts.FAMILY_JP, 11, "bold"),
            text_color=Colors.TEXT_TERTIARY,
        )
        label.pack(anchor="w", padx=20, pady=(16, 4))

    def _separator(self, parent):
        ctk.CTkFrame(
            parent, fg_color=Colors.SEPARATOR, height=1,
        ).pack(fill="x", padx=20, pady=8)

    def _toggle_row(self, parent, label, initial, command):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=44)
        row.pack(fill="x", padx=20, pady=2)

        ctk.CTkLabel(
            row, text=label,
            font=(Fonts.FAMILY_JP, 13),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        switch = ctk.CTkSwitch(
            row, text="",
            width=44, height=24,
            fg_color=Colors.SEPARATOR,
            progress_color=Colors.ACCENT,
            button_color="#FFFFFF",
            command=lambda: command(switch.get()),
        )
        if initial:
            switch.select()
        switch.pack(side="right")

        return switch

    def _value_row(self, parent, label, value, on_click=None):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=44)
        row.pack(fill="x", padx=20, pady=2)

        ctk.CTkLabel(
            row, text=label,
            font=(Fonts.FAMILY_JP, 13),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        display = value if len(value) < 30 else "..." + value[-27:]
        btn = ctk.CTkButton(
            row, text=display,
            font=(Fonts.FAMILY, 12),
            fg_color=Colors.SURFACE_HOVER,
            hover_color=Colors.SURFACE_PRESSED,
            text_color=Colors.TEXT_PRIMARY,
            corner_radius=6, height=28,
            command=on_click if on_click else lambda: None,
        )
        btn.pack(side="right")
        return btn

    def _dropdown_row(self, parent, label, current, options, command):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=44)
        row.pack(fill="x", padx=20, pady=2)

        ctk.CTkLabel(
            row, text=label,
            font=(Fonts.FAMILY_JP, 13),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        dropdown = ctk.CTkOptionMenu(
            row, values=options,
            font=(Fonts.FAMILY, 12),
            fg_color=Colors.SURFACE_HOVER,
            button_color=Colors.SURFACE_PRESSED,
            button_hover_color=Colors.TEXT_TERTIARY,
            dropdown_fg_color=Colors.SURFACE_HOVER,
            dropdown_hover_color=Colors.SURFACE_PRESSED,
            text_color=Colors.TEXT_PRIMARY,
            width=140, height=28,
            corner_radius=6,
            command=command,
        )
        dropdown.set(current)
        dropdown.pack(side="right")

        return dropdown

    # ----------------------------------------------------------
    # Handlers
    # ----------------------------------------------------------

    def _browse_save_dir(self):
        folder = filedialog.askdirectory(
            initialdir=self._config.save_directory,
        )
        if folder:
            self._config.save_directory = folder
            self._save()

    def _on_format_change(self, value):
        self._config.output_format = value
        self._save()

    def _on_fps_change(self, value):
        try:
            fps = int(value.split()[0])
        except (ValueError, IndexError):
            fps = 30
        self._config.fps = fps
        self._save()

    def _on_countdown_change(self, value):
        try:
            seconds = int(value.split()[0])
        except (ValueError, IndexError):
            seconds = 3
        self._config.countdown_seconds = seconds
        self._save()

    def _on_system_audio_toggle(self, value):
        self._config.system_audio = bool(value)
        self._save()

    def _on_mic_toggle(self, value):
        self._config.microphone = bool(value)
        self._save()

    def _on_auto_copy_toggle(self, value):
        self._config.auto_copy = bool(value)
        self._save()

    def _on_auto_save_toggle(self, value):
        self._config.auto_save = bool(value)
        self._save()

    def _save(self):
        self._config.save()
        logger.info("Settings saved")

    # ----------------------------------------------------------
    # Drag & Cleanup
    # ----------------------------------------------------------

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _handle_close(self):
        self.grab_release()
        if self._on_close:
            self._on_close()
        self.destroy()
        logger.info("SettingsWindow closed")
