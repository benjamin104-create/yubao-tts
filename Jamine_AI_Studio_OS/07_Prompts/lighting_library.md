# 電影語言庫 — 光線 (Lighting Library)

> Prompt Engine 的積木之一。光是本品牌的核心語言：**冷=壓力，暖=理解。**

| 光線 | 代號 | 英文 | 語意 / 場合 |
|------|------|------|-------------|
| 晨光 | `dawn` | Soft dawn light | 希望、新的開始 |
| 黃昏 | `dusk` | Golden dusk | 過渡、感傷、回望 |
| 暖燈 | `warm-lamp` | Warm lamplight | 紫微堂、被理解的時刻 |
| 霓虹 | `neon` | Neon city light | 都市、壓力、迷惘（冷） |
| 月光 | `moonlight` | Cool moonlight | 孤獨、夜、內省 |
| 逆光 | `backlight` | Backlight / Rim light | 輪廓、神秘、關鍵人物登場 |
| 神光 | `god-ray` | God Ray / Volumetric | 覺醒、領悟、命盤空間 |

## 用法

在 Prompt Engine 的「光線」欄填代號（未填則由**場景+情緒**自動推導）。

## 自動推導規則（引擎預設）

| 條件 | 預設光線 |
|------|----------|
| 場景 = 紫微堂 | `warm-lamp` |
| 場景 = 城市 / 捷運 / 百貨 | `neon` |
| 情緒 = 希望 / 覺醒 | `dawn` 或 `god-ray` |
| 情緒 = 孤獨 | `moonlight` |
| 命盤空間 | `god-ray` + 金色 |

> 光線一旦與場景綁定，就別隨意違反冷暖對比原則——那是品牌的視覺簽名。
