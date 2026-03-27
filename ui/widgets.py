"""Minimal reusable widgets following Apple HIG principles.

- Icons over text labels
- Generous touch targets
- Subtle hover feedback
"""

import customtkinter as ctk
from PIL import Image
import os
import sys
from ui.theme import Colors, Fonts, BUTTON_SIZE, ICON_SIZE


def get_asset_path(relative_path: str) -> str:
    """Resolve asset path for both dev and PyInstaller environments."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), relative_path
    )


class IconButton(ctk.CTkButton):
    """Minimal icon button with optional tooltip.

    Apple HIG: Controls should be clear and self-explanatory.
    Hover states are subtle - just a gentle background shift.
    """

    def __init__(
        self,
        master,
        icon_name: str = None,
        icon_size: tuple = (ICON_SIZE, ICON_SIZE),
        tooltip_text: str = None,
        size: int = BUTTON_SIZE,
        **kwargs,
    ):
        kwargs.setdefault("width", size)
        kwargs.setdefault("height", size)
        kwargs.setdefault("corner_radius", size // 2)
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", Colors.SURFACE_HOVER)
        kwargs.setdefault("text_color", Colors.TEXT_PRIMARY)
        kwargs.setdefault("font", (Fonts.FAMILY, Fonts.BODY))
        kwargs.setdefault("text", "")

        # Load icon if available
        if icon_name:
            icon_path = get_asset_path(f"assets/icons/{icon_name}.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                kwargs["image"] = ctk.CTkImage(
                    light_image=image, dark_image=image, size=icon_size
                )

        super().__init__(master, **kwargs)

        self._tooltip_text = tooltip_text
        self._tooltip_window = None
        self._tooltip_after_id = None
        if tooltip_text:
            self.bind("<Enter>", self._schedule_tooltip)
            self.bind("<Leave>", self._hide_tooltip)

    def _schedule_tooltip(self, event):
        """Show tooltip after a brief delay (Apple-style)."""
        self._tooltip_after_id = self.after(600, self._show_tooltip)

    def _show_tooltip(self):
        if self._tooltip_window or not self._tooltip_text:
            return
        x = self.winfo_rootx() + self.winfo_width() // 2
        y = self.winfo_rooty() + self.winfo_height() + 6

        self._tooltip_window = tw = ctk.CTkToplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.configure(fg_color=Colors.SURFACE)

        label = ctk.CTkLabel(
            tw,
            text=self._tooltip_text,
            font=(Fonts.FAMILY, Fonts.CAPTION),
            text_color=Colors.TEXT_SECONDARY,
            fg_color=Colors.SURFACE,
            corner_radius=4,
            padx=8,
            pady=3,
        )
        label.pack()

        # Center tooltip under button
        tw.update_idletasks()
        tw_width = tw.winfo_width()
        tw.geometry(f"+{x - tw_width // 2}+{y}")

    def _hide_tooltip(self, event):
        if self._tooltip_after_id:
            self.after_cancel(self._tooltip_after_id)
            self._tooltip_after_id = None
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None
