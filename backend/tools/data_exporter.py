from __future__ import annotations

import json
import logging
import csv
import io
from datetime import datetime, timezone
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def export_data(
    data: list[dict],
    export_format: str = "csv",
    columns: list[str] | None = None,
    filename: str | None = None,
) -> dict:
    if not data:
        return {"status": "error", "message": "No data to export"}

    export_format = export_format.lower()
    if not columns:
        columns = list(data[0].keys())

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = filename or f"export_{timestamp}.{export_format}"

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in data:
            writer.writerow([str(row.get(c, "")) for c in columns])
        content = output.getvalue()
        return {
            "status": "ok",
            "format": "csv",
            "filename": filename,
            "row_count": len(data),
            "column_count": len(columns),
            "columns": columns,
            "content": content,
            "content_preview": content[:2000],
        }

    elif export_format == "json":
        content = json.dumps(data, ensure_ascii=False, default=str, indent=2)
        return {
            "status": "ok",
            "format": "json",
            "filename": filename,
            "row_count": len(data),
            "content": content,
            "content_preview": content[:2000],
        }

    elif export_format == "jsonl":
        lines = [json.dumps(row, ensure_ascii=False, default=str) for row in data]
        content = "\n".join(lines)
        return {
            "status": "ok",
            "format": "jsonl",
            "filename": filename,
            "row_count": len(data),
            "content": content,
            "content_preview": content[:2000],
        }

    return {"status": "error", "format": export_format, "message": f"Unsupported format: {export_format}"}


class DataExporterTool(BaseTool):
    name = "data_exporter"
    description = "Export data to CSV, JSON, or JSONL format"
    parameters = {
        "type": "object",
        "properties": {
            "data": {
                "type": "array", "items": {"type": "object"},
                "description": "List of dicts to export",
            },
            "export_format": {
                "type": "string", "enum": ["csv", "json", "jsonl"],
                "description": "Export format",
            },
            "columns": {
                "type": "array", "items": {"type": "string"},
                "description": "Column names (auto-detected if omitted)",
            },
            "filename": {"type": "string", "description": "Output filename"},
        },
        "required": ["data", "export_format"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = export_data(
            kwargs.get("data", []),
            kwargs.get("export_format", "csv"),
            kwargs.get("columns"),
            kwargs.get("filename"),
        )
        return json.dumps(result, ensure_ascii=False)
