import json

from src.normalization import llm_enricher


def test_success_path_fills_missing_allowed_fields(monkeypatch):
    monkeypatch.setattr(llm_enricher.config, "ENABLE_LLM_COMPLETION", True)
    monkeypatch.setattr(llm_enricher.config, "LLM_COMPLETION_ALLOWED_FIELDS", ("metric_hints",))
    monkeypatch.setattr(llm_enricher.config, "LLM_COMPLETION_PROTECTED_FIELDS", ("raw_text",))
    monkeypatch.setattr(llm_enricher, "validate_normalized_request", lambda payload: (True, []))

    draft = {"raw_text": "query", "metric_hints": []}

    def stub_client(_prompt, timeout):
        assert timeout > 0
        return json.dumps({"completed": {"metric_hints": ["metric.deposit.total_end_balance"]}})

    enriched = llm_enricher.enrich_draft(draft, time_resolved=None, risk_flags=[], llm_client=stub_client)

    assert enriched["metric_hints"] == ["metric.deposit.total_end_balance"]
    assert enriched["raw_text"] == "query"


def test_invalid_json_response_falls_back_to_original(monkeypatch):
    monkeypatch.setattr(llm_enricher.config, "ENABLE_LLM_COMPLETION", True)
    monkeypatch.setattr(llm_enricher, "validate_normalized_request", lambda payload: (True, []))

    draft = {"raw_text": "query", "metric_hints": []}

    def stub_client(_prompt, timeout):
        return "not-json"

    enriched = llm_enricher.enrich_draft(draft, time_resolved=None, risk_flags=[], llm_client=stub_client)
    assert enriched == draft


def test_overwrite_attempt_on_protected_field_is_reverted(monkeypatch):
    monkeypatch.setattr(llm_enricher.config, "ENABLE_LLM_COMPLETION", True)
    monkeypatch.setattr(llm_enricher.config, "LLM_COMPLETION_ALLOWED_FIELDS", ("metric_hints", "raw_text"))
    monkeypatch.setattr(llm_enricher.config, "LLM_COMPLETION_PROTECTED_FIELDS", ("raw_text",))
    monkeypatch.setattr(llm_enricher, "validate_normalized_request", lambda payload: (True, []))

    draft = {"raw_text": "original", "metric_hints": []}

    def stub_client(_prompt, timeout):
        return json.dumps({"completed": {"raw_text": "tampered", "metric_hints": ["m1"]}})

    enriched = llm_enricher.enrich_draft(draft, time_resolved=None, risk_flags=[], llm_client=stub_client)
    assert enriched["raw_text"] == "original"
    assert enriched["metric_hints"] == ["m1"]


def test_non_allowed_field_modification_is_reverted(monkeypatch):
    monkeypatch.setattr(llm_enricher.config, "ENABLE_LLM_COMPLETION", True)
    monkeypatch.setattr(llm_enricher.config, "LLM_COMPLETION_ALLOWED_FIELDS", ("metric_hints",))
    monkeypatch.setattr(llm_enricher.config, "LLM_COMPLETION_PROTECTED_FIELDS", ("raw_text",))
    monkeypatch.setattr(llm_enricher, "validate_normalized_request", lambda payload: (True, []))

    draft = {"raw_text": "original", "metric_hints": [], "intent": "kpi_query"}

    def stub_client(_prompt, timeout):
        return json.dumps(
            {
                "completed": {
                    "metric_hints": ["m1"],
                    "intent": "detail_request",
                }
            }
        )

    enriched = llm_enricher.enrich_draft(draft, time_resolved=None, risk_flags=[], llm_client=stub_client)
    assert enriched["metric_hints"] == ["m1"]
    assert enriched["intent"] == "kpi_query"
