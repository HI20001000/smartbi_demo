from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace


class _DummyLLM:
    def __init__(self):
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(content='{"completed": {}}')


class _DummyBot:
    def __init__(self, *args, **kwargs):
        del args, kwargs
        self.llm = _DummyLLM()

    def reset(self, session_id: str):
        del session_id

    def history(self, session_id: str):
        del session_id
        return []

    def invoke(self, session_id: str, user_text: str) -> str:
        del session_id, user_text
        return "ok"


def _load_app_with_dummy_chat(monkeypatch):
    fake_chat = ModuleType("chat")
    fake_chat.SmartBIChat = _DummyBot
    monkeypatch.setitem(sys.modules, "chat", fake_chat)
    sys.modules.pop("src.app", None)
    return importlib.import_module("src.app")


def test_make_llm_completion_client_uses_bot_llm_invoke(monkeypatch):
    app = _load_app_with_dummy_chat(monkeypatch)

    bot = _DummyBot()
    client = app._make_llm_completion_client(bot)

    result = client("prompt text", timeout=1)

    assert result == '{"completed": {}}'
    assert bot.llm.prompts == ["prompt text"]


def test_run_cli_normalize_passes_llm_client(monkeypatch, capsys):
    app = _load_app_with_dummy_chat(monkeypatch)
    captured = {}

    def _fake_normalize_input(raw_text, user_context, request_context, debug=False, llm_client=None):
        captured["raw_text"] = raw_text
        captured["user_context"] = user_context
        captured["request_context"] = request_context
        captured["debug"] = debug
        captured["llm_client"] = llm_client
        return {
            "schema_version": "1.0",
            "request_context": request_context,
            "user_context": user_context,
            "query_context": {"raw_text": raw_text},
        }

    monkeypatch.setattr(app, "normalize_input", _fake_normalize_input)

    inputs = iter(["/normalize 查詢存款", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    app.run_cli()

    assert captured["raw_text"] == "查詢存款"
    assert captured["debug"] is True
    assert callable(captured["llm_client"])

    completion = captured["llm_client"]("hello")
    assert completion == '{"completed": {}}'

    out = capsys.readouterr().out
    assert "Normalized>" in out
