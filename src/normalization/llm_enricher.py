from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any, Dict, Iterable, Optional

from .llm_prompt import build_json_completion_prompt
from .validator import validate_normalized_request


def _record_enrichment_failure(_reason: str) -> None:
    """Hook for logging/metrics; intentionally no-op by default."""


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    parts = tuple(item.strip() for item in raw.split(",") if item.strip())
    return parts or default


def _completion_enabled() -> bool:
    return _env_bool("ENABLE_LLM_COMPLETION", True)


def _completion_timeout_seconds() -> int:
    return _env_int("LLM_COMPLETION_TIMEOUT_SECONDS", 5)


def _completion_allowed_fields() -> tuple[str, ...]:
    return _env_csv(
        "LLM_COMPLETION_ALLOWED_FIELDS",
        ("query_context", "time_context", "metric_hints", "filter_hints", "missing_required_fields"),
    )


def _completion_protected_fields() -> tuple[str, ...]:
    return _env_csv(
        "LLM_COMPLETION_PROTECTED_FIELDS",
        ("request_id", "request_context", "user_context", "schema_version"),
    )


def _completion_max_attempts() -> int:
    return max(1, min(_env_int("LLM_COMPLETION_MAX_ATTEMPTS", 1), 2))


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
    if not _completion_enabled() or llm_client is None:
        return draft

    original = deepcopy(draft)

    for _ in range(_completion_max_attempts()):
        prompt = build_json_completion_prompt(
            draft=original,
            time_resolved=time_resolved,
            risk_flags=risk_flags,
            allowed_fields=_completion_allowed_fields(),
            protected_fields=_completion_protected_fields(),
        )

        try:
            raw_response = _call_llm(
                llm_client=llm_client,
                prompt=prompt,
                timeout_seconds=_completion_timeout_seconds(),
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
            allowed_fields=_completion_allowed_fields(),
            protected_fields=_completion_protected_fields(),
        )

        try:
            ok, _ = validate_normalized_request(enforced)
        except Exception:
            ok = False

        if ok:
            return enforced

        _record_enrichment_failure("schema_validation_failure")

    return original
