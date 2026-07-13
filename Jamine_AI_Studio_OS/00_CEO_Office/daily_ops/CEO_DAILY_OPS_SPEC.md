# CEO 每日營運機制 (Daily Ops Spec) v1.0

> 老闆 2026-07-13 頒布的數位部門 CEO 日常職責，落地到 Studio OS 的實作規格。
> 與每週一的營運週報**並行**：週報談生意（收入/KPI/決策），每日簡報談產線（進度/資源/成本）。

## 五大產品線對應表

| 規格中的產品線 | 對應到本 OS | 現況 |
|----------------|-------------|------|
| 電影 | JMD《潔米爸的占驗派紫微斗數》S01（05–10 層產線） | E01 製作中 |
| 漫畫 | 紫微漫畫（擴受眾用，餵書房筆記 IG/Threads） | 未啟動 |
| 短影音 | Content Factory 切片（IG Reel 主戰場） | 等 E01 定稿 |
| 長內容 | YouTube 長片＋書房筆記長文 | 未啟動 |
| 數位產品 | 紫微斗數筆記電子書（R2）＋未來語寶（R7） | 等原稿 |

## 每日流程（由每日排程觸發 CEO Agent 執行）

1. **讀取 `resources_daily.json`**：當日可用預算、老闆可投入時數、備註（老闆有空就更新，沒更新沿用前值）
2. **讀取故事考古部研究**：`daily_ops/research/` 內當日檔案（若無則跳過此項調整）
3. **重排五大產品線優先序**，更新甘特狀態
4. **成本檢查**：API/工具月消耗 vs 預算上限；超支項目列入待審單
5. **輸出**：
   - `daily_ops/ceo_roadmap.json`（純 JSON，規格如下）
   - `daily_ops/daily_report.md`（精簡簡報，覆寫更新）
6. **匯報紀律**：一切正常 → 只 commit 不打擾老闆；`budget_status=ALERT` 或 `requires_human_approval=true` → 主動通知

## ceo_roadmap.json 規格（老闆頒布，不可擅改）

```json
{
  "date": "YYYY-MM-DD",
  "project_priorities": ["產品A", "產品B"],
  "budget_status": "NORMAL/ALERT",
  "requires_human_approval": true/false
}
```

## 預算規則

- 月固定成本基線：NT$1,173（Claude 攤提 + GPT，見 `data/finance_ledger.csv`）
- 預算上限：`resources_daily.json` 的 `monthly_budget_cap_twd`（老闆定，預設 NT$3,000/月）
- 預估月消耗 > 上限 → `ALERT` + 超支項目進待審單，等老闆核准才續用

## 故事考古部（新設研究單位）

職責：挖掘紫微斗數的故事題材（古籍案例、命盤原型、民俗考據），產出餵給編劇與漫畫線。
產出放 `daily_ops/research/YYYY-MM-DD_題目.md`。已登錄於 AGENT_ROSTER。
