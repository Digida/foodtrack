from __future__ import annotations

import json
import logging
import base64
import io
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


async def analyze_image(image_url: str, analysis_type: str = "auto") -> dict:
    results = {"image_url": image_url, "analysis_type": analysis_type}

    if not image_url:
        return {"status": "error", "message": "image_url required"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            results["content_type"] = content_type
            results["size_bytes"] = len(resp.content)
            results["size_kb"] = round(len(resp.content) / 1024, 1)

            img_b64 = base64.b64encode(resp.content).decode("ascii")

            analysis = {"format": content_type, "size_bytes": len(resp.content)}

            if analysis_type in ("auto", "labels"):
                try:
                    ocr_resp = await client.post(
                        "https://api.ocr.space/parse/image",
                        data={
                            "base64Image": f"data:{content_type};base64,{img_b64}",
                            "language": "eng",
                            "isOverlayRequired": False,
                        },
                        timeout=20,
                    )
                    if ocr_resp.status_code == 200:
                        ocr_data = ocr_resp.json()
                        parsed = ocr_data.get("ParsedResults", [])
                        if parsed:
                            text = parsed[0].get("ParsedText", "").strip()
                            if text:
                                analysis["ocr_text"] = text[:2000]
                                analysis["ocr_confidence"] = parsed[0].get("FileParseExitCode", 0)
                except Exception as e:
                    logger.warning(f"OCR failed: {e}")

            results["analysis"] = analysis
            results["status"] = "ok"
            return results

    except Exception as e:
        return {"status": "error", "image_url": image_url, "message": str(e)}


class ImageAnalyzerTool(BaseTool):
    name = "image_analyzer"
    description = "Analyze images: extract text via OCR, detect format, size, and content type"
    parameters = {
        "type": "object",
        "properties": {
            "image_url": {"type": "string", "description": "URL of the image to analyze"},
            "analysis_type": {
                "type": "string",
                "enum": ["auto", "labels", "ocr"],
                "description": "Type of analysis (default auto)",
            },
        },
        "required": ["image_url"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(analyze_image(
            kwargs.get("image_url", ""),
            kwargs.get("analysis_type", "auto"),
        ))
        return json.dumps(result, ensure_ascii=False)
