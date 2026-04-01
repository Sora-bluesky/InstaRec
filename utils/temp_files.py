"""Temporary file management with automatic cleanup."""

import atexit
import os
import shutil
import tempfile
import logging

logger = logging.getLogger(__name__)


class TempSession:
    """Manages temporary files for a recording session.

    Usage:
        with TempSession() as session:
            video_path = session.video_path
            audio_path = session.audio_path
            # ... record ...
        # Temp files are cleaned up automatically
    """

    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="instarec_")
        self.video_path = os.path.join(self._temp_dir, "video.avi")
        self.audio_path = os.path.join(self._temp_dir, "audio.wav")
        self.output_path = os.path.join(self._temp_dir, "output.mp4")
        # Register cleanup in case of abnormal exit
        atexit.register(self.cleanup)
        logger.info(f"Temp session created: {self._temp_dir}")

    @property
    def temp_dir(self) -> str:
        return self._temp_dir

    def cleanup(self):
        """Remove all temporary files."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                logger.info(f"Temp session cleaned: {self._temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean temp dir: {e}")
            self._temp_dir = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False
