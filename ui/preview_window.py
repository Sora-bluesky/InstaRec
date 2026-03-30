"""Preview window with video playback, trim, and export controls.

Uses ffpyplayer for audio+video decoding with tkinter Canvas display.
after() loop polls get_frame() at ~33ms intervals for smooth playback.
"""

import os
import subprocess
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from typing import Callable, Optional
import logging

from ui.theme import Colors, Fonts
from i18n import t

logger = logging.getLogger(__name__)

_ICON_FONT = "Segoe MDL2 Assets"
_ICON_PLAY = "\uE768"
_ICON_PAUSE = "\uE769"
_ICON_SPEAKER = "\uE767"
_ICON_CLOSE = "\uE711"
_ICON_SIZE = 15

_WIN_WIDTH = 800
_WIN_HEIGHT = 560


class PreviewWindow(ctk.CTkToplevel):
    """Post-recording preview with playback, trim, and export."""

    def __init__(
        self,
        master,
        video_path: str,
        on_close: Optional[Callable] = None,
    ):
        super().__init__(master)

        self._video_path = video_path
        self._on_close = on_close

        # Player state
        self._player = None
        self._playing = False
        self._duration = 0.0
        self._position = 0.0
        self._volume = 0.8
        self._trim_start = 0.0
        self._trim_end = 0.0
        self._poll_id = None
        self._photo = None
        self._seeking = False

        # Window setup
        self.title(t("preview.title"))
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=Colors.SURFACE)

        try:
            import pywinstyles
            pywinstyles.apply_style(self, "dark")
        except Exception:
            pass

        # Center on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - _WIN_WIDTH) // 2
        y = (screen_h - _WIN_HEIGHT) // 2
        self.geometry(f"{_WIN_WIDTH}x{_WIN_HEIGHT}+{x}+{y}")

        # Drag state
        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()
        self.after(300, self._load_video)

        logger.info(f"PreviewWindow opened: {video_path}")

    # ----------------------------------------------------------
    # UI Construction
    # ----------------------------------------------------------

    def _build_ui(self):
        """Build preview window layout."""
        # Title bar
        title_bar = ctk.CTkFrame(self, fg_color=Colors.SURFACE, height=36)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        title_bar.bind("<Button-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._do_drag)

        title_label = ctk.CTkLabel(
            title_bar, text=t("preview.title"),
            font=(Fonts.FAMILY_JP, 13),
            text_color=Colors.TEXT_PRIMARY,
        )
        title_label.pack(side="left", padx=16)
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._do_drag)

        close_btn = ctk.CTkButton(
            title_bar, text=_ICON_CLOSE,
            font=(_ICON_FONT, _ICON_SIZE),
            width=28, height=28, corner_radius=14,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            command=self._handle_close,
        )
        close_btn.pack(side="right", padx=8)

        # Video canvas
        self._canvas = tk.Canvas(
            self, bg="#000000", highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # Seek bar
        self._seek_canvas = tk.Canvas(
            self, height=24, bg=Colors.SURFACE, highlightthickness=0,
        )
        self._seek_canvas.pack(fill="x", padx=16, pady=(0, 4))
        self._seek_canvas.bind("<Button-1>", self._on_seek_press)
        self._seek_canvas.bind("<B1-Motion>", self._on_seek_drag)
        self._seek_canvas.bind("<ButtonRelease-1>", self._on_seek_release)

        # Controls row
        ctrl = ctk.CTkFrame(self, fg_color="transparent", height=40)
        ctrl.pack(fill="x", padx=16, pady=(0, 4))

        self._play_btn = ctk.CTkButton(
            ctrl, text=_ICON_PLAY,
            font=(_ICON_FONT, _ICON_SIZE),
            width=32, height=32, corner_radius=16,
            fg_color=Colors.SURFACE_HOVER,
            hover_color=Colors.SURFACE_PRESSED,
            text_color=Colors.TEXT_PRIMARY,
            command=self._toggle_play,
        )
        self._play_btn.pack(side="left", padx=(0, 8))

        self._time_label = ctk.CTkLabel(
            ctrl, text="00:00 / 00:00",
            font=(Fonts.FAMILY, 12),
            text_color=Colors.TEXT_SECONDARY,
        )
        self._time_label.pack(side="left", padx=(0, 16))

        # Volume
        vol_icon = ctk.CTkButton(
            ctrl, text=_ICON_SPEAKER,
            font=(_ICON_FONT, 13),
            width=24, height=24, corner_radius=12,
            fg_color="transparent", hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_SECONDARY,
        )
        vol_icon.pack(side="right", padx=(4, 0))

        self._vol_slider = ctk.CTkSlider(
            ctrl, from_=0, to=1, number_of_steps=20,
            width=80, height=14,
            fg_color=Colors.SEPARATOR,
            progress_color=Colors.TEXT_PRIMARY,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.TEXT_SECONDARY,
            command=self._on_volume_change,
        )
        self._vol_slider.set(self._volume)
        self._vol_slider.pack(side="right", padx=4)

        # Trim row
        trim_frame = ctk.CTkFrame(self, fg_color="transparent", height=28)
        trim_frame.pack(fill="x", padx=16, pady=(0, 4))

        trim_label = ctk.CTkLabel(
            trim_frame, text=t("preview.trim") + ":",
            font=(Fonts.FAMILY_JP, 11),
            text_color=Colors.TEXT_SECONDARY,
        )
        trim_label.pack(side="left", padx=(0, 8))

        self._trim_start_label = ctk.CTkLabel(
            trim_frame, text="00:00",
            font=(Fonts.FAMILY, 11),
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=4, width=50, height=22,
        )
        self._trim_start_label.pack(side="left", padx=2)

        ctk.CTkLabel(
            trim_frame, text="—",
            font=(Fonts.FAMILY, 11),
            text_color=Colors.TEXT_TERTIARY,
        ).pack(side="left", padx=4)

        self._trim_end_label = ctk.CTkLabel(
            trim_frame, text="00:00",
            font=(Fonts.FAMILY, 11),
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=4, width=50, height=22,
        )
        self._trim_end_label.pack(side="left", padx=2)

        # Action buttons
        actions = ctk.CTkFrame(self, fg_color="transparent", height=40)
        actions.pack(fill="x", padx=16, pady=(4, 12))

        # GIF Export (left side)
        ctk.CTkButton(
            actions, text=t("preview.export_gif"),
            font=(Fonts.FAMILY_JP, 13),
            width=100, height=32, corner_radius=8,
            fg_color=Colors.SURFACE_HOVER,
            hover_color=Colors.SURFACE_PRESSED,
            text_color=Colors.TEXT_PRIMARY,
            command=self._handle_gif_export,
        ).pack(side="left", padx=4)

        # Save (primary)
        ctk.CTkButton(
            actions, text=t("preview.save"),
            font=(Fonts.FAMILY_JP, 13),
            width=100, height=32, corner_radius=8,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._handle_save,
        ).pack(side="right", padx=4)

        # Copy (secondary)
        ctk.CTkButton(
            actions, text=t("preview.copy"),
            font=(Fonts.FAMILY_JP, 13),
            width=80, height=32, corner_radius=8,
            fg_color=Colors.SURFACE_HOVER,
            hover_color=Colors.SURFACE_PRESSED,
            text_color=Colors.TEXT_PRIMARY,
            command=self._handle_copy,
        ).pack(side="right", padx=4)

        # Share (secondary)
        ctk.CTkButton(
            actions, text=t("preview.share"),
            font=(Fonts.FAMILY_JP, 13),
            width=80, height=32, corner_radius=8,
            fg_color=Colors.SURFACE_HOVER,
            hover_color=Colors.SURFACE_PRESSED,
            text_color=Colors.TEXT_PRIMARY,
            command=self._handle_share,
        ).pack(side="right", padx=4)

    # ----------------------------------------------------------
    # Video Loading & Playback
    # ----------------------------------------------------------

    def _load_video(self):
        """Initialize MediaPlayer."""
        try:
            from ffpyplayer.player import MediaPlayer
        except ImportError:
            logger.error("ffpyplayer not installed")
            self._handle_close()
            return

        ff_opts = {
            "volume": self._volume,
        }
        try:
            self._player = MediaPlayer(self._video_path, ff_opts=ff_opts)
        except Exception as e:
            logger.error(f"Failed to open video: {e}")
            self._handle_close()
            return
        # Start unpaused to allow frame decoding, pause after first frame
        self.after(500, self._init_metadata)

    def _init_metadata(self, retries: int = 10):
        """Read duration and capture first frame, then pause."""
        if not self._player:
            return
        meta = self._player.get_metadata()
        dur = meta.get("duration", 0)
        if dur and dur > 0:
            self._duration = dur
            self._trim_end = dur
            self._trim_end_label.configure(text=self._fmt_time(dur))

        # Grab first frame (player started unpaused)
        frame, val = self._player.get_frame()
        if frame is not None:
            image_data, pts = frame
            self._position = pts
            self._display_frame(image_data)
            self._update_seek_bar()
            self._update_time_label()
            self._player.set_pause(True)
            self._playing = False
            self._update_play_button()
        elif retries > 0:
            self.after(100, lambda: self._init_metadata(retries - 1))
        else:
            self._player.set_pause(True)
            self._playing = False

    def _start_poll(self):
        if self._poll_id:
            return
        self._do_poll()

    def _do_poll(self):
        if not self._player or not self._playing:
            self._poll_id = None
            return

        frame, val = self._player.get_frame()

        if val == "eof":
            self._playing = False
            self._update_play_button()
            self._poll_id = None
            return

        if frame is not None:
            image_data, pts = frame
            self._position = pts
            self._display_frame(image_data)
            self._update_seek_bar()
            self._update_time_label()

        delay = max(8, int(val * 1000)) if isinstance(val, float) else 33
        self._poll_id = self.after(delay, self._do_poll)

    def _show_frame(self, retries: int = 10):
        """Display a single frame (for paused/seek).

        Briefly unpauses to allow frame decoding, then re-pauses.
        """
        if not self._player or retries <= 0:
            return
        # Unpause briefly to force frame decode
        self._player.set_pause(False)
        frame, val = self._player.get_frame()
        if frame is not None:
            image_data, pts = frame
            self._position = pts
            self._display_frame(image_data)
            self._update_seek_bar()
            self._update_time_label()
            if not self._playing:
                self._player.set_pause(True)
        else:
            self.after(50, lambda: self._show_frame(retries - 1))

    def _display_frame(self, image_data):
        """Convert ffpyplayer frame → PIL → Canvas."""
        try:
            w, h = image_data.get_size()
            raw = image_data.to_bytearray()[0]
            pil_img = Image.frombuffer(
                "RGB", (w, h), bytes(raw), "raw", "rgb24", 0, 1,
            )

            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
            if cw > 1 and ch > 1:
                pil_img = self._fit_image(pil_img, cw, ch)

            self._photo = ImageTk.PhotoImage(pil_img)
            self._canvas.delete("all")
            self._canvas.create_image(
                cw // 2, ch // 2, image=self._photo, anchor="center",
            )
        except Exception as e:
            logger.error(f"Frame display error: {e}")

    @staticmethod
    def _fit_image(img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        if ratio < 1:
            new_w = max(1, int(w * ratio))
            new_h = max(1, int(h * ratio))
            img = img.resize((new_w, new_h), Image.LANCZOS)
        return img

    # ----------------------------------------------------------
    # Playback Controls
    # ----------------------------------------------------------

    def _toggle_play(self):
        if not self._player:
            return
        if self._playing:
            self._player.set_pause(True)
            self._playing = False
        else:
            self._player.set_pause(False)
            self._playing = True
            self._start_poll()
        self._update_play_button()

    def _update_play_button(self):
        icon = _ICON_PAUSE if self._playing else _ICON_PLAY
        self._play_btn.configure(text=icon)

    def _on_volume_change(self, value):
        self._volume = value
        if self._player:
            self._player.set_volume(value)

    # ----------------------------------------------------------
    # Seek
    # ----------------------------------------------------------

    def _on_seek_press(self, event):
        self._seeking = True
        was_playing = self._playing
        if was_playing:
            self._player.set_pause(True)
            self._playing = False
        self._seek_to_event(event)
        self._was_playing_before_seek = was_playing

    def _on_seek_drag(self, event):
        if self._seeking:
            self._seek_to_event(event)

    def _on_seek_release(self, event):
        self._seeking = False
        self._seek_to_event(event)
        if getattr(self, "_was_playing_before_seek", False):
            self._player.set_pause(False)
            self._playing = True
            self._update_play_button()
            self._start_poll()

    def _seek_to_event(self, event):
        if self._duration <= 0 or not self._player:
            return
        w = self._seek_canvas.winfo_width()
        if w <= 0:
            return
        ratio = max(0.0, min(1.0, event.x / w))
        target = ratio * self._duration
        self._player.seek(target, relative=False)
        self._position = target
        self._update_seek_bar()
        self._update_time_label()
        self.after(100, self._show_frame)

    def _update_seek_bar(self):
        c = self._seek_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or self._duration <= 0:
            return

        bar_y = h // 2
        bar_h = 4

        # Track background
        c.create_rectangle(
            0, bar_y - bar_h // 2, w, bar_y + bar_h // 2,
            fill=Colors.SEPARATOR, outline="",
        )

        # Trim region
        ts = (self._trim_start / self._duration) * w
        te = (self._trim_end / self._duration) * w
        c.create_rectangle(
            ts, bar_y - bar_h // 2, te, bar_y + bar_h // 2,
            fill=Colors.TEXT_TERTIARY, outline="",
        )

        # Progress fill
        px = (self._position / self._duration) * w
        c.create_rectangle(
            ts, bar_y - bar_h // 2, min(px, te), bar_y + bar_h // 2,
            fill=Colors.ACCENT, outline="",
        )

        # Playhead
        c.create_oval(
            px - 6, bar_y - 6, px + 6, bar_y + 6,
            fill="#FFFFFF", outline="",
        )

    def _update_time_label(self):
        cur = self._fmt_time(self._position)
        tot = self._fmt_time(self._duration)
        self._time_label.configure(text=f"{cur} / {tot}")

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        s = max(0, int(seconds))
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

    # ----------------------------------------------------------
    # Actions
    # ----------------------------------------------------------

    def _handle_save(self):
        """Save (or Save As with trim) using ffmpeg stream copy."""
        from tkinter import filedialog
        from core.ffmpeg_utils import get_ffmpeg

        has_trim = (
            self._trim_start > 0.5 or
            (self._trim_end < self._duration - 0.5 and self._trim_end > 0)
        )

        if has_trim:
            out = filedialog.asksaveasfilename(
                title=t("preview.save_as"),
                defaultextension=".mp4",
                filetypes=[("MP4", "*.mp4")],
            )
            if not out:
                return
            cmd = [
                get_ffmpeg(), "-y",
                "-ss", str(self._trim_start),
                "-i", self._video_path,
                "-t", str(self._trim_end - self._trim_start),
                "-c", "copy",
                out,
            ]
            def _run_trim():
                try:
                    subprocess.run(cmd, capture_output=True, timeout=120)
                except Exception as e:
                    logger.error(f"Trim export failed: {e}")
            threading.Thread(target=_run_trim, daemon=True).start()
        else:
            # No trim — file already saved at _video_path
            logger.info(f"Recording already saved: {self._video_path}")

        self._handle_close()

    def _handle_gif_export(self):
        """Open GIF export dialog."""
        from ui.gif_export_dialog import GifExportDialog
        GifExportDialog(self, self._video_path, self._duration)

    def _handle_copy(self):
        """Copy video file path to clipboard."""
        self.clipboard_clear()
        self.clipboard_append(self._video_path)

    def _handle_share(self):
        """Open containing folder in Explorer."""
        folder = os.path.dirname(self._video_path)
        os.startfile(folder)

    # ----------------------------------------------------------
    # Drag & Cleanup
    # ----------------------------------------------------------

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _handle_close(self):
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        if self._player:
            self._player.close_player()
            self._player = None
        if self._on_close:
            self._on_close()
        self.destroy()
        logger.info("PreviewWindow closed")
