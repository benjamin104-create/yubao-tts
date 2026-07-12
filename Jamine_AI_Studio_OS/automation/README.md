# ⚙️ Automation — Phase 2

> 把 Production Pipeline 的重複勞動交給程式。純 Python 3 標準庫，**不需安裝任何套件**。
> 這一層落實 Roadmap 的 Phase 2：Claude/DeepSeek 自動拆劇本、自動生 Prompt、自動整理素材與版本。

---

## 工具一覽

| 檔案 | 做什麼 | 對應 Pipeline 步驟 / 修補的缺口 |
|------|--------|-------------------------------|
| `studio.py` | 共用：讀 Bible / 語言庫、解析分鏡、讀素材索引 | 基礎層 |
| `prompt_engine.py` | 六格輸入 → 完整影片 Prompt | Pipeline ④（生 Prompt）；缺口 #4 光線優先序 |
| `asset_check.py` | 分鏡 → 比對素材庫 → 列出缺的素材 | 缺口 #1 素材自動比對 |
| `voice_cue_sheet.py` | 分鏡 → 配音腳本（含秒數對齊警告） | 缺口 #2 配音腳本、#3 秒數對齊 |
| `build_shots.py` | 一鍵：分鏡 → 全部 Shot 卡 + 素材報告 + 配音腳本 + **Prompt 驗證矩陣** | Pipeline ④⑤ 批次自動化 |
| `continuity_audit.py` | **角色一致性 / 服道化 / 時代穿幫**自動稽核 | 視覺總監的稽核責任程式化 |
| `data/libraries.json` | 電影語言庫機器版（運鏡/情緒/光線/場景/護欄） | 引擎原料 |
| `../03_Characters/character_anchors.json` | **角色視覺錨定表**（trigger/服裝/漂移負面詞/seed） | 角色一致性上鎖真相來源 |

---

## 快速開始

```bash
cd Jamine_AI_Studio_OS/automation
SB=../06_Storyboard/JMD/S01/E01/JMD_S01_E01_storyboard_v01.md

# 1) 單鏡頭：六格 → Prompt
python3 prompt_engine.py --char ah-zhe --emotion anxiety \
    --scene 台北捷運 --camera slow-push --lighting neon

# 2) 素材比對（缺什麼還沒做）
python3 asset_check.py "$SB"

# 3) 配音腳本
python3 voice_cue_sheet.py "$SB" out_voice.md

# 4) 一鍵批次：整集 40 鏡頭全生成（含 Prompt 驗證矩陣）
python3 build_shots.py "$SB" ../07_Prompts/JMD/S01/E01

# 5) 角色一致性 / 服道化 / 時代穿幫稽核（進生成前的最後一關；有阻斷項回傳非 0）
python3 continuity_audit.py "$SB"
```

## 角色一致性上鎖（服道化防漂移）

`character_anchors.json` 是每個角色的「數位聖經上鎖層」。引擎會**強制**把
`[SLUG]` trigger + 服裝規範 + 漂移負面詞嵌入每一支 Prompt：

- **prompt_engine**：自動注入 trigger / costume / `Consistency guard (avoid): …`。
- **build_shots**：產出 `_prompt_validation_matrix.md`，逐鏡頭查核 trigger 是否確實帶入。
- **continuity_audit**：抓「未上鎖角色」「服裝時代穿幫」「複雜紋樣風險」，通過才進生成。

> 誠實校準：文字層（trigger/服裝/負面/矩陣/稽核）對 Kling/Seedance 與 SD/MJ 都有效；
> Seed / IP-Adapter 只有 SD/MJ 吃，文生影片改用 reference_sheet 當角色參考。見
> `agents/visual_costume_director.md`。

---

## 設計重點

### 六格引擎怎麼組（`prompt_engine.py`）
依 `07_Prompts/PROMPT_ENGINE.md` 規格，把每個鏡頭組成 7 段：

```
[角色錨句] + [情緒表演] + [場景世界] + [運鏡] + [光線色彩] + [聲音] + [技術+品牌護欄]
```

- **角色錨句**直接讀 `03_Characters/{slug}` 的定裝錨句 → 跨鏡頭外型一致。
- **品牌護欄**（no horror / no superstition / …）自動附在每支 Prompt 尾，守 Brand Bible。

### Phase 1.1 缺口修補（都寫進程式了）
- **#1 素材比對**：`asset_check.py` 自動掃「需用素材」欄對照 `ASSET_LIBRARY_INDEX`，列出未入庫者。
- **#2/#3 配音**：`voice_cue_sheet.py` 抽台詞成腳本，並以「中文字數 ÷ 5」估時，超過鏡頭秒數就標 ⚠️。
- **#4 光線優先序**：`resolve_lighting()` 採「明確指定 > 場景預設 > 保底」，情緒不覆蓋場景冷暖。

### Phase 2 新發現並已修補：**場景 carry-forward**
分鏡「場景」欄常寫的是取景標籤（如「堂內·倒茶」「阿哲抬頭」）而非地點。
引擎比對不到地點時，**自動沿用上一個鏡頭的地點**（像真實 shot list 一樣），並在 `build_shots.py`
輸出中列出哪些鏡頭用了 carry-forward，方便人工複核。

---

## 拆劇本（Pipeline ①③）在哪裡接 LLM？

「劇本 → 40 分鏡」本質是創作判斷，交給 **Claude / DeepSeek**，不是這裡的確定性程式。
本工具組負責 LLM **前後**的自動化：

```
                  ┌─ 前：組裝 context ─┐        ┌─ 後：解析產出 ─────────┐
劇本(05) ─► [ Bible + 拆鏡指令 ] ─► LLM ─► 分鏡表(06) ─► build_shots.py ─► 40×Shot Prompt
                                              │                              + 素材報告
                                              └───────────► voice_cue_sheet ─► 配音腳本
```

- **前**：把 `01/02/03` Bible + `06_Storyboard/_TEMPLATE` 表頭 + 劇本，餵給 LLM 要它輸出分鏡表。
  （Agent 指令見 `agents/AGENT_ROSTER.md` 的 Cinematographer。）
- **後**：LLM 產出的分鏡表存進 `06_Storyboard/…`，本工具組即可全自動接手到「可生成」。

> DeepSeek 批次接管：把 `build_shots.py` 包成 Production Worker 的一步即可（Pipeline ⑤）。

---

## 相依性

- Python 3.9+（開發於 3.11）。標準庫，無 `pip install`。
- 資料來源全是 repo 內的 `.md` / `.json`，離線可跑。
