"""Multi-monitor screen metrics utilities."""

import ctypes
from mss import mss


def get_screen_metrics() -> dict:
    """Get the bounding box covering all monitors."""
    with mss() as sct:
        # monitors[0] is the combined bounding box of all monitors
        monitor = sct.monitors[0]
        return {
            "left": monitor["left"],
            "top": monitor["top"],
            "width": monitor["width"],
            "height": monitor["height"],
        }


def get_monitor_scaling() -> float:
    """Get the main monitor DPI scaling factor."""
    try:
        user32 = ctypes.windll.user32
        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except Exception:
        return 1.0
