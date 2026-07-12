# 服道化：布料與紋樣控制規範 (Costume & Texture Spec)

> 服道化的最大漂移來源是**複雜紋樣**。這份規範把每套服裝的布料、紋樣、時代、貼圖釘死。
> 機器真相在 `03_Characters/character_anchors.json` 的 `costume` 欄；本檔是人看的規範與貼圖清單。

---

## 鐵則

1. **能純色就純色。** 本片主角服裝一律 solid，AI 漂移風險最低（見各角色 `costume.pattern`）。
2. **一定要有紋樣時**：必附**高清平鋪貼圖（seamless texture）**當 ControlNet 輸入，並用精確歷史描述，
   例：「19 世紀蘇格蘭高地塔坦平織，經緯交叉點 90°，拒絕現代數位迷彩感」。
3. **時代一致**：服裝 `period` 必須與 World Bible 年代相容；`continuity_audit.py` 會自動抓穿幫。
4. **一套鎖到底**：同一角色同一季用同一套（`variations_allowed: none`），換裝要另立 costume id 並經視覺總監審核。

---

## 角色服裝總表（S01）

| 角色 | costume id | 服裝 | 布料 | 紋樣 | 時代 | 貼圖 |
|------|-----------|------|------|------|------|------|
| 潔米爸 | `jamie-dad-default` | 深藍立領衫 + 炭灰長褲 | 霧面棉麻 | 純深藍·無紋 | 2026/timeless | `asset_tex_navy-mandarin_v01.png` |
| 阿哲 | `ah-zhe-default` | 灰帽 T + 白素 T + 深色窄褲 | 霧面棉質 | 純灰·無 logo | 2026 | `asset_tex_grey-hoodie_v01.png` |
| 小薇 | `xiao-wei-default` | 米色風衣 + 白襯衫 | 華達呢 | 純色·無紋 | 2026 | `asset_tex_beige-trench_v01.png` |

> 以上皆 solid，本季不需複雜紋樣貼圖。上表貼圖為「布料材質參考」，供 3D 導入階段（Marvelous Designer）與 AI 材質微調使用。

---

## 貼圖 / 參考圖清單（待製作，登記於 ASSET_LIBRARY_INDEX）

| 檔名 | 類別 | 用途 |
|------|------|------|
| `asset_char_jamie-dad_sheet_v01.png` | char | 角色定裝三視圖（正/側/3-4 面），SD/MJ 鎖 Seed、Kling 角色參考 |
| `asset_char_ah-zhe_sheet_v01.png` | char | 同上 |
| `asset_char_xiao-wei_sheet_v01.png` | char | 同上 |
| `asset_tex_navy-mandarin_v01.png` | char | 深藍立領布料材質 |
| `asset_tex_grey-hoodie_v01.png` | char | 灰帽 T 布料材質 |
| `asset_tex_beige-trench_v01.png` | char | 米色風衣布料材質 |

---

## 換裝流程（未來多套服裝時）

1. 新服裝 → 在 `character_anchors.json` 新增一個 costume id（不覆蓋舊的）。
2. 分鏡加「服裝」欄標明該鏡頭穿哪套 → `continuity_audit.py` 可查「換裝時間是否合理」。
3. 視覺總監審核換裝的時代 / 時間順序，通過才進生成。
