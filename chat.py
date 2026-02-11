# chat.py (smartbi_chat.py)
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


@dataclass
class ChatConfig:
    """
    統一管理環境變數 key 與模型參數，避免散落在程式各處。
    """
    # ===== 環境變數 key（.env 裡會提供）=====
    base_url_key: str = "LLM_BASE_URL"
    model_key: str = "LLM_MODEL"
    api_key_key: str = "LLM_API_KEY"
    system_prompt_key: str = "SYSTEM_PROMPT"

    # ===== 模型參數 =====
    temperature: float = 0.3

    # ===== RunnableWithMessageHistory 需要的 key =====
    input_messages_key: str = "input"
    history_messages_key: str = "history"


def _get_env_or_die(key: str) -> str:
    """
    讀取環境變數；若缺少則輸出報錯格式並直接結束程式。
    """
    val = os.getenv(key)
    if not val:
        print(f"[Env error]: Missing environment variable '{key}', please check your .env file.")
        sys.exit(1)
    return val


def build_llm(cfg: ChatConfig) -> ChatOpenAI:
    """
    建立 LLM 連線設定（ChatOpenAI）。
    依賴 .env 提供：base_url / model / api_key。
    """
    base_url = _get_env_or_die(cfg.base_url_key)
    model = _get_env_or_die(cfg.model_key)
    api_key = _get_env_or_die(cfg.api_key_key)

    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=cfg.temperature,
    )


def build_chain(llm: ChatOpenAI, cfg: ChatConfig):
    """
    建立 prompt | llm 的管線（chain）。
    - system：全域規則/人設/任務說明（從 SYSTEM_PROMPT 讀取）
    - history：由 RunnableWithMessageHistory 自動注入
    - human：當下使用者輸入
    """
    system_prompt = _get_env_or_die(cfg.system_prompt_key)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name=cfg.history_messages_key),
            ("human", "{input}"),
        ]
    )

    # LangChain pipeline：先套 prompt -> messages -> 丟給 llm -> 回傳 AIMessage
    return prompt | llm


class SmartBIChat:
    """
    可重用的 Chat 包裝器：
    - chain：prompt | llm
    - memory：以 session_id 分流保存對話（InMemoryChatMessageHistory）
    - chat：RunnableWithMessageHistory，把 history 自動串進 chain
    """

    def __init__(
        self,
        cfg: Optional[ChatConfig] = None,
        *,
        load_env: bool = True,
        test_connection: bool = True,
    ):
        """
        :param load_env: 是否自動 load_dotenv() 讀取 .env
        :param test_connection: 是否在初始化時用 "ping" 測試 LLM + prompt 是否可用
        """
        self.cfg = cfg or ChatConfig()

        # 讀取 .env（例如本地開發情境很需要；若部署環境用外部注入 env，可設 False）
        if load_env:
            load_dotenv()

        # 以 session_id 管理記憶：同一個 session_id 共享上下文
        self.store: Dict[str, InMemoryChatMessageHistory] = {}

        # 建立 llm 與 chain
        self.llm = build_llm(self.cfg)
        self.chain = build_chain(self.llm, self.cfg)

        # 測試 chain 連線（保留你原本的報錯日誌）
        if test_connection:
            try:
                _ = self.chain.invoke({self.cfg.input_messages_key: "ping", self.cfg.history_messages_key: []})
            except Exception as e:
                print("[Chain error]: ", repr(e))
                # 初始化直接失敗通常是設定問題；這裡選擇直接結束，行為跟你原先一致
                sys.exit(1)

        def get_history(session_id: str) -> InMemoryChatMessageHistory:
            """
            取得/建立指定 session 的對話歷史。
            """
            if session_id not in self.store:
                self.store[session_id] = InMemoryChatMessageHistory()
            return self.store[session_id]

        self._get_history: Callable[[str], InMemoryChatMessageHistory] = get_history

        # 包裝成可自動帶記憶的 chat runnable
        self.chat = RunnableWithMessageHistory(
            self.chain,
            get_session_history=self._get_history,
            input_messages_key=self.cfg.input_messages_key,
            history_messages_key=self.cfg.history_messages_key,
        )

    def invoke(self, session_id: str, user_text: str) -> str:
        """
        送出一段使用者輸入並取得模型回覆（字串）。
        - session_id：決定記憶要存在哪一段對話
        """
        try:
            out = self.chat.invoke(
                {self.cfg.input_messages_key: user_text},
                config={"configurable": {"session_id": session_id}},
            )
            return out.content
        except Exception as e:
            # 保留你 CLI 風格的錯誤日誌（讓上層也能選擇怎麼處理）
            print("[error]", repr(e))
            raise

    def reset(self, session_id: str) -> None:
        """
        清空某個 session 的對話記憶。
        """
        self.store[session_id] = InMemoryChatMessageHistory()

    def history(self, session_id: str):
        """
        取得某個 session 的完整訊息列表（可用於 /history 指令）。
        """
        return list(self._get_history(session_id).messages)

    def ping(self) -> str:
        """
        手動測試連線（會走 chain，不帶任何 history）。
        """
        try:
            out = self.chain.invoke(
                {self.cfg.input_messages_key: "ping", self.cfg.history_messages_key: []}
            )
            return out.content
        except Exception as e:
            print("[Chain error]: ", repr(e))
            raise
