# normalize_input() 規則草案（Draft v1）

## 目標
將自然語言輸入轉成 `NormalizedRequest` JSON，供後續 metric retrieval / semantic plan / validator 使用。

## 規則優先順序
1. **安全規則優先**（敏感詞、明細請求）
2. **時間規則**（若缺少時間，標記缺失）
3. **語意詞典規則**（metric aliases / 維度詞）
4. **LLM 補全規則**（僅處理規則未覆蓋部分）

## 規則清單

### R1 文本清理
- trim 前後空白
- 全形數字/符號轉半形
- 連續空白合併成單一空白

### R2 語言與術語正規化
- 同義詞映射（例："期末餘額" -> "存款餘額"）
- 中英術語對齊（例："transaction volume" -> "交易量"）

### R3 時間詞解析
- 今天/昨日/昨天/近7天/本月/今年/上月
- 解析為 `time_context.resolved`（type/start_date/end_date）
- 無法解析時，`missing_required_fields += ["time_window"]`

### R4 維度提示抽取
- region / currency / channel / branch 等關鍵詞提取
- 僅提取高置信度（規則詞典命中）

### R5 敏感與越權檢測
- 如命中 `account_no/full_name/id_no/phone/email` -> `contains_sensitive_terms=true`
- 若語句要求明細（例如"列出每個帳戶"） -> `risk_flags += ["account_level_detail_requested"]`

### R6 意圖分類
- `kpi_query`：聚合 KPI 查詢
- `comparison`：同比/環比/A vs B
- `trend`：時間序列趨勢
- `detail_request`：明細資料請求
- `out_of_scope`：非資料查詢

### R7 候選 metric hint
- 使用 `metrics.yaml` 的 aliases/name/definition 進行關鍵詞召回
- 輸出 `metric_hints`（可多個，依分數排序）

### R8 LLM 補全
- 僅在規則無法判定時使用
- 限制只回傳符合 schema 的 JSON
- 禁止新增 schema 外欄位

## 失敗處理
- 若 JSON 不合法或不符合 schema：
  1. 重試一次（帶 validation error）
  2. 仍失敗則 fallback 至純規則輸出 + `needs_clarification`

## 追蹤欄位
- `normalization_trace` 記錄命中規則，如：
  - `R3:time_phrase=昨天`
  - `R5:sensitive_term=account_no`
  - `R7:metric_hint=metric.deposit.total_end_balance`
