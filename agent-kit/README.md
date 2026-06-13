# 個人 Agent Kit（語寶 / 短影音 / 長期記憶）

這是一套「**把 Claude 變成一個跑在你自己電腦上、有長期記憶、能動本機檔案、能做短影音的私人 Agent**」的起步包。
雲端版 Claude Code（手機 Coco / claude.ai/code）做不到這件事——它是臨時、隔離的容器。
所以這套東西的**主場是你自己的電腦**。

## 檔案導覽

| 檔案 | 對應你的需求 | 用途 |
|---|---|---|
| `SETUP-本機.md` | 「希望它是獨立、能幫我完成事情的 Agent」 | 在自己電腦裝 Claude Code、接 MCP、開機自動載記憶 的逐步清單 |
| `CLAUDE.md` | 「長期記憶,而非雲端短期記憶」 | Agent 的身分與規則範本；放到你工作資料夾根目錄,Claude Code 每次啟動自動讀 |
| `memory/` | 「把我的所有資訊都存在本機資料庫」 | 你的長期記憶庫(人物設定、專案狀態、日誌、素材索引 DB) |
| `memory/schema.sql` | 「本機資料庫 + 找資料夾並存取」 | 素材/檔案索引的 SQLite 結構 |
| `tools/scan_assets.py` | 「本機電腦協助找尋資料夾並存取」 | 掃描你指定的本機資料夾,把所有檔案登錄進記憶 DB |
| `hyperframes/RECIPE.md` | 「調用 HyperFrames 做短影音」 | 實測可用的 HTML→MP4 配方(含這次踩到的坑) |

## 三句話總結

1. **搬到本機**:照 `SETUP-本機.md` 在自己電腦上裝好 Claude Code。
2. **給它記憶**:把 `CLAUDE.md` + `memory/` 放進工作資料夾,跑 `tools/scan_assets.py` 建立本機索引。
3. **做影片**:照 `hyperframes/RECIPE.md` 讓 Agent 寫 HTML、render 成 MP4。
