from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


async def parse_document(file_url: str, doc_type: str | None = None) -> dict:
    if not file_url:
        return {"status": "error", "message": "file_url required"}

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(file_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text

            if not doc_type:
                if "pdf" in content_type:
                    doc_type = "pdf"
                elif "xml" in content_type or "html" in content_type:
                    doc_type = "markup"
                else:
                    doc_type = "text"

            extracted = {
                "source_url": file_url,
                "content_type": content_type,
                "doc_type": doc_type,
                "size_bytes": len(resp.content),
                "size_kb": round(len(resp.content) / 1024, 1),
            }

            if doc_type == "pdf":
                import io
                try:
                    import PyPDF2
                    pdf_file = io.BytesIO(resp.content)
                    reader = PyPDF2.PdfReader(pdf_file)
                    pages = []
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text() or ""
                        pages.append({"page": i + 1, "text": page_text[:2000], "char_count": len(page_text)})
                    extracted["pages"] = pages
                    extracted["page_count"] = len(pages)
                    extracted["full_text"] = "\n".join(p["text"] for p in pages)
                except ImportError:
                    extracted["note"] = "PyPDF2 not installed; returning raw content"
                    extracted["text_preview"] = text[:2000]
            elif doc_type == "markup":
                from xml.etree import ElementTree as ET
                try:
                    root = ET.fromstring(text)
                    extracted["full_text"] = re.sub(r'<[^>]+>', '', text)[:5000]
                    extracted["root_tag"] = root.tag
                except ET.ParseError:
                    extracted["full_text"] = text[:5000]
            else:
                extracted["full_text"] = text[:5000]

            figures = re.findall(r'([\d,]+\.?\d*)\s*(USD|EUR|GBP|%|kg|ton|days?)', extracted.get("full_text", ""))
            if figures:
                extracted["extracted_figures"] = [
                    {"value": v.replace(",", ""), "unit": u} for v, u in figures[:10]
                ]

            return {"status": "ok", **extracted}

    except Exception as e:
        return {"status": "error", "file_url": file_url, "message": str(e)}


class DocumentParserTool(BaseTool):
    name = "document_parser"
    description = "Parse PDFs, XML, HTML, and text documents to extract structured content"
    parameters = {
        "type": "object",
        "properties": {
            "file_url": {"type": "string", "description": "URL of the document to parse"},
            "doc_type": {
                "type": "string",
                "enum": ["pdf", "markup", "text"],
                "description": "Document type (auto-detected if omitted)",
            },
        },
        "required": ["file_url"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        import asyncio
        result = asyncio.run(parse_document(
            kwargs.get("file_url", ""),
            kwargs.get("doc_type"),
        ))
        return json.dumps(result, ensure_ascii=False)
