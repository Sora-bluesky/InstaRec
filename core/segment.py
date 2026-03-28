"""Segment file management for pause/resume recording."""

import os
import logging

logger = logging.getLogger(__name__)


class Segment:
    """One continuous recording segment (between pause events)."""

    def __init__(self, index: int, base_dir: str):
        self.index = index
        self.video_path = os.path.join(base_dir, f"seg_{index:03d}_video.mp4")
        self.system_audio_path = os.path.join(
            base_dir, f"seg_{index:03d}_sys.wav",
        )
        self.mic_audio_path = os.path.join(
            base_dir, f"seg_{index:03d}_mic.wav",
        )


class SegmentManager:
    """Creates and tracks segments within a temp directory.

    Usage:
        mgr = SegmentManager(temp_dir)
        seg0 = mgr.new_segment()   # Segment(0, ...)
        seg1 = mgr.new_segment()   # Segment(1, ...)
        all_segs = mgr.segments    # [seg0, seg1]
    """

    def __init__(self, base_dir: str):
        self._base_dir = base_dir
        self._segments: list[Segment] = []

    @property
    def segments(self) -> list[Segment]:
        return list(self._segments)

    @property
    def current(self) -> Segment | None:
        return self._segments[-1] if self._segments else None

    def new_segment(self) -> Segment:
        seg = Segment(len(self._segments), self._base_dir)
        self._segments.append(seg)
        logger.info(f"New segment {seg.index}: {seg.video_path}")
        return seg

    @property
    def video_paths(self) -> list[str]:
        return [s.video_path for s in self._segments
                if os.path.exists(s.video_path)]

    @property
    def system_audio_paths(self) -> list[str]:
        return [s.system_audio_path for s in self._segments
                if os.path.exists(s.system_audio_path)]

    @property
    def mic_audio_paths(self) -> list[str]:
        return [s.mic_audio_path for s in self._segments
                if os.path.exists(s.mic_audio_path)]
