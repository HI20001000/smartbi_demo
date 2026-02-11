# SmartBI 規則集（強制）

## 1. 資安/合規
- 禁止輸出任何 PII 明細：full_name、id_no、phone、email、birth_date
- 禁止輸出識別性強的 ID：account_no、customer_no、loan_no（如需定位只能用內部 ID 且不可回傳明細）
- 交易/帳戶/客戶層級明細一律拒絕；只允許聚合結果（分行/區域/日期/渠道等）

## 2. SQL 安全
- 只允許 SELECT
- 禁止多語句、禁止 ; 
- 禁止 DROP/ALTER/TRUNCATE/INSERT/UPDATE/DELETE
- 必須包含日期條件（biz_date 或 yyyy_mm）
- 必須包含 LIMIT（除非是 GROUP BY 的聚合查詢）

## 3. 輸出格式
- 先回覆：需求理解 + 採用的指標口徑 + SQL（若適用）+ 注意事項
- 若需求越權或涉及敏感明細：提供可替代的聚合口徑與示例查詢
