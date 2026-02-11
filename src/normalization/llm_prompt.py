from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


PROMPT_FILE = Path(__file__).resolve().parents[2] / "prompts" / "json_completion_prompt.md"


def load_json_completion_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def build_json_completion_prompt(
    draft: Dict[str, Any],
    time_resolved: Optional[Dict[str, Any]],
    risk_flags: Iterable[str],
    allowed_fields: Iterable[str],
    protected_fields: Iterable[str],
) -> str:
    template = load_json_completion_prompt()
    payload = {
        "draft": draft,
        "time_resolved": time_resolved,
        "risk_flags": list(risk_flags),
        "allowed_fields": list(allowed_fields),
        "protected_fields": list(protected_fields),
    }
    return f"{template}\n\nInput JSON:\n{json.dumps(payload, ensure_ascii=False)}"
