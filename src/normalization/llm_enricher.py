from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, Iterable, Optional

from . import config
from .llm_prompt import build_json_completion_prompt
from .validator import validate_normalized_request


def _record_enrichment_failure(_reason: str) -> None:
    """Hook for logging/metrics; intentionally no-op by default."""


def _call_llm(llm_client: Any, prompt: str, timeout_seconds: int) -> str:
    if callable(llm_client):
        return llm_client(prompt, timeout=timeout_seconds)
    if hasattr(llm_client, "complete"):
        return llm_client.complete(prompt=prompt, timeout=timeout_seconds)
    raise TypeError("Unsupported llm_client interface")


def _enforce_allowed_and_protected(
    original: Dict[str, Any],
    completed: Dict[str, Any],
    allowed_fields: Iterable[str],
    protected_fields: Iterable[str],
) -> Dict[str, Any]:
    result = deepcopy(original)
    allowed = set(allowed_fields)
    for field in allowed:
        if field in completed:
            result[field] = completed[field]

    for field in protected_fields:
        if field in original:
            result[field] = original[field]

    return result


def enrich_draft(
    draft: Dict[str, Any],
    time_resolved: Optional[Dict[str, Any]],
    risk_flags: list[str],
    llm_client: Any,
) -> Dict[str, Any]:
    if not config.ENABLE_LLM_COMPLETION or llm_client is None:
        return draft

    original = deepcopy(draft)
    attempts = max(1, min(int(config.LLM_COMPLETION_MAX_ATTEMPTS), 2))

    for _ in range(attempts):
        prompt = build_json_completion_prompt(
            draft=original,
            time_resolved=time_resolved,
            risk_flags=risk_flags,
            allowed_fields=config.LLM_COMPLETION_ALLOWED_FIELDS,
            protected_fields=config.LLM_COMPLETION_PROTECTED_FIELDS,
        )

        try:
            raw_response = _call_llm(
                llm_client=llm_client,
                prompt=prompt,
                timeout_seconds=config.LLM_COMPLETION_TIMEOUT_SECONDS,
            )
            response_json = json.loads(raw_response)
            completed = response_json.get("completed")
            if not isinstance(completed, dict):
                _record_enrichment_failure("missing_completed")
                continue
        except Exception:
            _record_enrichment_failure("llm_or_parse_failure")
            continue

        enforced = _enforce_allowed_and_protected(
            original=original,
            completed=completed,
            allowed_fields=config.LLM_COMPLETION_ALLOWED_FIELDS,
            protected_fields=config.LLM_COMPLETION_PROTECTED_FIELDS,
        )

        try:
            ok, _ = validate_normalized_request(enforced)
        except Exception:
            ok = False

        if ok:
            return enforced

        _record_enrichment_failure("schema_validation_failure")

    return original
