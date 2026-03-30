"""GIF export dialog with quality and FPS selection.

Converts MP4 to GIF using ffmpeg with palette generation for quality.
"""

import os
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog
from typing import Optional
import logging

from ui.theme import Colors, Fonts
from core.ffmpeg_utils import get_ffmpeg
from i18n import t

logger = logging.getLogger(__name__)

# Quality presets: (scale_factor, dither)
_QUALITY = {
    "low": (0.5, "none"),
    "medium": (0.75, "bayer:bayer_scale=3"),
    "high": (1.0, "bayer:bayer_scale=5"),
}

_FPS_OPTIONS = [10, 15, 30]


class GifExportDialog(ctk.CTkToplevel):
    """Modal dialog for GIF export settings."""

    def __init__(self, master, video_path: str, duration: float = 0.0):
        super().__init__(master)

        self._video_path = video_path
        self._duration = duration
        self._quality = "medium"
        self._fps = 15
        self._exporting = False

        # Window setup
        self.title(t("gif.title"))
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=Colors.SURFACE)

        try:
            import pywinstyles
            pywinstyles.apply_style(self, "dark")
        except Exception:
            pass

        # Center on screen
        w, h = 420, 280
        sx = self.winfo_screenwidth()
        sy = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sx-w)//2}+{(sy-h)//2}")

        self._build_ui()

        # Grab focus
        self.grab_set()
        self.focus_force()

    def _build_ui(self):
        # Title
        title = ctk.CTkLabel(
            self, text=t("gif.title"),
            font=(Fonts.FAMILY_JP, 16, "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(pady=(20, 16), padx=24, anchor="w")

        # Quality row
        q_frame = ctk.CTkFrame(self, fg_color="transparent")
        q_frame.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            q_frame, text=t("gif.quality") + ":",
            font=(Fonts.FAMILY_JP, 13),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 12))

        self._q_buttons = {}
        for q, label_key in [
            ("low", "gif.quality.low"),
            ("medium", "gif.quality.medium"),
            ("high", "gif.quality.high"),
        ]:
            btn = ctk.CTkButton(
                q_frame, text=t(label_key),
                font=(Fonts.FAMILY_JP, 12),
                width=70, height=28, corner_radius=6,
                fg_color=Colors.ACCENT if q == self._quality else Colors.SURFACE_HOVER,
                hover_color=Colors.ACCENT_HOVER,
                text_color="#FFFFFF",
                command=lambda quality=q: self._set_quality(quality),
            )
            btn.pack(side="left", padx=4)
            self._q_buttons[q] = btn

        # FPS row
        fps_frame = ctk.CTkFrame(self, fg_color="transparent")
        fps_frame.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(
            fps_frame, text=t("gif.fps") + ":",
            font=(Fonts.FAMILY_JP, 13),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 12))

        self._fps_buttons = {}
        for fps in _FPS_OPTIONS:
            btn = ctk.CTkButton(
                fps_frame, text=f"{fps} fps",
                font=(Fonts.FAMILY, 12),
                width=60, height=28, corner_radius=6,
                fg_color=Colors.ACCENT if fps == self._fps else Colors.SURFACE_HOVER,
                hover_color=Colors.ACCENT_HOVER,
                text_color="#FFFFFF",
                command=lambda f=fps: self._set_fps(f),
            )
            btn.pack(side="left", padx=4)
            self._fps_buttons[fps] = btn

        # Estimated size
        self._size_label = ctk.CTkLabel(
            self, text="",
            font=(Fonts.FAMILY, 11),
            text_color=Colors.TEXT_SECONDARY,
        )
        self._size_label.pack(padx=24, anchor="w", pady=(0, 16))
        self._update_size_estimate()

        # Status label (for exporting)
        self._status_label = ctk.CTkLabel(
            self, text="",
            font=(Fonts.FAMILY_JP, 11),
            text_color=Colors.ACCENT,
        )
        self._status_label.pack(padx=24, anchor="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(8, 20))

        ctk.CTkButton(
            btn_frame, text=t("gif.export"),
            font=(Fonts.FAMILY_JP, 13, "bold"),
            width=120, height=32, corner_radius=8,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._export,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            btn_frame, text=t("gif.cancel"),
            font=(Fonts.FAMILY_JP, 13),
            width=90, height=32, corner_radius=8,
            fg_color=Colors.SURFACE_HOVER,
            hover_color=Colors.SURFACE_PRESSED,
            text_color=Colors.TEXT_PRIMARY,
            command=self._cancel,
        ).pack(side="right", padx=4)

    def _set_quality(self, quality: str):
        self._quality = quality
        for q, btn in self._q_buttons.items():
            btn.configure(
                fg_color=Colors.ACCENT if q == quality else Colors.SURFACE_HOVER,
            )
        self._update_size_estimate()

    def _set_fps(self, fps: int):
        self._fps = fps
        for f, btn in self._fps_buttons.items():
            btn.configure(
                fg_color=Colors.ACCENT if f == fps else Colors.SURFACE_HOVER,
            )
        self._update_size_estimate()

    def _update_size_estimate(self):
        """Rough estimate based on duration, fps, and quality."""
        if self._duration <= 0:
            self._size_label.configure(text="")
            return
        scale = _QUALITY[self._quality][0]
        # Rough: ~50KB per frame at full quality, scaled down
        kb_per_frame = 50 * scale * scale
        total_frames = self._duration * self._fps
        size_mb = (total_frames * kb_per_frame) / 1024
        self._size_label.configure(
            text=f"{t('gif.estimated_size')}: ~{size_mb:.1f} MB",
        )

    def _export(self):
        if self._exporting:
            return

        out = filedialog.asksaveasfilename(
            title=t("gif.title"),
            defaultextension=".gif",
            filetypes=[("GIF", "*.gif")],
        )
        if not out:
            return

        self._exporting = True
        self._status_label.configure(text=t("gif.exporting"))

        threading.Thread(
            target=self._do_export,
            args=(out,),
            daemon=True,
        ).start()

    def _do_export(self, output_path: str):
        """Run ffmpeg GIF conversion with palette generation."""
        ffmpeg = get_ffmpeg()
        scale = _QUALITY[self._quality][0]
        dither = _QUALITY[self._quality][1]
        fps = self._fps

        # Two-pass with palette for better quality
        palette_path = output_path + ".palette.png"
        try:
            scale_w = -1 if scale >= 1.0 else f"iw*{scale}"
            scale_filter = f"fps={fps},scale={scale_w}:-1:flags=lanczos"

            # Pass 1: Generate palette
            cmd1 = [
                ffmpeg, "-y",
                "-i", self._video_path,
                "-vf", f"{scale_filter},palettegen=stats_mode=diff",
                palette_path,
            ]
            r1 = subprocess.run(cmd1, capture_output=True, timeout=120)
            if r1.returncode != 0:
                logger.error(f"Palette gen failed: {r1.stderr.decode(errors='ignore')[:300]}")
                self.after(0, lambda: self._on_export_done(False))
                return

            # Pass 2: Convert with palette
            cmd2 = [
                ffmpeg, "-y",
                "-i", self._video_path,
                "-i", palette_path,
                "-lavfi",
                f"{scale_filter} [x]; [x][1:v] paletteuse=dither={dither}",
                output_path,
            ]
            r2 = subprocess.run(cmd2, capture_output=True, timeout=300)
            if r2.returncode != 0:
                logger.error(f"GIF export failed: {r2.stderr.decode(errors='ignore')[:300]}")
                self.after(0, lambda: self._on_export_done(False))
                return

            self.after(0, lambda: self._on_export_done(True))

        except Exception as e:
            logger.error(f"GIF export error: {e}")
            self.after(0, lambda: self._on_export_done(False))
        finally:
            try:
                os.unlink(palette_path)
            except Exception:
                pass

    def _on_export_done(self, success: bool):
        self._exporting = False
        if success:
            self.grab_release()
            self.destroy()
        else:
            self._status_label.configure(
                text="Export failed", text_color=Colors.RED,
            )

    def _cancel(self):
        if not self._exporting:
            self.grab_release()
            self.destroy()
