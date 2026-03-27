"""Application configuration with JSON persistence."""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", ""), "InstaRec")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class AppConfig:
    save_directory: str = ""  # Empty = Desktop
    fps: int = 30
    system_audio: bool = True
    microphone: bool = False
    output_format: str = "mp4"  # "mp4" or "gif"
    hotkey: str = "win+shift+r"
    cursor_style: str = "target"  # "target", "default", "none"
    countdown_seconds: int = 3

    def __post_init__(self):
        if not self.save_directory:
            self.save_directory = os.path.join(
                os.path.expanduser("~"), "Desktop"
            )

    def save(self):
        """Save config to JSON file."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
            logger.info(f"Config saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config from JSON file, or return defaults."""
        if not os.path.exists(CONFIG_FILE):
            return cls()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Only use known fields
            valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in valid_fields}
            return cls(**filtered)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return cls()
