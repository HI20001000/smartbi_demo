from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional

from .metric_hint_retriever import load_metric_catalog, retrieve_metric_hints
from .time_parser import parse_time_phrase

SENSITIVE_TERMS = ["account_no", "full_name", "id_no", "phone", "email", "客戶明細", "帳戶明細", "明細"]


def _normalize_text(raw_text: str) -> str:
    text = raw_text.strip()
    text = re.sub(r"\s+", " ", text)
    replacements = {
        "期末餘額": "存款餘額",
        "transaction volume": "交易量",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _detect_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh-TW"
    return "en"


def _detect_intent(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["明細", "detail", "列出每個", "list all"]):
        return "detail_request"
    if any(k in t for k in ["趨勢", "trend"]):
        return "trend"
    if any(k in t for k in ["比較", "vs", "對比", "同比", "環比"]):
        return "comparison"
    if any(k in t for k in ["存款", "交易", "餘額", "kpi", "balance", "volume"]):
        return "kpi_query"
    return "out_of_scope"


def _risk_flags(text: str, time_resolved: Optional[dict]) -> Dict[str, object]:
    flags: List[str] = []
    lowered = text.lower()

    if any(term.lower() in lowered for term in SENSITIVE_TERMS):
        flags.append("pii_requested")

    if any(k in lowered for k in ["帳戶明細", "account detail", "account_id"]):
        flags.append("account_level_detail_requested")

    if any(k in lowered for k in ["客戶明細", "customer detail", "customer_id"]):
        flags.append("customer_level_detail_requested")

    if time_resolved is None:
        flags.append("missing_time_filter")

    if any(k in lowered for k in ["總餘額", "總和", "total"]) and not any(
        k in lowered for k in ["mop", "hkd", "幣別", "currency"]
    ):
        flags.append("cross_currency_aggregation_risk")

    dedup = list(dict.fromkeys(flags))
    return {
        "contains_sensitive_terms": len([f for f in dedup if "requested" in f]) > 0,
        "risk_flags": dedup,
    }


def build_normalized_request(
    raw_text: str,
    user_context: Dict[str, object],
    request_context: Dict[str, object],
    metrics_path: str = "semantic/metrics.yaml",
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    normalized_text = _normalize_text(raw_text)
    language = _detect_language(normalized_text)
    intent = _detect_intent(normalized_text)

    time_result = parse_time_phrase(normalized_text, now=now)

    catalog = load_metric_catalog(metrics_path)
    metric_hints = retrieve_metric_hints(normalized_text, catalog)

    risk = _risk_flags(normalized_text, time_result.resolved)

    missing: List[str] = []
    trace: List[str] = []

    if time_result.original_phrase:
        trace.append(f"R3:time_phrase={time_result.original_phrase}")
    else:
        missing.append("time_window")

    for hint in metric_hints:
        trace.append(f"R7:metric_hint={hint}")
    if not metric_hints:
        missing.append("metric")

    if risk["contains_sensitive_terms"]:
        trace.append("R5:sensitive_term_detected")

    return {
        "schema_version": "1.0",
        "request_id": str(request_context.get("request_id", "")),
        "request_context": {
            "request_ts": request_context.get("request_ts"),
            "timezone": request_context.get("timezone", "Asia/Macau"),
            "channel": request_context.get("channel", "api"),
        },
        "user_context": {
            "user_id": str(user_context.get("user_id", "")),
            "role": str(user_context.get("role", "")),
            "data_scope": list(user_context.get("data_scope", [])),
            "allowed_regions": list(user_context.get("allowed_regions", [])),
        },
        "query_context": {
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "language": language,
            "intent": intent,
        },
        "time_context": {
            "original_phrase": time_result.original_phrase,
            "resolved": time_result.resolved,
        },
        "risk_context": risk,
        "metric_hints": metric_hints,
        "normalization_trace": trace,
        "missing_required_fields": list(dict.fromkeys(missing)),
    }
