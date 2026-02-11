from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from .llm_enricher import enrich_draft
from .rule_engine import build_normalized_request
from .validator import validate_normalized_request


class NormalizationError(Exception):
    pass


def _to_pretty_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _diff_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    if before == after:
        return []

    if isinstance(before, dict) and isinstance(after, dict):
        paths: list[str] = []
        keys = set(before.keys()) | set(after.keys())
        for key in sorted(keys):
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in before:
                paths.append(f"{next_prefix} (added)")
                continue
            if key not in after:
                paths.append(f"{next_prefix} (removed)")
                continue
            paths.extend(_diff_paths(before[key], after[key], next_prefix))
        return paths

    if isinstance(before, list) and isinstance(after, list):
        max_len = max(len(before), len(after))
        paths: list[str] = []
        for idx in range(max_len):
            next_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            if idx >= len(before):
                paths.append(f"{next_prefix} (added)")
                continue
            if idx >= len(after):
                paths.append(f"{next_prefix} (removed)")
                continue
            paths.extend(_diff_paths(before[idx], after[idx], next_prefix))
        return paths

    return [prefix or "<root>"]


def _print_stage(stage: str, payload: Any) -> None:
    print(f"[normalize_input] {stage} JSON:")
    print(_to_pretty_json(payload))


def _print_stage_diff(label: str, before: Any, after: Any) -> None:
    paths = _diff_paths(before, after)
    print(f"[normalize_input] {label} diff_paths: {paths if paths else ['<no_changes>']}")


def normalize_input(
    raw_text: str,
    user_context: Dict[str, object],
    request_context: Dict[str, object],
    *,
    metrics_path: str = "semantic/metrics.yaml",
    now: Optional[datetime] = None,
    llm_client=None,
    debug: bool = False,
) -> Dict[str, object]:
    built = build_normalized_request(
        raw_text=raw_text,
        user_context=user_context,
        request_context=request_context,
        metrics_path=metrics_path,
        now=now,
    )

    if debug:
        _print_stage("build_normalized_request", built)

    enriched = enrich_draft(
        draft=built,
        time_resolved=built.get("time_context", {}).get("resolved") if isinstance(built.get("time_context"), dict) else None,
        risk_flags=built.get("risk_context", {}).get("risk_flags", []) if isinstance(built.get("risk_context"), dict) else [],
        llm_client=llm_client,
    )

    if debug:
        _print_stage("enrich_draft", enriched)
        _print_stage_diff("build -> enrich", built, enriched)

    ok, errors = validate_normalized_request(enriched)

    if debug:
        validation_payload = {
            "ok": ok,
            "errors": errors,
            "validated": enriched,
        }
        _print_stage("validate_normalized_request", validation_payload)

    if not ok:
        raise NormalizationError("; ".join(errors))

    return enriched
