# B｜把主場搬到本機：本機 Claude Code 設定清單

目標：在**你自己的電腦**上跑一個有長期記憶、能動本機檔案、能調用工具（Google Drive / 影片 / HyperFrames）的私人 Agent。
手機只是「遠端進去下指令」的窗口（見最後一節）。

---

## 步驟 1：在電腦上裝 Claude Code

1. 裝 Node.js 22+（HyperFrames 也需要）：<https://nodejs.org>
2. 裝 Claude Code CLI：
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```
3. 開一個你的工作資料夾當「主場」，例如 `~/yubao-agent`，進去啟動：
   ```bash
   mkdir ~/yubao-agent && cd ~/yubao-agent
   claude
   ```
   第一次會請你登入（Anthropic 帳號）。

> 桌面 App 也行（Mac/Windows），但 CLI 最適合「自動化 / 開機載記憶 / 之後手機 SSH 進來用」。

## 步驟 2：放入長期記憶骨架

把本 kit 的 `CLAUDE.md` 和 `memory/` 整個資料夾複製到 `~/yubao-agent/` 根目錄。
Claude Code **每次啟動會自動讀同目錄的 `CLAUDE.md`** —— 這就是「長期記憶」的入口。

```
~/yubao-agent/
├── CLAUDE.md          ← 自動載入：Agent 身分 + 規則 + 記憶庫位置
└── memory/            ← 你的長期記憶（會一直累積在你硬碟）
    ├── profile.md
    ├── log.md
    ├── projects/
    └── assets.db      ← 跑 scan 後產生
```

## 步驟 3：接上你要的工具（MCP server）

在 `~/yubao-agent/` 建一個 `.mcp.json`，把要用的服務接上。範例：

```jsonc
{
  "mcpServers": {
    "google-drive": {
      "command": "npx",
      "args": ["-y", "@google/drive-mcp"]   // ← 依你選用的 Drive MCP 套件為準
    }
    // 影片：HyperFrames 不是 MCP，是本機 CLI，見 hyperframes/RECIPE.md
  }
}
```
> 接好後在 Claude Code 裡輸入 `/mcp` 可檢查連線狀態。MCP 設定細節：<https://code.claude.com/docs>

## 步驟 4：建立本機素材索引（找資料夾 + 存進 DB）

把你散落各處的素材資料夾掃進記憶 DB：

```bash
cd ~/yubao-agent
python3 tools/scan_assets.py ~/Movies ~/Pictures ~/Downloads/素材
```
之後 Agent 問「我手邊有哪些貓的影片」時，就能查 `memory/assets.db`，不必每次重掃硬碟。

## 步驟 5（選配）：讓手機能遠端進這台電腦

這才是你最早問的「手機控制自己電腦終端機」的正解：

1. 電腦開 SSH（Mac：設定→一般→共享→遠端登入；Windows：裝 OpenSSH Server）。
2. 電腦+手機都裝 **Tailscale**（同帳號）→ 在外面也連得到家裡電腦，免設定 port。
3. 手機裝 **Termius** / **Blink Shell**，SSH 進電腦後直接 `cd ~/yubao-agent && claude`。
   → 這時 Claude Code 跑在你電腦上、用你的本機記憶、動你的本機檔案，手機只是螢幕。

---

## 一句話分工

- **手機雲端 Coco**：適合改 GitHub 上的程式（像這個 yubao-tts repo）。
- **本機 Claude Code（本清單）**：你要的「有記憶、動本機檔、做影片」的獨立 Agent。
- **手機 SSH 進本機**：兩者的橋——人在外面，但用的是電腦上那個有記憶的 Agent。
