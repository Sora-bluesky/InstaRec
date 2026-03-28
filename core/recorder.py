"""Recording orchestrator: coordinates screen capture, audio, and segments."""

import os
import threading
import logging
from typing import Callable, Optional

from config import AppConfig
from utils.temp_files import TempSession
from core.segment import SegmentManager
from core.screen_capture import ScreenCapture
from core.audio_capture import AudioCapture
from core.ffmpeg_utils import concat_segments, mux_audio_video

logger = logging.getLogger(__name__)


class Recorder:
    """Top-level recording coordinator.

    Lifecycle:
        recorder = Recorder(region, config, root)
        recorder.start()              # starts segment 0
        recorder.pause()              # stops segment 0
        recorder.resume()             # starts segment 1
        recorder.stop(on_complete)    # stops, concatenates, muxes
        # on_complete(output_path) called on main thread
        recorder.cleanup()            # removes temp files
    """

    def __init__(
        self,
        region: dict,
        config: AppConfig,
        root,  # tkinter root for after() scheduling
        on_error: Callable[[str], None] | None = None,
    ):
        self._region = region
        self._config = config
        self._root = root
        self._on_error = on_error

        self._session: TempSession | None = None
        self._seg_mgr: SegmentManager | None = None

        self._screen_cap: ScreenCapture | None = None
        self._sys_audio_cap: AudioCapture | None = None
        self._mic_audio_cap: AudioCapture | None = None

        self._mic_device_id: str | None = None

    @property
    def output_path(self) -> str | None:
        if self._session:
            return self._session.output_path
        return None

    def set_mic_device(self, device_id: str | None):
        self._mic_device_id = device_id

    def start(self):
        self._session = TempSession()
        self._seg_mgr = SegmentManager(self._session.temp_dir)
        self._start_segment()
        logger.info("Recorder started")

    def pause(self):
        self._stop_segment()
        logger.info("Recorder paused")

    def resume(self):
        self._start_segment()
        logger.info("Recorder resumed")

    def stop(self, on_complete: Callable[[Optional[str]], None]):
        """Stop recording and begin finalization in background.

        on_complete(output_path) is called on the main thread.
        output_path is None on failure.
        """
        self._stop_segment()
        thread = threading.Thread(
            target=self._finalize,
            args=(on_complete,),
            name="Finalize",
            daemon=True,
        )
        thread.start()
        logger.info("Recorder stopped, finalizing...")

    def cleanup(self):
        self._stop_segment()
        if self._session:
            self._session.cleanup()
            self._session = None
        logger.info("Recorder cleaned up")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _start_segment(self):
        seg = self._seg_mgr.new_segment()

        # Screen capture
        self._screen_cap = ScreenCapture(
            region=self._region,
            fps=self._config.fps,
            output_path=seg.video_path,
        )
        self._screen_cap.start()

        # System audio (loopback)
        if self._config.system_audio:
            self._sys_audio_cap = AudioCapture(
                output_path=seg.system_audio_path,
                loopback=True,
            )
            if not self._sys_audio_cap.start():
                logger.warning("System audio capture failed to start")
                self._sys_audio_cap = None

        # Microphone
        if self._config.microphone:
            self._mic_audio_cap = AudioCapture(
                output_path=seg.mic_audio_path,
                loopback=False,
                device_id=self._mic_device_id,
            )
            if not self._mic_audio_cap.start():
                logger.warning("Mic capture failed to start")
                self._mic_audio_cap = None

    def _stop_segment(self):
        if self._screen_cap:
            self._screen_cap.stop()
            self._screen_cap = None
        if self._sys_audio_cap:
            self._sys_audio_cap.stop()
            self._sys_audio_cap = None
        if self._mic_audio_cap:
            self._mic_audio_cap.stop()
            self._mic_audio_cap = None

    def _finalize(self, on_complete: Callable):
        try:
            video_paths = self._seg_mgr.video_paths
            if not video_paths:
                logger.error("No video segments found")
                self._schedule(on_complete, None)
                return

            session_dir = self._session.temp_dir

            # 1. Concat video segments
            if len(video_paths) == 1:
                concat_video = video_paths[0]
            else:
                concat_video = os.path.join(session_dir, "concat_video.mp4")
                if not concat_segments(video_paths, concat_video):
                    logger.error("Video concat failed")
                    self._schedule(on_complete, None)
                    return

            # 2. Concat audio segments (system + mic separately)
            audio_tracks = []

            sys_paths = self._seg_mgr.system_audio_paths
            if sys_paths:
                if len(sys_paths) == 1:
                    audio_tracks.append(sys_paths[0])
                else:
                    concat_sys = os.path.join(session_dir, "concat_sys.wav")
                    if concat_segments(sys_paths, concat_sys):
                        audio_tracks.append(concat_sys)

            mic_paths = self._seg_mgr.mic_audio_paths
            if mic_paths:
                if len(mic_paths) == 1:
                    audio_tracks.append(mic_paths[0])
                else:
                    concat_mic = os.path.join(session_dir, "concat_mic.wav")
                    if concat_segments(mic_paths, concat_mic):
                        audio_tracks.append(concat_mic)

            # 3. Mux video + audio
            output_path = self._session.output_path
            if audio_tracks:
                if mux_audio_video(concat_video, audio_tracks, output_path):
                    self._schedule(on_complete, output_path)
                else:
                    logger.warning("Audio mux failed; using video-only")
                    self._schedule(on_complete, concat_video)
            else:
                # Video only
                self._schedule(on_complete, concat_video)

        except Exception as e:
            logger.error(f"Finalization error: {e}")
            self._schedule(on_complete, None)

    def _schedule(self, callback: Callable, *args):
        """Schedule a callback on the tkinter main thread."""
        self._root.after(0, callback, *args)
