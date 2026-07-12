# 3D 導入 SOP — 「3D 為骨，AI 為皮」

> 當一致性要求高到文生影片扛不住時，改走 3D。核心原則一句話：
> **讓 3D 負責結構與動態（保證 100% 不走樣），讓 AI 只負責風格化與材質微調。**
>
> ⚠️ 這是外部 DCC 工具（Unreal Engine / Blender / MetaHuman / Marvelous Designer）的**工作流規範**，
> 不是本 repo 能跑的程式。但它嚴格接上前期已建好的上鎖層：
> `03_Characters/character_anchors.json`、`04_Assets/COSTUME_TEXTURE_SPEC.md`、`automation/continuity_audit.py`。

---

## 何時走 3D，何時留在 2D 文生影片？

| 情況 | 建議路線 |
|------|----------|
| 情緒特寫、氛圍鏡、過場、命盤心象 | **Kling/Seedance 文生影片**（快、便宜，一致性由 trigger 守住） |
| 角色連續動作、多鏡頭同場、複雜互動、服裝需 100% 不變 | **3D 導入**（MetaHuman + Marvelous Designer） |
| 需要精確重複同一角色跨幾十鏡 | **3D**（2D 每幀都在賭一致性，3D 是實體不會賭） |

> 原則：**每幀都在變的東西，就該用 3D 釘死。** 文生影片扛得住的，就別浪費 3D 工時。

---

## 五階段流程

```
前期上鎖（已完成）              3D 導入（本 SOP）                    後製
character_anchors.json  ─►  ① MetaHuman 角色建模  ─►  ④ 綁定+動畫 ─►  ⑤ AI 為皮
COSTUME_TEXTURE_SPEC    ─►  ② Marvelous 服裝     ─►     (骨架/OpenPose)   (風格濾鏡/材質微調)
asset_tex_*（貼圖）      ─►  ③ 紋理回貼
        │
   continuity_audit（每階段都可回跑稽核）
```

### ① 角色建模（MetaHuman）— 鎖比例
- 輸入：該角色的 `reference_sheet`（定裝三視圖，見 anchor 表）＋ `immutable` 特徵清單。
- 動作：在 MetaHuman Creator 依三視圖捏臉，**逐項對齊 `immutable`**：
  - 潔米爸：185cm 身高比例、細框圓眼鏡（建模為配件，恆戴）、灰白短髮、高顴骨。
  - 阿哲：176cm、瀏海、左眼下小痣（貼圖或幾何細節）、清瘦體態。
  - 小薇：165cm、低馬尾、右下顎美人痣、金耳釘。
- 產出：`asset_3d_char_<slug>_v01`（MetaHuman 資產）。**比例一旦鎖定，全季不改。**

### ② 服裝（Marvelous Designer）— 鎖版型
- 輸入：`COSTUME_TEXTURE_SPEC.md` 的該角色 costume（版型 + 布料）。
- 動作：用 Marvelous Designer 做出實體布料模擬的服裝（立領衫 / 帽 T / 風衣）。
  - **純色服裝**：直接指定素色材質。
  - **有紋樣時**：把 `asset_tex_*`（高清平鋪貼圖）當 fabric texture 貼上，**由 3D UV 保證紋樣不扭曲**
    ——這正是 2D AI 最會出包的地方（格紋錯亂），3D 從根本解決。
- 產出：`asset_3d_costume_<costume-id>_v01`。

### ③ 紋理回貼 — AI 紋理 → 3D 表面
- 把前期鎖定的 AI 材質貼圖（布料質感、皮膚細節）**回貼**到 ①② 的 3D 模型。
- 原則：**紋樣/圖案一律來自 ControlNet 鎖定的貼圖，不由 3D 即興生成**，確保與 2D 分鏡同源。

### ④ 綁定 + 動畫 — 骨架橋接 2D 分鏡
- 依 `06_Storyboard` 的運鏡與動作，用 3D 傀儡擺姿勢。
- **OpenPose 橋接**：3D 擺好的骨架可輸出 OpenPose 骨架圖，餵回 2D ControlNet（若混用 2D/3D），
  保證同一動作在 2D 與 3D 版本一致。
- 相機依 `camera_language` 代號設定（slow-push / orbit / crane…）。

### ⑤ 後製「AI 為皮」— 只做風格，不動幾何
- AI 在此**只**做：風格化濾鏡、材質微調、光線氛圍潤色（回扣 World Bible 冷暖）。
- **絕對禁止**：用 AI 逐幀重繪角色或服裝（那會讓一致性當場崩潰，等於前功盡棄）。
- 局部走樣？→ **Inpainting 局部重繪**，只修那一塊，不重算整幀。

---

## 與 Studio OS 的接點

| 3D 階段 | 吃前期哪份上鎖 | 命名 |
|---------|----------------|------|
| ① 建模 | `character_anchors.json`（immutable + reference_sheet） | `asset_3d_char_<slug>_v01` |
| ② 服裝 | `COSTUME_TEXTURE_SPEC.md`（版型/布料/紋樣） | `asset_3d_costume_<costume-id>_v01` |
| ③ 貼圖 | `asset_tex_*`（ControlNet 鎖定貼圖） | 沿用貼圖檔名 |
| ④ 動畫 | `06_Storyboard`（運鏡/動作/秒數） | `<PROJECT>_S01_E01_shot_XXX_3d_v01` |
| ⑤ 後製 | `02_World`（冷暖色彩） | `..._final_v01.mp4` |

> 3D 資產登記進 `04_Assets`（新增 `3d` 類別），與 2D 素材同一套索引管理。

---

## 3D 一致性 QA 檢查（交 QA Agent + 視覺總監）

- [ ] 角色比例對齊 `immutable`（身高、五官、獨特標記）
- [ ] 眼鏡/配件（潔米爸圓框、小薇金耳釘）恆在
- [ ] 服裝版型與 `COSTUME_TEXTURE_SPEC` 一致，紋樣不扭曲
- [ ] 動作骨架對得上 `06_Storyboard`
- [ ] 後製只做風格，未逐幀重繪角色
- [ ] 3D 版與 2D 文生影片版（若混用）同角色外觀一致

---

## 誠實邊界

- MetaHuman / Marvelous Designer / Unreal / Blender 都是**桌面級 DCC 軟體**，不在本 repo 或沙箱內執行；
  本 SOP 是給你（或美術外包）照著做的規範。
- 本 repo 能自動化的是**前期上鎖 + 稽核**（已完成）與**2D 文生影片批次**（Phase 3 harness）。
- 3D 這條線的自動化程度依團隊工具而定；SOP 先把「規範與接點」釘死，工時與品質才可控。

---

## 複合式工作流總圖（把後期修改率降 80%+）

```
【LLM：規範+稽核】 character_anchors / continuity_audit   ← 已自動化
        │
        ├─►【2D 路線】Kling/Seedance + trigger 上鎖  ── 氛圍/特寫/過場
        │
        └─►【3D 路線】MetaHuman(骨) + Marvelous(衣) + AI 紋理(皮)  ── 連續動作/高一致
                        │  OpenPose 骨架橋接 2D／Inpainting 局部修
                        ▼
              【後製】AI 只做風格化濾鏡 + 材質微調
```

**結構化文字規範（LLM）＋ 幾何骨架控制（ControlNet/OpenPose）＋ 3D 實體基底（MetaHuman）= 一致性。**
