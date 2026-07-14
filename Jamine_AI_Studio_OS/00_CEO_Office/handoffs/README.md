# AI 拋接協定 (Handoff Protocol) v1.0

> 讓 ChatGPT（或任何外部 AI）成為可調度的外包部門。
> 核心原則：**指令包自帶完整上下文與回報格式**——對方不需要讀 repo 也能正確執行與回報。

## 目錄結構

```
handoffs/
├── outbox/   ← CEO 產出的指令包（等老闆轉交）
├── inbox/    ← 外部 AI 的回報歸檔（老闆貼回後由 CEO 驗收存檔）
└── README.md
```

## 流程（老闆只當 30 秒傳令兵）

```
1. CEO 寫指令包 → outbox/，通知老闆
2. 老闆全選複製 → 貼到 ChatGPT → 送出
3. GPT 依包內規格執行，第一行必回 STATUS
4. 老闆把 GPT 的完整回覆貼回本對話（或丟 Drive）
5. CEO 驗收：過 → 歸檔 inbox/、進產線；不過 → 產修正包 v2
```

## 命名規範

`outbox/YYYY-MM-DD_GPT_{主題}_v{版}.md`
`inbox/YYYY-MM-DD_GPT_{主題}_result_v{版}.md`

## 指令包必含五段（缺一不可）

1. **角色設定**：你是誰、為誰工作、絕對禁令（Brand Bible 濃縮版）
2. **上下文**：完成任務所需的全部資料（世界觀/角色錨點/規格，內嵌不外連）
3. **任務**：具體交付物、範圍邊界（哪些不要做）
4. **回報格式**：固定結構，第一行必須是 `STATUS: DONE` 或 `STATUS: BLOCKED - 原因`
5. **自我檢核**：交件前 GPT 要自答的檢查清單

## 兩種執行端模式

### 模式一：網頁版 ChatGPT（人肉拋接）
老闆複製 outbox 指令包 → 貼給 ChatGPT → 把回覆貼回對話，CEO 歸檔 inbox。
限制：網頁版不能讀私有 repo、不能 push——上限就是貼上/貼回。

### 模式二：Codex CLI（近全自動，2026-07-15 啟用）★
老闆本機已裝 OpenAI Codex CLI，它能讀寫檔案與操作 git，於是拋接變成：

```
CEO 寫包 push → 老闆本機跑一條命令
  cd {repo 本機路徑}
  git pull origin claude/digital-marketing-ceo-project-uzws8r
  codex exec "讀取並遵守 Jamine_AI_Studio_OS/00_CEO_Office/handoffs/CODEX_RUNNER.md，
              處理 outbox 中所有尚未回報的指令包"
→ Codex 執行、寫 inbox/、commit、push → CEO 排程自動驗收
```

- Codex 端規則見 `CODEX_RUNNER.md`（只准寫 inbox/、STATUS 回報、做不到要 BLOCKED）
- 想再省：把上面三行存成 `jamine_handoff.sh`，甚至掛進本機排程（cron／捷徑 App），連打字都免了
- 計費：Codex CLI 用 ChatGPT 帳號登入即可，額度含在訂閱內，不需另外的 API key
