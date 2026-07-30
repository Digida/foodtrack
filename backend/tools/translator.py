from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

LIBRETRANSLATE_URL = "https://libretranslate.de/translate"
MOCK_LANGUAGES = {
    "ar": "arabic", "zh": "chinese", "fr": "french", "de": "german",
    "hi": "hindi", "id": "indonesian", "it": "italian", "ja": "japanese",
    "ko": "korean", "ms": "malay", "pt": "portuguese", "ru": "russian",
    "es": "spanish", "sw": "swahili", "ta": "tamil", "tl": "tagalog",
    "tr": "turkish", "ur": "urdu", "vi": "vietnamese",
}


async def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> dict:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                LIBRETRANSLATE_URL,
                json={"q": text, "source": source_lang, "target": target_lang, "format": "text"},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "ok",
                    "source_text": text,
                    "translated_text": data.get("translatedText", ""),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "target_language": MOCK_LANGUAGES.get(target_lang, target_lang),
                    "engine": "libretranslate",
                }
            return {
                "status": "error",
                "source_text": text,
                "message": f"LibreTranslate returned {resp.status_code}",
            }
    except Exception as e:
        return {
            "status": "error",
            "source_text": text,
            "message": f"Translation failed: {e}",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "engine": "fallback",
        }


class TranslatorTool(BaseTool):
    name = "translator"
    description = "Translate item names and descriptions between languages using LibreTranslate"
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate"},
            "target_lang": {
                "type": "string",
                "description": "Target language code (ar, zh, fr, de, hi, id, it, ja, ko, ms, pt, ru, es, sw, ta, tl, tr, ur, vi)",
            },
            "source_lang": {"type": "string", "description": "Source language code (default auto)"},
        },
        "required": ["text", "target_lang"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(translate_text(
            kwargs.get("text", ""),
            kwargs.get("target_lang", ""),
            kwargs.get("source_lang", "auto"),
        ))
        return json.dumps(result, ensure_ascii=False)
