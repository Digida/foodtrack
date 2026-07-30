from __future__ import annotations

import json
import logging
import csv
import io
from typing import Any

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)


def import_data(
    content: str,
    import_format: str = "csv",
    columns: list[str] | None = None,
    validate: bool = True,
) -> dict:
    import_format = import_format.lower()
    records = []
    errors = []

    if import_format == "csv":
        reader = csv.DictReader(io.StringIO(content))
        if columns:
            reader = csv.DictReader(io.StringIO(content), fieldnames=columns)

        for i, row in enumerate(reader):
            cleaned = {k.strip(): v.strip() if v else None for k, v in row.items() if k}
            if any(cleaned.values()):
                records.append(cleaned)
            else:
                errors.append({"row": i + 1, "message": "Empty row"})

    elif import_format == "json":
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                records = [parsed]
            elif isinstance(parsed, list):
                records = parsed
            else:
                return {"status": "error", "message": "JSON must be object or array"}
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON: {e}"}

    elif import_format == "jsonl":
        for i, line in enumerate(content.strip().split("\n")):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors.append({"row": i + 1, "message": str(e)})
    else:
        return {"status": "error", "format": import_format, "message": f"Unsupported format: {import_format}"}

    if validate and records:
        keys = set(records[0].keys())
        for i, rec in enumerate(records[1:], 2):
            if set(rec.keys()) != keys:
                errors.append({"row": i, "message": f"Inconsistent columns: expected {keys}, got {set(rec.keys())}"})

    return {
        "status": "ok",
        "format": import_format,
        "record_count": len(records),
        "records": records,
        "errors": errors,
        "error_count": len(errors),
        "summary": f"Parsed {len(records)} records with {len(errors)} errors",
    }


class DataImporterTool(BaseTool):
    name = "data_importer"
    description = "Import data from CSV, JSON, or JSONL format"
    parameters = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Raw content to parse"},
            "import_format": {
                "type": "string", "enum": ["csv", "json", "jsonl"],
                "description": "Input format",
            },
            "columns": {
                "type": "array", "items": {"type": "string"},
                "description": "Column names for CSV without header row",
            },
            "validate": {
                "type": "boolean",
                "description": "Validate column consistency (default true)",
            },
        },
        "required": ["content", "import_format"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        result = import_data(
            kwargs.get("content", ""),
            kwargs.get("import_format", "csv"),
            kwargs.get("columns"),
            kwargs.get("validate", True),
        )
        return json.dumps(result, ensure_ascii=False)
