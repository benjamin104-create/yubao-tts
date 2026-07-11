# 🎬 Jamine AI Studio OS v1.0

> 一間「一個人就能運作」的 AI 內容公司作業系統。
> 把它想成 Pixar / Marvel 的內部製作系統：以後所有作品都走同一套流程。

第一個產品：**《潔米爸的占驗派紫微斗數》**
但這套系統的真正目標，是讓每一個新系列（BCJL、教育系列、小潔米成長紀錄……）都能沿用同一套底層架構，讓製作成本與時間逐季下降。

---

## 為什麼要先蓋工廠，而不是先拍第一集

你的目標不是「完成一部 30 分鐘電影」，而是**未來五年穩定產出數十部作品**。

只要底層架構建立好：

- 角色、世界觀、畫風 → 永遠一致
- Prompt → 不用重寫，用組合的
- 素材 → 做一次，用一輩子
- 重複勞動 → 交給 AI Agents
- 一部電影 → 自動拆成 IG / TikTok / Podcast / 電子報 / 課程 / 書

這份 repo 就是那座工廠的**設計藍圖與運作手冊**。

---

## 十二層架構（資料夾對照）

| 層 | 資料夾 | 角色 | 更動頻率 |
|----|--------|------|----------|
| 1 | `01_Brand` | 品牌聖經（品牌精神、Tone、禁止事項） | 幾乎不改 |
| 2 | `02_World` | 世界觀聖經（城市、年代、色彩） | 幾乎不改 |
| 3 | `03_Characters` | 角色聖經（每個角色固定設定） | 新增角色時才動 |
| 4 | `04_Assets` | 素材庫（最值錢的資產） | 持續累積 |
| 5 | `05_Scripts` | 劇本 | 每部作品 |
| 6 | `06_Storyboard` | 分鏡 | 每部作品 |
| 7 | `07_Prompts` | Prompt 引擎 + 電影語言庫 | 持續累積 |
| 8 | `08_Video` | 影片生成（Kling / Seedance） | 每部作品 |
| 9 | `09_Voice` | 配音（串接本 repo 的語寶 TTS） | 每部作品 |
| 10 | `10_Edit` | 剪輯（DaVinci） | 每部作品 |
| 11 | `11_Publish` | 內容工廠（多平台自動拆解） | 每部作品 |
| 12 | `12_Archive` | 封存 | 完成後 |

輔助模組：

| 模組 | 資料夾 | 角色 |
|------|--------|------|
| 製作流程 | `pipeline/` | 端到端 pipeline 定義 |
| AI 團隊 | `agents/` | 9 位 AI Agent 的職責與指令 |
| 知識庫 | `knowledge/` | 你的真正價值：Knowledge Graph |
| 命名規範 | `NAMING_CONVENTION.md` | 全系統檔名規則 |

---

## 資料流（一部作品怎麼跑完）

```
01 Brand  ┐
02 World  ├─►  所有 AI 都先讀這三份（永遠固定）
03 Char   ┘
             │
05 Scripts ──┤  Screenwriter Agent 依 Bible 寫劇本
             │
06 Storyboard┤  Director Agent 審核，拆 40 鏡頭
             │
07 Prompts ──┤  Prompt Engine：角色+情緒+場景+運鏡 → 3000 字 Prompt
             │  （組合 camera / emotion / lighting 三大電影語言庫）
             │
04 Assets ───┤  能重用的素材直接調用，不用重生
             │
08 Video ────┤  Kling / Seedance 批次生成 MP4
             │
09 Voice ────┤  語寶 TTS 生成配音（角色固定聲線）
             │
10 Edit ─────┤  匯入 DaVinci，剪輯 + 字幕
             │
11 Publish ──┤  Content Factory 自動拆成多平台內容
             │
12 Archive ──┘  封存版本 + 回收可重用素材
```

完整版見 [`pipeline/PRODUCTION_PIPELINE.md`](pipeline/PRODUCTION_PIPELINE.md)。

---

## 四個里程碑（Roadmap）

| Phase | 名稱 | 期程 | 產出 |
|-------|------|------|------|
| **Phase 1** | Studio Foundation | ~2 週 | 世界觀 / 角色 / Prompt / 鏡頭 Bible、命名規範、資料夾結構 ← **本次交付** |
| Phase 2 | Automation | 2–4 週 | Claude 自動拆劇本、DeepSeek 自動生成 Prompt、自動鏡頭清單、自動整理版本 |
| Phase 3 | Film Factory | — | 正式製作《潔米爸》第一季，累積可重用素材資產 |
| Phase 4 | Content Factory | — | 電影自動拆成 IG / TikTok / Shorts / Podcast / 電子報 / 課程 / 電子書 |

> **本 repo 目前完成 Phase 1 的 foundation。** 每份 Bible 都是「可讀、可餵給 AI、可隨作品成長」的活文件。

---

## 怎麼用這套系統

1. **開新作品** → 複製 `05_Scripts/_TEMPLATE_script.md`、`06_Storyboard/_TEMPLATE_storyboard.md`。
2. **所有 AI 對話開頭** → 先貼上 `01_Brand` + `02_World` + 相關 `03_Characters`。
3. **要生成畫面** → 用 `07_Prompts/PROMPT_ENGINE.md` 的六格輸入法，不要手寫 Prompt。
4. **做出新素材** → 登記進 `04_Assets/ASSET_LIBRARY_INDEX.md`，下次直接重用。
5. **新增角色** → 複製 `03_Characters/_TEMPLATE_character.md`，設定一次、永遠固定。

---

*Jamine AI Studio OS — 讓一個人，運作一整間內容公司。*
