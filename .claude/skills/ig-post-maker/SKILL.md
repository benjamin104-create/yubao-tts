---
name: ig-post-maker
description: 把《潔米爸》劇本／分鏡轉成 IG 貼文包（輪播貼文、Reels 腳本、貼文文案 + hashtag），並自動跑 Brand Bible 品牌護欄稽核。使用時機：使用者要做 IG 貼文、輪播、Reels、社群切片、內容拆解、貼文文案，或提到 11_Publish / Content Factory / Marketing Manager Agent。
---

# IG 貼文製造機（Marketing Manager Agent）

把一集作品拆成 IG 內容，落實 `Jamine_AI_Studio_OS/11_Publish/CONTENT_FACTORY.md` 的槓桿層。
**你扮演的是 AGENT_ROSTER 裡的 📣 Marketing Manager。**

## 開工前必讀（順序不可換）

1. `Jamine_AI_Studio_OS/01_Brand/BRAND_BIBLE.md` — 最高法律，尤其第五節「絕對禁止」。
2. `Jamine_AI_Studio_OS/02_World/` — 世界觀色彩與冷暖節奏。
3. `Jamine_AI_Studio_OS/03_Characters/` — 出場角色設定（貼文金句別寫出角色不會說的話）。
4. `Jamine_AI_Studio_OS/11_Publish/CONTENT_FACTORY.md` — 各格式規格與命名規範。

## 流程

### 1. 先跑程式，拿到草稿

```bash
cd Jamine_AI_Studio_OS/automation
python3 ig_post_maker.py ../05_Scripts/JMD/S01/E01/JMD_S01_E01_script_v01.md \
    --storyboard ../06_Storyboard/JMD/S01/E01/JMD_S01_E01_storyboard_v01.md
```

產出到 `11_Publish/IG/{PROJECT}/S{季}/E{集}/`：

| 檔案 | 內容 |
|------|------|
| `…_carousel_01_v01.md` | 輪播貼文（4:5，6–10 卡：封面 → 金句 → 收束 → CTA），每卡附視覺指示 |
| `…_reels_01_v01.md` | Reels 腳本（9:16，15–60s，前 3 秒鉤子 + 分鏡選段 + 收尾） |
| `…_caption_01_v01.md` | 可直接貼的文案 + 備用鉤子（A/B）+ hashtag |
| `_brand_guard_report.md` | 品牌護欄稽核（有阻斷項時程式回傳非 0） |

常用參數：`--cards 6~10`、`--formats carousel,reels,caption`、`--out DIR`、
`--index/--version`（同一集出第二版切片時用）、`--dry-run`（只看不寫檔）。

沒有分鏡表也能跑，只是視覺指示與 Reels 選段會退化成劇本層級。

### 2. 再用人的判斷潤稿（這步不能省）

程式做的是「抽金句、對鏡頭、套規格、掃禁用詞」，**創作判斷是你的事**：

- **金句**：確認每句離開上下文仍讀得懂；被截斷或指涉不明的換掉。
- **封面鉤子**：可以提問，不可以恐嚇。用「你今天替自己選了什麼？」不用「不看會後悔」。
- **順序**：沿劇本情緒弧線，**一定收在釋懷**，不停在焦慮。
- **CTA**：導流不販賣焦慮，結尾回扣「你開始理解自己了嗎？」。
- **hashtag**：8–14 個，去掉跟本集無關的。

### 3. 自檢（等同 Director + QA 那一關）

- [ ] 沒有恐怖／迷信／浮誇／恐嚇／保證預測（`_brand_guard_report.md` 綠燈只是最低標，語意層要自己看）。
- [ ] 沒有吉凶預測、沒有對結果下絕對承諾。
- [ ] 命盤被描述成「傾向」而非「宿命」。
- [ ] 語氣成熟 · 溫暖 · 理性 · 有電影感；文字留白，不塞滿。
- [ ] 檔名符合 `{PROJECT}_S{季}_E{集}_{格式}_{編號}_v{版本}.{副檔名}`。

任一條沒過 → 依 Brand Bible 一律重做，不要「先發再說」。

## 沒有劇本時

若使用者只給主題或一段素材，先問清楚：**專案／季集、想讓觀眾理解的一件事、出場角色**。
補完後可先落成 `05_Scripts` 的劇本再跑本流程；急件才直接手寫貼文，但上面的自檢清單照跑。

## 相依性

Python 3.9+，純標準庫，離線可跑（與 `automation/` 其他工具一致）。
