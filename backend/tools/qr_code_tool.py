from __future__ import annotations

import json
import logging
import io
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


def generate_qr(data: str, box_size: int = 10, border: int = 4) -> dict:
    if not QR_AVAILABLE:
        return generate_qr_text(data)

    try:
        qr = qrcode.QRCode(box_size=box_size, border=border)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        import base64
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        return {
            "status": "ok",
            "data": data,
            "format": "png_base64",
            "image_base64": b64,
            "data_uri": f"data:image/png;base64,{b64}",
            "box_size": box_size,
            "border": border,
        }
    except Exception as e:
        return {"status": "error", "data": data, "message": str(e)}


def generate_qr_text(data: str) -> dict:
    return {
        "status": "ok",
        "data": data,
        "format": "text",
        "note": "Install 'qrcode' and 'pillow' packages to generate actual QR images",
        "qr_payload": data,
        "url_template": f"https://api.foodtrack.ae/scan/qr/{{hash}}",
        "suggestion": f"Use this payload in a QR generator: {data}",
    }


def decode_qr(image_url: str) -> dict:
    try:
        import httpx
        import io
        resp = __import__("httpx").get(image_url, timeout=15)
        resp.raise_for_status()

        try:
            from PIL import Image
            from pyzbar.pyzbar import decode as pyzbar_decode
            img = Image.open(io.BytesIO(resp.content))
            decoded = pyzbar_decode(img)
            if decoded:
                return {
                    "status": "ok",
                    "data": decoded[0].data.decode("utf-8", errors="replace"),
                    "type": str(decoded[0].type),
                }
            return {"status": "error", "message": "No QR code found in image"}
        except ImportError:
            return {"status": "error", "message": "Install pyzbar and Pillow for QR decoding"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class QrCodeTool(BaseTool):
    name = "qr_code_tool"
    description = "Generate QR codes for items and decode QR codes from images"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["generate", "decode"],
                "description": "Action to perform",
            },
            "data": {"type": "string", "description": "Data to encode in QR (for generate)"},
            "image_url": {"type": "string", "description": "Image URL containing QR code (for decode)"},
            "box_size": {"type": "integer", "description": "QR box size in pixels (default 10)"},
            "border": {"type": "integer", "description": "QR border width (default 4)"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        if action == "generate":
            result = generate_qr(
                kwargs.get("data", ""),
                kwargs.get("box_size", 10),
                kwargs.get("border", 4),
            )
        elif action == "decode":
            result = decode_qr(kwargs.get("image_url", ""))
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        return json.dumps(result, ensure_ascii=False)
