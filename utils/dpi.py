"""Windows High DPI awareness utilities."""

import ctypes


def enable_high_dpi_awareness():
    """Enable Windows High DPI awareness for crisp rendering."""
    try:
        # Windows 8.1 / 10+
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            # Windows 7 / 8
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
