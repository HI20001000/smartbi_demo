from __future__ import annotations

ENABLE_LLM_COMPLETION = False
LLM_COMPLETION_TIMEOUT_SECONDS = 5
LLM_COMPLETION_ALLOWED_FIELDS = (
    "intent",
    "time_context",
    "metric_hints",
    "filter_hints",
    "missing_required_fields",
)
LLM_COMPLETION_PROTECTED_FIELDS = (
    "raw_text",
    "request_context",
    "user_context",
)
LLM_COMPLETION_MAX_ATTEMPTS = 1
