from datetime import datetime

from src.normalization import normalizer


def test_normalize_input_debug_prints_stage_json_and_diff(monkeypatch, capsys):
    built = {
        "schema_version": "1.0",
        "request_context": {"request_ts": "2026-01-01T00:00:00+08:00", "timezone": "Asia/Macau"},
        "query_context": {"language": "zh-TW", "intent": "out_of_scope"},
        "time_context": {"resolved": None},
        "risk_context": {"risk_flags": []},
        "missing_required_fields": [],
    }
    enriched = {
        **built,
        "query_context": {"language": "zh-TW", "intent": "kpi_query"},
    }

    monkeypatch.setattr(normalizer, "build_normalized_request", lambda **kwargs: built)
    monkeypatch.setattr(normalizer, "enrich_draft", lambda **kwargs: enriched)
    monkeypatch.setattr(normalizer, "validate_normalized_request", lambda payload: (True, []))

    result = normalizer.normalize_input(
        raw_text="查詢",
        user_context={},
        request_context={},
        now=datetime(2026, 1, 1),
        llm_client=object(),
        debug=True,
    )

    out = capsys.readouterr().out
    assert "[normalize_input] build_normalized_request JSON:" in out
    assert "[normalize_input] enrich_draft JSON:" in out
    assert "[normalize_input] build -> enrich diff_paths:" in out
    assert "query_context.intent" in out
    assert "[normalize_input] validate_normalized_request JSON:" in out
    assert result == enriched
