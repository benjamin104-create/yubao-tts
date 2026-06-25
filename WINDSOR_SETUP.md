# Windsor.ai → Instagram Reels 審計　串接指南

這份說明帶你把 `windsor_audit.py` 接上真實的 Instagram 數據。
全程約 10 分鐘，做完你就有一個「每跑一次、就拿到一份毒舌審計報告」的管道。

---

## 一次性設定（約 10 分鐘）

### 步驟 1：在 Windsor.ai 連好 Instagram
1. 登入 <https://windsor.ai>（免費方案即可起步）。
2. 後台選 **Add data source → Instagram Insights**（若你是商業帳號也可選 *Instagram Business*）。
3. 用 Facebook/Meta 登入，授權你要分析的 IG 帳號。
   - ⚠️ IG 必須是**商業帳號或創作者帳號**（個人帳號 Meta 不給 Insights）。
   - 同時要把 IG 連到一個 Facebook 粉專，否則 Insights API 拉不到 Reels。

### 步驟 2：拿 API key
1. 後台找 **API / "Get data"**（通常在 onboarding 或 Account 頁）。
2. 複製你的 `api_key`。它會出現在一條長得像這樣的網址裡：
   ```
   https://connectors.windsor.ai/instagram?api_key=XXXXXXXX&date_preset=last_7d&fields=...
   ```
   你要的就是 `api_key=` 後面那串。

### 步驟 3：設環境變數
```bash
export WINDSOR_API_KEY="把你的金鑰貼這裡"
# 連接器預設就是 instagram，一般不用改。
```
> 想長期保存可寫進 `.env` 或 shell profile。**金鑰不要 commit 進 git**（本 repo 的 `.gitignore` 已幫你擋掉 `.env`）。

---

## 跑審計

```bash
# 先用假資料確認程式能動（不需金鑰）
python windsor_audit.py --self-test

# 正式：拉最近 30 天，輸出 TOP 3 排行榜
python windsor_audit.py

# 想看更多
python windsor_audit.py --days 60 --top 5

# 只想看原始資料、debug 欄位命名
python windsor_audit.py --raw-only
```

跑完會在 `audit_output/` 產生三個檔：

| 檔案 | 用途 |
|---|---|
| `audit_*.md` | 人看的報告（排行榜＋總覽） |
| `audit_*.csv` | 丟 Excel / Google Sheet |
| `audit_*.json` | **丟回對話給 AI 夥伴做深度診斷** |

---

## 然後呢？把報告丟回來

把 `audit_*.md` 或 `audit_*.json` 貼回我們的對話，我會：
- 逐支拆解 Hook（黃金前三秒）、內容架構、拍攝形式
- 指出流量在第幾秒流失、互動為什麼斷崖
- 點出你自己沒意識到的最大盲點
- 給 3 個可立即執行的 Action Plan

---

## 疑難排解

| 症狀 | 八成原因 | 怎麼修 |
|---|---|---|
| `沒有 WINDSOR_API_KEY` | 沒設環境變數 | 重做步驟 3 |
| `HTTP 401 / 403` | 金鑰錯或過期 | 回 Windsor 後台重拿 |
| 抓到 0 支 Reels | 連接器或欄位名不符 | 跑 `--raw-only` 看實際欄名，再用 `WINDSOR_FIELDS` 覆寫 |
| 觀看數對不上 IG 後台 | Windsor 欄位命名差異 | 用 `--raw-only` 確認是 `video_views` 還是 `reels_plays`，必要時調 `FIELD_ALIASES` |
| Reels 沒被認出來 | `media_product_type` 命名不同 | 看 raw.json 的型別欄位，調整 `is_reel()` |

> 不同帳號的 Windsor 欄位命名會有差異，程式已用「別名表 + 寬鬆判斷」盡量吸收。
> 真的對不上時，`--raw-only` 拉一份原始 JSON 給我，我幫你把欄位對映調準。
