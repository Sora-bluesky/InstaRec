"""FFmpeg subprocess utilities using imageio-ffmpeg binary."""

import os
import subprocess
import logging

from imageio_ffmpeg import get_ffmpeg_exe

logger = logging.getLogger(__name__)


def get_ffmpeg() -> str:
    """Return path to ffmpeg binary from imageio-ffmpeg."""
    return get_ffmpeg_exe()


def start_video_writer(
    output_path: str,
    width: int,
    height: int,
    fps: int,
) -> subprocess.Popen:
    """Start an ffmpeg process that accepts raw BGRA frames on stdin.

    Returns a Popen with stdin pipe open for writing raw frame bytes.
    Output is H.264 in MP4 container, tuned for fast recording.
    """
    cmd = [
        get_ffmpeg(),
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgra",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def concat_segments(segment_paths: list[str], output_path: str) -> bool:
    """Concatenate media segments using ffmpeg concat demuxer.

    Works for both video (.mp4) and audio (.wav) segments.
    Returns True on success.
    """
    if not segment_paths:
        return False

    if len(segment_paths) == 1:
        # Single segment: just copy
        import shutil
        try:
            shutil.copy2(segment_paths[0], output_path)
            return True
        except Exception as e:
            logger.error(f"Segment copy failed: {e}")
            return False

    # Write concat list file
    list_path = output_path + ".list.txt"
    try:
        with open(list_path, "w", encoding="utf-8") as f:
            for p in segment_paths:
                # Normalize to forward slashes for ffmpeg
                normalized = p.replace("\\", "/")
                f.write(f"file '{normalized}'\n")

        cmd = [
            get_ffmpeg(), "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            output_path,
        ]

        result = subprocess.run(
            cmd, capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="ignore")
            logger.error(f"Concat failed: {stderr[:500]}")
            return False
        return True

    except Exception as e:
        logger.error(f"Concat error: {e}")
        return False
    finally:
        try:
            os.unlink(list_path)
        except Exception:
            pass


def mux_audio_video(
    video_path: str,
    audio_paths: list[str],
    output_path: str,
) -> bool:
    """Mux video with one or more audio tracks.

    Multiple audio tracks are mixed with amix filter.
    Returns True on success.
    """
    if not audio_paths:
        return False

    cmd = [get_ffmpeg(), "-y", "-i", video_path]
    for ap in audio_paths:
        cmd.extend(["-i", ap])

    if len(audio_paths) == 1:
        cmd.extend([
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ])
    else:
        n = len(audio_paths)
        filter_inputs = "".join(f"[{i + 1}:a]" for i in range(n))
        cmd.extend([
            "-filter_complex",
            f"{filter_inputs}amix=inputs={n}:duration=shortest",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ])

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="ignore")
            logger.error(f"Mux failed: {stderr[:500]}")
            return False
        return True
    except Exception as e:
        logger.error(f"Mux error: {e}")
        return False
