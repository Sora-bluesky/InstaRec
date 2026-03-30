"""Selection overlay for drawing and adjusting the recording region.

Two-phase approach:
  Phase A (Draw): Full-screen dim overlay. User drags to draw a rectangle.
  Phase B (Adjust): 4 dim panels around selection + border overlay with
                    resize handles. User can move, resize, confirm, or cancel.
"""

import tkinter as tk
from typing import Callable, Optional
import logging

from ui.theme import Colors, OVERLAY_ALPHA, HANDLE_SIZE
from utils.monitors import get_screen_metrics

logger = logging.getLogger(__name__)

MIN_SELECTION_SIZE = 10
_HIT_PADDING = 20  # Interaction area extends this far beyond the selection edges

# Which edges each handle controls: (x_key, y_key)
_RESIZE_EDGES = {
    "nw": ("x1", "y1"), "n": (None, "y1"), "ne": ("x2", "y1"),
    "w":  ("x1", None),                     "e":  ("x2", None),
    "sw": ("x1", "y2"), "s": (None, "y2"), "se": ("x2", "y2"),
}

_HANDLE_CURSORS = {
    "nw": "size_nw_se", "n": "size_ns",    "ne": "size_ne_sw",
    "w":  "size_we",                        "e":  "size_we",
    "sw": "size_ne_sw", "s": "size_ns",    "se": "size_nw_se",
}

# Color used for -transparentcolor on Windows
_CHROMA_KEY = "#010101"


class SelectionOverlay:
    """Manages the selection overlay windows and user interaction."""

    def __init__(
        self,
        master: tk.Tk,
        on_selection_drawn: Callable[[dict], None],
        on_cancelled: Callable[[], None],
    ):
        self._master = master
        self._on_selection_drawn = on_selection_drawn
        self._on_cancelled = on_cancelled

        self._screen: dict = {}
        self._selection: Optional[dict] = None  # {x1, y1, x2, y2}

        # Drag state
        self._drag_mode = "none"  # "draw", "move", "resize_xx"
        self._drag_start = (0, 0)
        self._drag_sel_start: Optional[dict] = None

        # Windows
        self._draw_overlay: Optional[tk.Toplevel] = None
        self._draw_canvas: Optional[tk.Canvas] = None
        self._dim_panels: list[tk.Toplevel] = []
        self._border_win: Optional[tk.Toplevel] = None
        self._border_canvas: Optional[tk.Canvas] = None
        self._interact_win: Optional[tk.Toplevel] = None

        self._destroyed = False

    def show(self):
        """Show the overlay and enter draw mode (Phase A)."""
        self._screen = get_screen_metrics()
        logger.info(f"Selection overlay: screen={self._screen}")
        self._create_draw_overlay()

    def get_region(self) -> Optional[dict]:
        """Return current selection as {x, y, w, h}, or None."""
        s = self._selection
        if s is None:
            return None
        w = s["x2"] - s["x1"]
        h = s["y2"] - s["y1"]
        if w < MIN_SELECTION_SIZE or h < MIN_SELECTION_SIZE:
            return None
        return {"x": s["x1"], "y": s["y1"], "w": w, "h": h}

    def destroy(self):
        """Tear down all overlay windows."""
        if self._destroyed:
            return
        self._destroyed = True

        for win in [self._draw_overlay, self._border_win, self._interact_win]:
            if win:
                try:
                    win.destroy()
                except Exception:
                    pass

        for panel in self._dim_panels:
            try:
                panel.destroy()
            except Exception:
                pass

        self._draw_overlay = None
        self._draw_canvas = None
        self._border_win = None
        self._border_canvas = None
        self._interact_win = None
        self._dim_panels.clear()
        logger.info("Selection overlay destroyed")

    # ------------------------------------------------------------------
    # Phase A: Draw mode
    # ------------------------------------------------------------------

    def _create_draw_overlay(self):
        """Create a full-screen dim overlay for drawing the initial selection."""
        scr = self._screen
        win = tk.Toplevel(self._master)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", OVERLAY_ALPHA)
        win.configure(bg=Colors.OVERLAY_DIM)
        win.geometry(
            f"{scr['width']}x{scr['height']}+{scr['left']}+{scr['top']}"
        )

        canvas = tk.Canvas(
            win, bg=Colors.OVERLAY_DIM,
            highlightthickness=0, cursor="tcross",
        )
        canvas.pack(fill="both", expand=True)

        canvas.bind("<Button-1>", self._draw_on_press)
        canvas.bind("<B1-Motion>", self._draw_on_drag)
        canvas.bind("<ButtonRelease-1>", self._draw_on_release)
        win.bind("<Escape>", self._on_escape)

        win.focus_force()
        self._draw_overlay = win
        self._draw_canvas = canvas
        logger.info("Phase A: draw overlay created")

    def _draw_on_press(self, event):
        self._drag_mode = "draw"
        self._drag_start = (event.x_root, event.y_root)

    def _draw_on_drag(self, event):
        if self._drag_mode != "draw":
            return
        sx, sy = self._drag_start
        ex, ey = event.x_root, event.y_root

        # Convert to canvas coordinates
        scr = self._screen
        cx1 = sx - scr["left"]
        cy1 = sy - scr["top"]
        cx2 = ex - scr["left"]
        cy2 = ey - scr["top"]

        canvas = self._draw_canvas
        canvas.delete("sel_rect")
        canvas.create_rectangle(
            cx1, cy1, cx2, cy2,
            outline=Colors.SELECTION_BORDER, dash=(6, 4), width=2,
            tags="sel_rect",
        )

    def _draw_on_release(self, event):
        if self._drag_mode != "draw":
            return
        self._drag_mode = "none"

        sx, sy = self._drag_start
        ex, ey = event.x_root, event.y_root

        x1, x2 = min(sx, ex), max(sx, ex)
        y1, y2 = min(sy, ey), max(sy, ey)

        if (x2 - x1) < MIN_SELECTION_SIZE or (y2 - y1) < MIN_SELECTION_SIZE:
            logger.debug("Selection too small, ignoring")
            return

        self._selection = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        logger.info(f"Selection drawn: {self._selection}")
        self._transition_to_adjust()

        # Notify app so control bar can appear
        region = self.get_region()
        if region and self._on_selection_drawn:
            self._on_selection_drawn(region)

    def _transition_to_adjust(self):
        """Destroy draw overlay, create Phase B adjust windows."""
        if self._draw_overlay:
            self._draw_overlay.destroy()
            self._draw_overlay = None
            self._draw_canvas = None

        self._create_dim_panels()
        self._create_adjust_overlays()

    # ------------------------------------------------------------------
    # Phase B: Adjust mode
    # ------------------------------------------------------------------

    def _create_dim_panels(self):
        """Create 4 dim panels around the selection."""
        for _ in range(4):
            panel = tk.Toplevel(self._master)
            panel.overrideredirect(True)
            panel.attributes("-topmost", True)
            panel.attributes("-alpha", OVERLAY_ALPHA)
            panel.configure(bg=Colors.OVERLAY_DIM)

            panel.bind("<Button-1>", self._dim_on_press)
            panel.bind("<B1-Motion>", self._dim_on_drag)
            panel.bind("<ButtonRelease-1>", self._dim_on_release)
            panel.bind("<Escape>", self._on_escape)

            self._dim_panels.append(panel)

        self._update_dim_panels()

    def _update_dim_panels(self):
        """Reposition the 4 dim panels around the current selection."""
        s = self._selection
        scr = self._screen
        sl, st = scr["left"], scr["top"]
        sr = sl + scr["width"]
        sb = st + scr["height"]

        if s is None:
            self._set_panel_geom(0, sl, st, sr - sl, sb - st)
            for i in range(1, 4):
                self._set_panel_geom(i, 0, 0, 0, 0)
            return

        x1, y1, x2, y2 = s["x1"], s["y1"], s["x2"], s["y2"]

        # Top: full width, above selection
        self._set_panel_geom(0, sl, st, sr - sl, max(0, y1 - st))
        # Bottom: full width, below selection
        self._set_panel_geom(1, sl, y2, sr - sl, max(0, sb - y2))
        # Left: selection height, left of selection
        self._set_panel_geom(2, sl, y1, max(0, x1 - sl), max(0, y2 - y1))
        # Right: selection height, right of selection
        self._set_panel_geom(3, x2, y1, max(0, sr - x2), max(0, y2 - y1))

        # Ensure overlays stay above dim panels
        self._ensure_z_order()

    def _set_panel_geom(self, index: int, x: int, y: int, w: int, h: int):
        panel = self._dim_panels[index]
        if w <= 0 or h <= 0:
            panel.withdraw()
        else:
            panel.deiconify()
            panel.geometry(f"{w}x{h}+{x}+{y}")

    def _create_adjust_overlays(self):
        """Create the border overlay and interaction panel over the selection.

        Layer stack (front to back):
          interact_win  -- alpha=0.01, covers selection+handle padding, all events
          border_win    -- -transparentcolor, visual only (border + handles)
          dim_panels    -- alpha=0.4, darkening around selection
        """
        s = self._selection
        if s is None:
            return

        w = s["x2"] - s["x1"]
        h = s["y2"] - s["y1"]
        pad = _HIT_PADDING  # Large padding so handles are easy to grab
        visual_pad = HANDLE_SIZE  # Smaller padding for border visual

        # 1. Border overlay (below interact) - visual only, no events
        border = tk.Toplevel(self._master)
        border.overrideredirect(True)
        border.attributes("-topmost", True)
        border.configure(bg=_CHROMA_KEY)

        try:
            border.attributes("-transparentcolor", _CHROMA_KEY)
        except Exception:
            border.attributes("-alpha", 0.99)

        bw = w + pad * 2
        bh = h + pad * 2
        border.geometry(
            f"{bw}x{bh}+{s['x1'] - pad}+{s['y1'] - pad}"
        )

        canvas = tk.Canvas(
            border, bg=_CHROMA_KEY, highlightthickness=0,
            width=bw, height=bh,
        )
        canvas.pack(fill="both", expand=True)

        self._border_win = border
        self._border_canvas = canvas

        # 2. Interaction panel (on top) - covers selection + hit padding
        #    alpha=0.01 so nearly invisible, but captures ALL mouse events
        interact = tk.Toplevel(self._master)
        interact.overrideredirect(True)
        interact.attributes("-topmost", True)
        interact.attributes("-alpha", 0.01)
        interact.configure(bg="black")
        interact.geometry(
            f"{bw}x{bh}+{s['x1'] - pad}+{s['y1'] - pad}"
        )

        interact.bind("<Button-1>", self._adjust_on_press)
        interact.bind("<B1-Motion>", self._adjust_on_drag)
        interact.bind("<ButtonRelease-1>", self._adjust_on_release)
        interact.bind("<Motion>", self._adjust_on_motion)
        interact.bind("<Escape>", self._on_escape)

        self._interact_win = interact

        # Z-order: interact on top of border
        interact.lift()
        interact.focus_force()

        self._redraw_border()
        logger.info("Phase B: adjust overlays created")

    def _update_adjust_overlays(self):
        """Reposition border and interaction overlays to match selection."""
        s = self._selection
        if s is None:
            return

        w = s["x2"] - s["x1"]
        h = s["y2"] - s["y1"]
        pad = _HIT_PADDING
        bw = w + pad * 2
        bh = h + pad * 2
        geom = f"{bw}x{bh}+{s['x1'] - pad}+{s['y1'] - pad}"

        if self._border_win:
            self._border_win.geometry(geom)
            if self._border_canvas:
                self._border_canvas.configure(width=bw, height=bh)

        if self._interact_win:
            self._interact_win.geometry(geom)

        self._redraw_border()

    def _redraw_border(self):
        """Redraw the dashed border and tick-mark handles (Snipping Tool style)."""
        canvas = self._border_canvas
        if not canvas:
            return

        canvas.delete("all")

        s = self._selection
        if s is None:
            return

        pad = _HIT_PADDING
        w = s["x2"] - s["x1"]
        h = s["y2"] - s["y1"]

        # Thin dashed white border
        canvas.create_rectangle(
            pad, pad, pad + w, pad + h,
            outline=Colors.SELECTION_BORDER, dash=(4, 3), width=1,
        )

        # Snipping Tool-style tick marks at corners and midpoints
        tick = 18  # Tick mark length
        lw = 5     # Tick line width
        color = Colors.SELECTION_BORDER
        x1, y1 = pad, pad
        x2, y2 = pad + w, pad + h
        cx, cy = pad + w // 2, pad + h // 2

        # Corner ticks (L-shaped)
        # NW
        canvas.create_line(x1, y1, x1 + tick, y1, fill=color, width=lw)
        canvas.create_line(x1, y1, x1, y1 + tick, fill=color, width=lw)
        # NE
        canvas.create_line(x2, y1, x2 - tick, y1, fill=color, width=lw)
        canvas.create_line(x2, y1, x2, y1 + tick, fill=color, width=lw)
        # SW
        canvas.create_line(x1, y2, x1 + tick, y2, fill=color, width=lw)
        canvas.create_line(x1, y2, x1, y2 - tick, fill=color, width=lw)
        # SE
        canvas.create_line(x2, y2, x2 - tick, y2, fill=color, width=lw)
        canvas.create_line(x2, y2, x2, y2 - tick, fill=color, width=lw)

        # Edge midpoint ticks (short perpendicular lines)
        edge_tick = 10
        # N (top center)
        canvas.create_line(cx, y1, cx, y1 - edge_tick, fill=color, width=lw)
        # S (bottom center)
        canvas.create_line(cx, y2, cx, y2 + edge_tick, fill=color, width=lw)
        # W (left center)
        canvas.create_line(x1, cy, x1 - edge_tick, cy, fill=color, width=lw)
        # E (right center)
        canvas.create_line(x2, cy, x2 + edge_tick, cy, fill=color, width=lw)

    def _handle_canvas_positions(
        self, w: int, h: int, pad: int
    ) -> dict[str, tuple[int, int]]:
        """Handle positions relative to the border canvas."""
        cx = pad + w // 2
        cy = pad + h // 2
        return {
            "nw": (pad, pad),
            "n":  (cx, pad),
            "ne": (pad + w, pad),
            "w":  (pad, cy),
            "e":  (pad + w, cy),
            "sw": (pad, pad + h),
            "s":  (cx, pad + h),
            "se": (pad + w, pad + h),
        }

    def _handle_screen_positions(self) -> dict[str, tuple[int, int]]:
        """Handle positions in screen coordinates."""
        s = self._selection
        if s is None:
            return {}
        x1, y1, x2, y2 = s["x1"], s["y1"], s["x2"], s["y2"]
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        return {
            "nw": (x1, y1), "n": (cx, y1), "ne": (x2, y1),
            "w":  (x1, cy),                 "e":  (x2, cy),
            "sw": (x1, y2), "s": (cx, y2), "se": (x2, y2),
        }

    # ------------------------------------------------------------------
    # Event handlers - Draw phase (clicking on dim panels for redraw)
    # ------------------------------------------------------------------

    def _dim_on_press(self, event):
        """Click on dim panel = start drawing a new selection."""
        self._drag_mode = "draw"
        self._drag_start = (event.x_root, event.y_root)

    def _dim_on_drag(self, event):
        if self._drag_mode != "draw":
            return
        sx, sy = self._drag_start
        ex, ey = event.x_root, event.y_root

        x1, x2 = min(sx, ex), max(sx, ex)
        y1, y2 = min(sy, ey), max(sy, ey)

        self._selection = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        self._update_dim_panels()
        self._update_adjust_overlays()

    def _dim_on_release(self, event):
        if self._drag_mode != "draw":
            return
        self._drag_mode = "none"

        s = self._selection
        if s and (s["x2"] - s["x1"]) >= MIN_SELECTION_SIZE and \
                (s["y2"] - s["y1"]) >= MIN_SELECTION_SIZE:
            logger.info(f"Selection redrawn: {self._selection}")
        else:
            self._selection = None

    # ------------------------------------------------------------------
    # Event handlers - Adjust phase (border overlay + interaction panel)
    # ------------------------------------------------------------------

    def _hit_test(self, mx: int, my: int) -> str:
        """Determine drag mode from screen coordinates."""
        s = self._selection
        if s is None:
            return "none"

        # Check handles first (generous hit area: ±16px)
        hs = HANDLE_SIZE + 12
        for name, (hx, hy) in self._handle_screen_positions().items():
            if abs(mx - hx) <= hs and abs(my - hy) <= hs:
                return f"resize_{name}"

        # Inside selection = move
        if s["x1"] <= mx <= s["x2"] and s["y1"] <= my <= s["y2"]:
            return "move"

        return "none"

    def _adjust_on_press(self, event):
        mx, my = event.x_root, event.y_root
        mode = self._hit_test(mx, my)

        if mode == "none":
            return

        self._drag_mode = mode
        self._drag_start = (mx, my)
        self._drag_sel_start = dict(self._selection) if self._selection else None

    def _adjust_on_drag(self, event):
        if self._drag_mode == "none" or self._drag_sel_start is None:
            return

        mx, my = event.x_root, event.y_root
        dx = mx - self._drag_start[0]
        dy = my - self._drag_start[1]
        ss = self._drag_sel_start

        if self._drag_mode == "move":
            w = ss["x2"] - ss["x1"]
            h = ss["y2"] - ss["y1"]
            new_x1 = ss["x1"] + dx
            new_y1 = ss["y1"] + dy

            # Clamp to screen
            scr = self._screen
            sl, st = scr["left"], scr["top"]
            sr = sl + scr["width"]
            sb = st + scr["height"]
            new_x1 = max(sl, min(new_x1, sr - w))
            new_y1 = max(st, min(new_y1, sb - h))

            self._selection = {
                "x1": new_x1, "y1": new_y1,
                "x2": new_x1 + w, "y2": new_y1 + h,
            }

        elif self._drag_mode.startswith("resize_"):
            handle = self._drag_mode[7:]  # e.g., "nw"
            edges = _RESIZE_EDGES.get(handle)
            if not edges:
                return

            new_sel = dict(ss)
            if edges[0]:
                new_sel[edges[0]] = ss[edges[0]] + dx
            if edges[1]:
                new_sel[edges[1]] = ss[edges[1]] + dy

            # Clamp to screen bounds
            scr = self._screen
            sl, st = scr["left"], scr["top"]
            sr = sl + scr["width"]
            sb = st + scr["height"]
            for key in ("x1", "x2"):
                new_sel[key] = max(sl, min(new_sel[key], sr))
            for key in ("y1", "y2"):
                new_sel[key] = max(st, min(new_sel[key], sb))

            self._selection = self._normalize_selection(new_sel)

        self._update_dim_panels()
        self._update_adjust_overlays()

    def _adjust_on_release(self, event):
        self._drag_mode = "none"
        self._drag_sel_start = None

    def _adjust_on_motion(self, event):
        """Update cursor based on hover position."""
        if self._drag_mode != "none":
            return

        mx, my = event.x_root, event.y_root
        mode = self._hit_test(mx, my)

        win = self._interact_win
        if not win:
            return

        if mode.startswith("resize_"):
            handle = mode[7:]
            cursor = _HANDLE_CURSORS.get(handle, "arrow")
        elif mode == "move":
            cursor = "fleur"
        else:
            cursor = "arrow"

        win.configure(cursor=cursor)

    # ------------------------------------------------------------------
    # Shared event handlers
    # ------------------------------------------------------------------

    def _on_escape(self, event):
        logger.info("Selection cancelled by user")
        self.destroy()
        if self._on_cancelled:
            self._on_cancelled()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_z_order(self):
        """Keep border and interact windows above dim panels."""
        try:
            if self._border_win:
                self._border_win.lift()
            if self._interact_win:
                self._interact_win.lift()
        except Exception:
            pass

    @staticmethod
    def _normalize_selection(sel: dict) -> dict:
        """Ensure x1 < x2 and y1 < y2."""
        x1, x2 = min(sel["x1"], sel["x2"]), max(sel["x1"], sel["x2"])
        y1, y2 = min(sel["y1"], sel["y2"]), max(sel["y1"], sel["y2"])
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
