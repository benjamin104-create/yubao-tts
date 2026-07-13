# 00 — CEO Office（數位行銷執行長辦公室）

> 這一層在十二層架構**之上**。01–12 層負責「把作品做出來」，00 層負責「讓這間公司活下去、賺到錢」。
> 營運狀況不能只有支出沒有收入——這裡就是看緊這件事的地方。

---

## 這個模組有什麼

| 檔案 | 用途 | 更新頻率 |
|------|------|----------|
| [`CEO_CHARTER.md`](CEO_CHARTER.md) | CEO 職權章程：管什麼、怎麼決策、怎麼驅動各部門 Agent | 幾乎不改 |
| [`REVENUE_STRATEGY.md`](REVENUE_STRATEGY.md) | 收入策略：錢從哪裡來、先做哪個、平台門檻數據 | 每季檢討 |
| [`EXECUTION_ROADMAP.md`](EXECUTION_ROADMAP.md) | 90 天執行規劃：每週 Sprint + 各部門任務分派 | 每週更新 |
| [`OPERATIONS_LEDGER.md`](OPERATIONS_LEDGER.md) | 營運帳本使用說明（收入/支出/KPI 怎麼記） | 幾乎不改 |
| [`WEEKLY_REPORT_TEMPLATE.md`](WEEKLY_REPORT_TEMPLATE.md) | 週報固定格式 | 幾乎不改 |
| `data/finance_ledger.csv` | 收支流水帳（唯一真相來源） | 隨時記 |
| `data/kpi_weekly.csv` | 每週 KPI 快照（訂閱、觀看、名單、轉換） | 每週一筆 |
| `reports/` | 歷週週報存檔 | 每週一份 |
| `tools/weekly_report.py` | 從兩份 CSV 自動彙總出週報骨架 | — |

---

## 運作節奏

```
每天    （老闆）有支出/收入就記一筆 finance_ledger.csv
每週一  CEO Agent 彙整數據 → 產出週報 → 向老闆匯報
每週一  依週報結論，更新 EXECUTION_ROADMAP 的本週 Sprint
每月底  檢討收入策略：哪條收入線該加碼、哪條該停損
每季    REVENUE_STRATEGY 全面檢討升版
```

## 一條鐵律

> **每一筆支出，都要能回答：它在哪一條收入線上？**
> 回答不出來的支出，先凍結，進週報討論。
