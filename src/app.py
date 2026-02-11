from __future__ import annotations

import json
from datetime import datetime

from chat import SmartBIChat
from src.normalization import NormalizationError, normalize_input


def run_cli() -> None:
    bot = SmartBIChat(load_env=True)
    session_id = "smartbi-cli"

    print("=== SmartBI CLI Chat (LangChain + Memory) ===")
    print("指令：/exit  /reset  /history  /normalize <text>  /normalize-debug <text>")
    print("-------------------------------------------")

    while True:
        try:
            user_text = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_text:
            continue

        if user_text == "/exit":
            print("Bye.")
            break

        if user_text == "/reset":
            bot.reset(session_id)
            print("已清空對話記憶。")
            continue

        if user_text == "/history":
            h = bot.history(session_id)
            if not h:
                print("(empty)")
            else:
                for i, m in enumerate(h, 1):
                    role = "AI" if m.type == "ai" else "You"
                    print(f"{i:02d} {role}: {m.content}")
            continue

        text_for_normalize = user_text
        normalize_only = False
        debug_normalization = False
        if user_text.startswith("/normalize-debug "):
            text_for_normalize = user_text[len("/normalize-debug ") :].strip()
            normalize_only = True
            debug_normalization = True
        elif user_text.startswith("/normalize "):
            text_for_normalize = user_text[len("/normalize ") :].strip()
            normalize_only = True
            debug_normalization = True

        request_context = {
            "request_id": f"req-{int(datetime.now().timestamp())}",
            "request_ts": datetime.now().astimezone().isoformat(),
            "timezone": "Asia/Macau",
            "channel": "cli",
        }
        user_context = {
            "user_id": "smartbi-cli-user",
            "role": "analyst",
            "data_scope": ["AGGREGATED_ONLY"],
            "allowed_regions": ["澳門半島", "氹仔", "路氹城", "路環"],
        }

        try:
            normalized = normalize_input(
                text_for_normalize,
                user_context,
                request_context,
                debug=debug_normalization,
            )
            print("Normalized>")
            print(json.dumps(normalized, ensure_ascii=False, indent=2))
        except NormalizationError as e:
            print("[normalize error]", str(e))
            continue

        if normalize_only:
            continue

        try:
            ans = bot.invoke(session_id, user_text)
            print("AI>", ans)
        except Exception as e:
            print("[error]", repr(e))
