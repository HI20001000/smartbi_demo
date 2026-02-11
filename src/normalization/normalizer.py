from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .rule_engine import build_normalized_request
from .validator import validate_normalized_request
from .llm_enricher import enrich_draft


class NormalizationError(Exception):
    pass


def normalize_input(
    raw_text: str,
    user_context: Dict[str, object],
    request_context: Dict[str, object],
    *,
    metrics_path: str = "semantic/metrics.yaml",
    now: Optional[datetime] = None,
    llm_client=None,
) -> Dict[str, object]:
    result = build_normalized_request(
        raw_text=raw_text,
        user_context=user_context,
        request_context=request_context,
        metrics_path=metrics_path,
        now=now,
    )

    result = enrich_draft(
        draft=result,
        time_resolved=result.get("time_context", {}).get("resolved") if isinstance(result.get("time_context"), dict) else None,
        risk_flags=result.get("risk_context", {}).get("risk_flags", []) if isinstance(result.get("risk_context"), dict) else [],
        llm_client=llm_client,
    )

    ok, errors = validate_normalized_request(result)
    if not ok:
        raise NormalizationError("; ".join(errors))

    return result
