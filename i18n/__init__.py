"""Internationalization module for InstaRec.

Usage:
    from i18n import t, init, get_system_language

    init("en")          # Initialize with language code
    label = t("menu.quit")  # Returns "Exit"
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
_strings: dict[str, str] = {}
_current_lang: str = "en"
_AVAILABLE = {"en": "English", "ja": "日本語"}


def init(lang: str = "en") -> None:
    """Load translation strings for the given language code."""
    global _strings, _current_lang

    if lang not in _AVAILABLE:
        lang = "en"

    path = os.path.join(_DATA_DIR, f"{lang}.json")
    if not os.path.exists(path):
        logger.warning(f"Translation file not found: {path}, falling back to en")
        path = os.path.join(_DATA_DIR, "en.json")
        lang = "en"

    with open(path, "r", encoding="utf-8") as f:
        _strings = json.load(f)

    _current_lang = lang
    logger.info(f"i18n initialized: {lang}")


def t(key: str) -> str:
    """Get translated string by key. Returns key itself if not found."""
    return _strings.get(key, key)


def current_language() -> str:
    """Return current language code."""
    return _current_lang


def available_languages() -> dict[str, str]:
    """Return dict of available language codes to display names."""
    return dict(_AVAILABLE)


def get_system_language() -> str:
    """Detect OS UI language and return matching language code.

    Uses Windows API GetUserDefaultUILanguage() to get the LCID,
    then maps to our supported language codes.
    Falls back to 'en' for unsupported languages.
    """
    try:
        import ctypes
        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # Japanese: primary language ID 0x11
        if (lcid & 0xFF) == 0x11:
            return "ja"
    except Exception:
        pass
    return "en"
