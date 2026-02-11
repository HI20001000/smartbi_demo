# main.py
from chat import SmartBIChat

def main():
    bot = SmartBIChat(load_env=True)
    session_id = "smartbi-cli"

    print("=== SmartBI CLI Chat (LangChain + Memory) ===")
    print("指令：/exit  /reset  /history")
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

        try:
            ans = bot.invoke(session_id, user_text)
            print("AI>", ans)
        except Exception as e:
            print("[error]", repr(e))

if __name__ == "__main__":
    main()
