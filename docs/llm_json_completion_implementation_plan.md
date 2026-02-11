# LLM 輔助補全 Normalized JSON：實作計劃（v1）

## 1. 現況判斷

目前 **尚未實作** LLM 輔助補全 normalized JSON：

- `normalize_input(...)` 只做兩件事：
  1) `build_normalized_request(...)`
  2) `validate_normalized_request(...)`
- 中間沒有任何 LLM 補全步驟。

因此現在流程是 deterministic rule-based normalize + validator gate，不包含 AI 修補。

---

## 2. 建議落點（放在 validate 前）

建議主路徑：

1. `build_normalized_request(...)` 產生初稿 JSON。
2. `llm_complete_normalized_request(...)` 嘗試補齊可推斷但缺漏欄位。
3. `validate_normalized_request(...)` 做最終硬驗證。

另外建議 recovery 路徑：

- 若第一次 validate 失敗，可將 `errors + JSON` 餵給 LLM 再修一次，修完後必須 re-validate。

---

## 3. 模組拆分建議

### 3.1 新增檔案：`src/normalization/llm_enricher.py`

目的：封裝 LLM 補全能力，避免污染 rule engine。

建議介面：

```python
def llm_complete_normalized_request(
    draft: dict,
    *,
    user_raw_text: str,
    timeout_s: float = 3.0,
) -> dict:
    """回傳補全後 JSON（若失敗可回傳原 draft）。"""
```

職責：

- 構造受控 prompt（只允許補欄位，不允許覆寫高信心欄位）。
- 呼叫既有 LLM 客戶端（可沿用 `chat.py` 的配置模式）。
- 嚴格解析與保底（解析失敗就 fallback 原 draft）。

### 3.2 新增檔案：`src/normalization/llm_prompt.py`

目的：集中存放 JSON 補全 prompt template 與系統約束。

重點約束：

- 只能輸出 JSON，不得輸出說明文字。
- 不可變更 `schema_version/request_id/user_context/request_context`。
- 對推斷欄位標記來源（例如在 `normalization_trace` 補 `LLM:...`）。

### 3.3 調整檔案：`src/normalization/normalizer.py`

新增可選參數（預設關閉）：

- `enable_llm_completion: bool = False`

流程調整：

- build 後，若開啟開關才進 LLM 補全。
- 補全後統一走 validate。
- validate fail 可選擇再修一次（可由 `max_repair_rounds=1` 控制）。

### 3.4 新增檔案：`src/normalization/config.py`

目的：集中管理功能開關與安全策略。

例如：

- `ENABLE_LLM_COMPLETION`
- `LLM_COMPLETION_TIMEOUT_S`
- `LLM_MAX_REPAIR_ROUNDS`
- `LLM_ALLOWED_FIELDS_TO_FILL`

---

## 4. 驗證與測試建議

### 4.1 新增測試：`tests/normalization/test_llm_enricher.py`

情境：

- LLM 成功補齊 `missing_required_fields`。
- LLM 回傳無效 JSON（應 fallback 原 draft）。
- LLM 試圖改動受保護欄位（應拒收或回滾）。

### 4.2 調整測試：`tests/normalization/test_normalizer.py`

新增：

- `enable_llm_completion=False` 時結果與既有行為一致（回歸保證）。
- `enable_llm_completion=True` 時，補全後可通過 validator。

---

## 5. 文件新增建議（你問的「新增甚麼文件」）

建議新增/更新以下文件：

1. **本文件** `docs/llm_json_completion_implementation_plan.md`
   - 記錄架構設計、風險與落地步驟。
2. `docs/llm_json_completion_prompt_contract.md`
   - 定義 prompt input/output contract、可改欄位白名單。
3. `docs/llm_json_completion_failure_playbook.md`
   - 記錄失敗排查（格式錯誤、超時、越權覆寫、幻覺）。
4. 更新根目錄 `流程說明.md`
   - 增補「可選 LLM 補全階段」的流程圖與開關說明。

---

## 6. 風險控制

- **白名單欄位補全**：只允許補 `metric_hints/time_context/missing_required_fields/normalization_trace` 等欄位。
- **不可覆寫欄位**：`request_id/schema_version/user_context/request_context`。
- **雙重驗證**：LLM 後一定要 validate；失敗直接回退規則輸出或報錯。
- **觀測性**：把 LLM 補全前後 diff 與耗時打 log。

---

## 7. 建議實作順序

1. 先做 `llm_enricher.py` 的 stub + fallback，不接真 LLM（確保可測）。
2. 接上真實 LLM client，先灰度開關（預設 off）。
3. 補齊測試與 failure playbook。
4. 小流量觀測後再開預設。

