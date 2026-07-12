# 角色聖經範本 (Character Bible Template)

> 複製本檔 → 重新命名為 `{slug}_{中文名}.md` → 一次設定、永遠固定。
> slug 同步登記進 `NAMING_CONVENTION.md`。

---

## 基本資料

| 欄位 | 內容 |
|------|------|
| 中文名 | |
| slug | |
| 年齡 | |
| 身高 / 體重 | |
| 職業 / 身分 | |

## 外型（生成一致性關鍵，務必具體）

| 欄位 | 內容 |
|------|------|
| 臉型 / 五官 | |
| 髮型 / 髮色 | |
| 眼鏡 / 配件 | |
| 服裝（固定造型） | |
| 體態 / 氣質 | |
| 一句話外型錨點 | （給 Prompt 用的定裝描述，越固定越好） |

## 個性

- 三個關鍵詞：
- 說話方式：
- 口頭禪：

## 內在

| 欄位 | 內容 |
|------|------|
| 渴望（想要什麼） | |
| 恐懼（怕什麼） | |
| 傷口（過去的痛） | |
| 成長弧線（會如何改變） | |

## 命理設定（呼應世界觀）

- 主星 / 命格傾向：
- 這個設定如何影響他的行為：

## 關係網

| 對象 | 關係 |
|------|------|

## 聲音（給 09_Voice / 語寶 TTS 用）

| 欄位 | 內容 |
|------|------|
| 音色描述 | |
| 語速 / 節奏 | |
| 情緒基調 | |

## Prompt 定裝錨句（英文，直接複製進生成器）

> （一段固定的英文外型描述，確保每次生成同一個人）

## 視覺錨定（機器真相，服道化上鎖）

> 新角色**必須**在 `character_anchors.json` 加一筆，否則 `continuity_audit.py` 會擋（未上鎖=漂移風險）。

在 `03_Characters/character_anchors.json` 新增：

```jsonc
"<slug>": {
  "name": "中文名",
  "trigger": "[SLUG] 精確到不可誤解的英文核心特徵（年齡/身高/髮/眼鏡/獨特標記/體態）",
  "immutable": ["恆定特徵1（如：細框圓眼鏡·恆戴）", "獨特標記（如：左眼下小痣）"],
  "costume": {
    "id": "<slug>-default", "items": "服裝", "fabric": "布料",
    "pattern": "紋樣（能 solid 就 solid）", "period": "時代（須合世界年代）",
    "texture_ref": "asset_tex_xxx_v01.png", "variations_allowed": "none"
  },
  "negative": "最常見的漂移，逗號分隔（如：no beard, no pattern, no age drift）",
  "seed": 0, "reference_sheet": "asset_char_<slug>_sheet_v01.png", "ip_adapter_weight": 0.8
}
```

服道化細節規範見 `04_Assets/COSTUME_TEXTURE_SPEC.md`；監督流程見 `agents/visual_costume_director.md`。
