from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from .rule_engine import build_normalized_request
from .validator import validate_normalized_request


class NormalizationError(Exception):
    pass


def normalize_input(
    raw_text: str,
    user_context: Dict[str, object],
    request_context: Dict[str, object],
    *,
    metrics_path: str = "semantic/metrics.yaml",
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    result = build_normalized_request(
        raw_text=raw_text,
        user_context=user_context,
        request_context=request_context,
        metrics_path=metrics_path,
        now=now,
    )

    ok, errors = validate_normalized_request(result)
    if not ok:
        raise NormalizationError("; ".join(errors))

    return result
