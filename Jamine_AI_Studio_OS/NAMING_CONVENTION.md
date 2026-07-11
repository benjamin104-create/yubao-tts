# 檔案命名規範 (Naming Convention)

> 一致的命名，是 AI 能自動整理、你能永遠找得到東西的前提。
> 規則越無聊，系統越可靠。

---

## 核心原則

1. **全小寫、用連字號 `-` 或底線 `_`，不用空格、不用中文檔名**（中文放在檔案內容，不放檔名）。
2. **能排序**：所有序號補零（`01`, `02`, ... `40`）。
3. **看檔名就知道是什麼**：`專案_季_集_鏡頭_版本` 由粗到細。
4. **版本永遠留痕**：不要覆蓋，改用 `v01`, `v02`。

---

## 專案代號 (Project Code)

| 系列 | 代號 |
|------|------|
| 潔米爸的占驗派紫微斗數 | `JMD` |
| BCJL | `BCJL` |
| 教育系列 | `EDU` |
| 小潔米成長紀錄 | `KIDS` |

---

## 通用格式

```
{PROJECT}_S{季}_E{集}_{類型}_{編號}_{描述}_v{版本}.{副檔名}
```

範例：

| 用途 | 檔名 |
|------|------|
| 劇本 | `JMD_S01_E01_script_v03.md` |
| 分鏡 | `JMD_S01_E01_storyboard_v02.md` |
| 單一鏡頭 Prompt | `JMD_S01_E01_shot_012_v01.md` |
| 生成影片 | `JMD_S01_E01_shot_012_kling_v01.mp4` |
| 配音 | `JMD_S01_E01_voice_ah-zhe_012_v01.wav` |
| 剪輯輸出 | `JMD_S01_E01_final_v04.mp4` |
| 發布切片 | `JMD_S01_E01_reels_03_v01.mp4` |

---

## 角色代號 (Character Slug)

| 角色 | slug |
|------|------|
| 潔米爸 | `jamie-dad` |
| 阿哲 | `ah-zhe` |
| 小薇 | `xiao-wei` |

新增角色時，在 `03_Characters/` 建檔並同步登記 slug。

---

## 素材命名 (Assets)

```
asset_{類別}_{名稱}_{變體}_v{版本}.{副檔名}
```

範例：

| 素材 | 檔名 |
|------|------|
| 羅盤 PNG | `asset_prop_compass_gold_v01.png` |
| 命盤動畫 | `asset_fx_natal-chart_glow_v02.mp4` |
| 台北捷運場景 | `asset_scene_taipei-mrt_night_v01.png` |

類別建議：`prop`（道具）、`scene`（場景）、`fx`（特效/動畫）、`char`（角色定裝）、`ui`（介面元素）。

---

## 版本規則

- `v01` 起跳，補零到兩位數。
- **定稿**額外複製一份加 `_FINAL`：`JMD_S01_E01_final_v04_FINAL.mp4`。
- 廢棄版本移到 `12_Archive/`，不刪除。

---

## 資料夾內作品結構（建議）

每個系列在 `05_Scripts` / `06_Storyboard` / `08_Video` 等層底下，用同一套子路徑：

```
{PROJECT}/S{季}/E{集}/
```

例：`08_Video/JMD/S01/E01/`
