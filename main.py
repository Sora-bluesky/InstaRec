"""InstaRec - Screen recording tool for Windows 10."""

from utils.dpi import enable_high_dpi_awareness
from app import InstaRecApp


def main():
    enable_high_dpi_awareness()
    app = InstaRecApp()
    app.mainloop()


if __name__ == "__main__":
    main()
