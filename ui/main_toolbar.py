"""Main toolbar - ultra-minimal, Apple HIG inspired.

Design reference: macOS Screenshot toolbar (Cmd+Shift+5)
- Frosted dark surface
- Icon-only buttons
- No text labels on the bar itself
- Compact pill shape
"""

import tkinter as tk
import customtkinter as ctk
from ui.theme import Colors, Fonts, TOOLBAR_HEIGHT, TOOLBAR_PADDING, CORNER_RADIUS
from ui.widgets import IconButton
import logging

logger = logging.getLogger(__name__)

# Toolbar width is compact: just the buttons + padding
_TOOLBAR_WIDTH = 120


class MainToolbar(ctk.CTkToplevel):
    """Floating pill-shaped toolbar.

    Layout:  [ ● (record) ]  [ ⋯ (menu) ]

    That's it. Two buttons. Maximum clarity.
    """

    def __init__(self, master, on_new=None, on_quit=None):
        super().__init__(master)

        self._on_new = on_new
        self._on_quit = on_quit

        # Window: frameless, always-on-top, dark surface
        self.title("InstaRec")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=Colors.SURFACE)

        # Try translucent window effect
        try:
            self.attributes("-alpha", 0.92)
        except Exception:
            pass

        # Position: top-center of screen
        screen_w = self.winfo_screenwidth()
        x = (screen_w - _TOOLBAR_WIDTH) // 2
        y = 50
        self.geometry(f"{_TOOLBAR_WIDTH}x{TOOLBAR_HEIGHT}+{x}+{y}")

        # Dark window style on Windows
        try:
            import pywinstyles
            pywinstyles.apply_style(self, "dark")
        except Exception:
            pass

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()

    def _build_ui(self):
        # Main container
        self._frame = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=CORNER_RADIUS,
        )
        self._frame.pack(fill="both", expand=True, padx=1, pady=1)
        self._frame.bind("<Button-1>", self._start_drag)
        self._frame.bind("<B1-Motion>", self._do_drag)

        # Center the buttons
        inner = ctk.CTkFrame(self._frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Record button: red circle
        self._rec_btn = ctk.CTkButton(
            inner,
            text="",
            width=24,
            height=24,
            corner_radius=12,
            fg_color=Colors.RED,
            hover_color=Colors.RED_HOVER,
            command=self._handle_new,
        )
        self._rec_btn.pack(side="left", padx=(0, 12))

        # Menu button: three dots
        self._menu_btn = IconButton(
            inner,
            text="⋯",
            font=(Fonts.FAMILY, 16),
            tooltip_text="メニュー",
            size=28,
            corner_radius=6,
            command=self._show_menu,
        )
        self._menu_btn.pack(side="left")

    def _handle_new(self):
        if self._on_new:
            self._on_new()

    def _show_menu(self):
        menu = tk.Menu(self, tearoff=0, bg="#2A2A2A", fg="white",
                       activebackground="#3A3A3A", activeforeground="white",
                       relief="flat", borderwidth=0)
        menu.add_command(label="終了", command=self._handle_quit)

        x = self._menu_btn.winfo_rootx()
        y = self._menu_btn.winfo_rooty() + self._menu_btn.winfo_height() + 4
        menu.post(x, y)

    def _handle_quit(self):
        if self._on_quit:
            self._on_quit()

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def set_enabled(self, enabled: bool):
        """Enable/disable the record button."""
        self._rec_btn.configure(
            state="normal" if enabled else "disabled",
            fg_color=Colors.RED if enabled else Colors.TEXT_TERTIARY,
        )
