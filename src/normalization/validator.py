from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


def _load_schema(path: str = "contracts/normalized_request.schema.json") -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_normalized_request(data: Dict[str, object], schema_path: str = "contracts/normalized_request.schema.json") -> Tuple[bool, List[str]]:
    schema = _load_schema(schema_path)
    errors: List[str] = []

    required = schema.get("required", [])
    for key in required:
        if key not in data:
            errors.append(f"missing required key: {key}")

    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")

    request_context = data.get("request_context", {})
    if not isinstance(request_context, dict):
        errors.append("request_context must be object")
    else:
        if not request_context.get("request_ts"):
            errors.append("request_context.request_ts is required")
        tz = request_context.get("timezone")
        if not tz:
            errors.append("request_context.timezone is required")

    query_context = data.get("query_context", {})
    if not isinstance(query_context, dict):
        errors.append("query_context must be object")
    else:
        if query_context.get("language") not in ["zh-TW", "zh-CN", "en"]:
            errors.append("query_context.language invalid")
        if query_context.get("intent") not in ["kpi_query", "comparison", "trend", "detail_request", "out_of_scope"]:
            errors.append("query_context.intent invalid")

    time_context = data.get("time_context", {})
    if not isinstance(time_context, dict):
        errors.append("time_context must be object")
    else:
        resolved = time_context.get("resolved")
        if resolved is not None:
            if not isinstance(resolved, dict):
                errors.append("time_context.resolved must be object|null")
            else:
                kind = resolved.get("type")
                if kind not in ["single_date", "date_range", "month_to_date", "year_to_date", "latest_available_date"]:
                    errors.append("time_context.resolved.type invalid")
                for k in ["start_date", "end_date"]:
                    val = resolved.get(k, "")
                    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(val)):
                        errors.append(f"time_context.resolved.{k} invalid")

    missing_fields = data.get("missing_required_fields", [])
    if not isinstance(missing_fields, list):
        errors.append("missing_required_fields must be array")

    return len(errors) == 0, errors
