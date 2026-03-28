"""Countdown overlay and recording border.

CountdownOverlay: Shows 3→2→1 countdown centered over selection area.
RecordingBorder: Red frame around selection during RECORDING/PAUSED.
"""

import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from typing import Callable, Optional
import logging
import os

from ui.theme import Colors, Fonts, RECORDING_BORDER_WIDTH

logger = logging.getLogger(__name__)

_CHROMA_KEY = "#010101"
_BADGE_W = 80
_BADGE_H = 80
_BADGE_RADIUS = 12
_BORDER_PAD = 10  # Padding around selection for countdown border


class CountdownOverlay:
    """Displays a 3→2→1 countdown badge with gray dashed border."""

    def __init__(
        self,
        master: tk.Tk,
        region: dict,
        seconds: int,
        on_complete: Callable[[], None],
    ):
        self._master = master
        self._region = region
        self._count = seconds
        self._on_complete = on_complete
        self._after_id = None
        self._win: Optional[tk.Toplevel] = None
        self._canvas: Optional[tk.Canvas] = None
        self._photo_img = None  # prevent GC
        self._destroyed = False

        self._font = self._load_font()

    @staticmethod
    def _load_font() -> ImageFont.FreeTypeFont:
        """Load bold font for countdown numbers."""
        try:
            # Windows Segoe UI Bold
            font_path = os.path.join(
                os.environ.get("WINDIR", r"C:\Windows"),
                "Fonts", "segoeuib.ttf"
            )
            return ImageFont.truetype(font_path, 60)
        except Exception:
            try:
                return ImageFont.truetype("arial.ttf", 60)
            except Exception:
                return ImageFont.load_default()

    def start(self):
        """Create the overlay and begin the countdown."""
        r = self._region
        pad = _BORDER_PAD

        win = tk.Toplevel(self._master)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=_CHROMA_KEY)

        try:
            win.attributes("-transparentcolor", _CHROMA_KEY)
        except Exception:
            pass

        cw = r["w"] + pad * 2
        ch = r["h"] + pad * 2
        win.geometry(f"{cw}x{ch}+{r['x'] - pad}+{r['y'] - pad}")

        canvas = tk.Canvas(
            win, bg=_CHROMA_KEY, highlightthickness=0,
            width=cw, height=ch,
        )
        canvas.pack(fill="both", expand=True)

        self._win = win
        self._canvas = canvas

        self._draw(self._count)
        self._schedule_tick()

        logger.info(f"Countdown started: {self._count}")

    def _draw(self, number: int):
        """Draw gray dashed border + countdown badge."""
        canvas = self._canvas
        if not canvas:
            return

        canvas.delete("all")
        r = self._region
        pad = _BORDER_PAD

        # Gray dashed border around selection
        canvas.create_rectangle(
            pad, pad, pad + r["w"], pad + r["h"],
            outline=Colors.COUNTDOWN_BORDER, dash=(6, 4), width=1,
        )

        # Countdown badge (PIL rendered)
        badge = self._render_badge(str(number))
        self._photo_img = ImageTk.PhotoImage(badge)

        cx = pad + r["w"] // 2
        cy = pad + r["h"] // 2
        canvas.create_image(cx, cy, image=self._photo_img, anchor="center")

    def _render_badge(self, text: str) -> Image.Image:
        """Render a dark rounded rectangle badge with white number."""
        img = Image.new("RGBA", (_BADGE_W, _BADGE_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark rounded rectangle
        draw.rounded_rectangle(
            (0, 0, _BADGE_W - 1, _BADGE_H - 1),
            radius=_BADGE_RADIUS,
            fill=Colors.COUNTDOWN_BADGE_BG,
        )

        # White number centered
        bbox = draw.textbbox((0, 0), text, font=self._font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (_BADGE_W - tw) // 2 - bbox[0]
        ty = (_BADGE_H - th) // 2 - bbox[1]
        draw.text((tx, ty), text, fill="#FFFFFF", font=self._font)

        return img

    def _schedule_tick(self):
        self._after_id = self._master.after(1000, self._tick)

    def _tick(self):
        if self._destroyed:
            return

        self._count -= 1
        if self._count > 0:
            self._draw(self._count)
            self._schedule_tick()
        else:
            # Countdown complete
            self.destroy()
            if self._on_complete:
                self._on_complete()

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True

        if self._after_id is not None:
            self._master.after_cancel(self._after_id)
            self._after_id = None

        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
            self._canvas = None
            self._photo_img = None

        logger.info("CountdownOverlay destroyed")


class RecordingBorder:
    """Red border frame around the selection during recording."""

    def __init__(self, master: tk.Tk, region: dict):
        self._master = master
        self._region = region
        self._panels: list[tk.Toplevel] = []

        bw = RECORDING_BORDER_WIDTH
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]

        # Top, Bottom, Left, Right strips
        positions = [
            (x - bw, y - bw, w + 2 * bw, bw),  # Top
            (x - bw, y + h, w + 2 * bw, bw),    # Bottom
            (x - bw, y, bw, h),                   # Left
            (x + w, y, bw, h),                    # Right
        ]

        for px, py, pw, ph in positions:
            panel = tk.Toplevel(master)
            panel.overrideredirect(True)
            panel.attributes("-topmost", True)
            panel.configure(bg=Colors.RECORDING_BORDER)
            panel.geometry(f"{pw}x{ph}+{px}+{py}")
            self._panels.append(panel)

        logger.info("RecordingBorder created")

    def show(self):
        for panel in self._panels:
            panel.deiconify()

    def hide(self):
        for panel in self._panels:
            panel.withdraw()

    def destroy(self):
        for panel in self._panels:
            try:
                panel.destroy()
            except Exception:
                pass
        self._panels.clear()
        logger.info("RecordingBorder destroyed")
