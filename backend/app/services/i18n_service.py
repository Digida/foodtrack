import json
import os
from pathlib import Path

_translations: dict[str, dict[str, str]] = {}


def _load_translations():
    global _translations
    i18n_dir = Path(__file__).resolve().parent.parent / "i18n"
    if not i18n_dir.exists():
        return
    for f in i18n_dir.glob("*.json"):
        lang = f.stem
        try:
            with open(f, encoding="utf-8") as fh:
                _translations[lang] = json.load(fh)
        except Exception:
            _translations[lang] = {}


def get_supported_languages() -> list[str]:
    if not _translations:
        _load_translations()
    return list(_translations.keys())


def translate(key: str, lang: str = "en") -> str:
    if not _translations:
        _load_translations()
    if lang in _translations and key in _translations[lang]:
        return _translations[lang][key]
    return key


def get_accept_language(accept_language_header: str | None) -> str:
    if not accept_language_header:
        return "en"
    supported = get_supported_languages()
    if not supported:
        return "en"
    for part in accept_language_header.split(","):
        lang = part.split(";")[0].strip().split("-")[0].lower()
        if lang in supported:
            return lang
    return "en"
