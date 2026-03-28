"""Screen capture: mss frame grabbing -> ffmpeg stdin pipe."""

import threading
import time
import logging

from mss import mss
from core.ffmpeg_utils import start_video_writer

logger = logging.getLogger(__name__)


class ScreenCapture:
    """Captures screen frames from a region and pipes to ffmpeg.

    Usage:
        cap = ScreenCapture(region, fps, output_path)
        cap.start()   # begins capture in background thread
        cap.stop()    # signals stop, blocks until thread joins
    """

    def __init__(self, region: dict, fps: int, output_path: str):
        self._region = region  # {x, y, w, h}
        self._fps = fps
        self._output_path = output_path
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ffmpeg_proc = None
        self._error: Exception | None = None

    @property
    def had_error(self) -> bool:
        return self._error is not None

    def start(self):
        self._stop_event.clear()
        self._error = None
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="ScreenCapture",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10.0)
            self._thread = None

    def _capture_loop(self):
        r = self._region
        monitor = {
            "left": r["x"], "top": r["y"],
            "width": r["w"], "height": r["h"],
        }
        frame_interval = 1.0 / self._fps

        try:
            self._ffmpeg_proc = start_video_writer(
                self._output_path, r["w"], r["h"], self._fps,
            )

            with mss() as sct:
                next_frame_time = time.perf_counter()

                while not self._stop_event.is_set():
                    now = time.perf_counter()
                    if now < next_frame_time:
                        sleep_time = next_frame_time - now
                        if sleep_time > 0.001:
                            time.sleep(sleep_time * 0.8)
                        continue

                    frame = sct.grab(monitor)
                    try:
                        # frame.raw returns BGRA pixel data
                        self._ffmpeg_proc.stdin.write(frame.raw)
                    except (BrokenPipeError, OSError):
                        logger.error("ffmpeg pipe broken")
                        break

                    next_frame_time += frame_interval

        except Exception as e:
            self._error = e
            logger.error(f"Screen capture error: {e}")
        finally:
            self._close_ffmpeg()

    def _close_ffmpeg(self):
        if self._ffmpeg_proc:
            try:
                if self._ffmpeg_proc.stdin and not self._ffmpeg_proc.stdin.closed:
                    self._ffmpeg_proc.stdin.close()
                self._ffmpeg_proc.wait(timeout=10)
            except Exception as e:
                logger.warning(f"ffmpeg close error: {e}")
                try:
                    self._ffmpeg_proc.kill()
                except Exception:
                    pass
            self._ffmpeg_proc = None
