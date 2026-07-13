# 營運帳本使用說明 (Operations Ledger)

> 兩份 CSV 是整個 CEO Office 的數據地基。**記錄不求精美，只求誠實、不漏。**

---

## 1. `data/finance_ledger.csv` — 收支流水帳

每一筆收入或支出記一列：

| 欄位 | 說明 | 範例 |
|------|------|------|
| `date` | YYYY-MM-DD | 2026-07-13 |
| `type` | `income` 或 `expense` | expense |
| `category` | 分類（見下方分類表） | ai_tools |
| `item` | 具體項目 | Kling 月訂閱 |
| `amount_twd` | 金額（新台幣，支出記正數） | 800 |
| `revenue_line` | 對應收入線（R1–R9；支出也要填「這筆錢養哪條線」，答不出來填 `unassigned`） | R4 |
| `note` | 備註 | — |

**分類表**：
- 支出：`ai_tools`（生成工具）、`infra`（主機/網域）、`software`（剪輯等軟體）、`marketing`（廣告投放）、`fees`（金流手續費）、`other`
- 收入：`service`（R1 對談）、`digital_product`（R2/R9）、`subscription`（R3/R6）、`platform`（R4 分潤）、`sponsor`（R5）、`saas`（R7）

## 2. `data/kpi_weekly.csv` — 每週 KPI 快照

每週一記一列（上週日為快照日）：

| 欄位 | 說明 |
|------|------|
| `week` | ISO 週，如 2026-W29 |
| `yt_subs` / `yt_watch_hours` | YouTube 訂閱數 / 累積有效觀看時數（營利門檻進度） |
| `tiktok_followers` | TikTok 粉絲數 |
| `ig_milkmoney_followers` / `ig_bookroom_followers` | IG 兩帳號分開記：奶粉錢奮鬥記（親子受眾→語寶潛在客）／書房筆記（命理受眾→R1/R2 潛在客） |
| `list_size` | 自有名單（LINE + Email 合計）← North Star |
| `posts_published` | 本週實際發佈則數 |
| `income_twd` / `expense_twd` | 本週收支（由 ledger 彙總，可用工具算） |
| `note` | 大事記 |

## 3. 自動彙總

```bash
python Jamine_AI_Studio_OS/00_CEO_Office/tools/weekly_report.py 2026-W29
```

會讀兩份 CSV，輸出該週的收支彙總與 KPI 對照，作為週報的數據段落。

## 4. 誠實原則

- 沒有數據就寫 `0` 或留白，**不要估一個好看的數字**。
- 支出漏記比高支出更危險——漏記會讓「淨利」變成幻覺。
- 平台數據每週一從各平台後台抄一次即可，不用天天看。
