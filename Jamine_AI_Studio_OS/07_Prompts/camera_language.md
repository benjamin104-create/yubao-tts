# 電影語言庫 — 運鏡 (Camera Language)

> Prompt Engine 的積木之一。挑一個運鏡名，引擎自動展開成完整鏡頭描述。

| 運鏡 | 代號 | 英文 | 語意 / 何時用 |
|------|------|------|----------------|
| 緩推 | `slow-push` | Slow Push In | 情緒逐漸靠近、進入內心；潔米爸說重話前 |
| 環繞 | `orbit` | Orbit / Arc | 揭示、命盤空間、關鍵領悟 |
| 過肩 | `shoulder` | Over-the-Shoulder | 對話、對峙、傾聽 |
| 手持 | `handheld` | Handheld | 焦慮、混亂、真實感 |
| 廣角 | `wide` | Wide Shot | 建立場景、孤獨感、人在城市裡渺小 |
| 空拍 | `drone` | Drone / Aerial | 山腰紫微堂、城市全景、開場 |
| 跟拍 | `tracking` | Tracking Shot | 角色行走、情緒推進 |
| 推近 | `zoom-in` | Zoom In | 聚焦一個物件 / 表情 |
| 拉遠 | `zoom-out` | Zoom Out | 抽離、釋懷、收尾 |
| 升降 | `crane` | Crane | 情緒升華、片尾 |
| 焦點轉移 | `rack-focus` | Rack Focus | 從人到命盤、從近到遠的心念轉移 |

## 用法

在 Prompt Engine 的「運鏡」欄填**代號**即可，例如 `slow-push`。
引擎會展開為：

> Slow, deliberate push-in toward the subject, gradually tightening the frame to draw the viewer into the character's inner state, cinematic, steady.

## 預設

未指定時，對話用 `shoulder`，情緒收尾用 `zoom-out`，開場用 `drone` 或 `wide`。
