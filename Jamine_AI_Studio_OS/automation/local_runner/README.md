# 本機自動執行器 — 一次設定，永久自動

> 目的：讓老闆**不再當傳令兵**。設定一次後，你的電腦每天自動：
> 拉取 CEO 派的工單 → 叫 Codex 執行 → Codex 把成果 push 回 GitHub → CEO 自動驗收。

## 全自動後的完整循環

```
雲端 CEO（已自動）          你的電腦（本設定）           雲端 CEO（已自動）
每日/每月排程出工單  ──→   排程每天跑 jamine_auto.ps1  ──→  每日排程自動驗收
push 到 outbox            拉取→Codex執行→push回inbox        分發下游、寫進簡報
```

老闆只需在「有 ALERT 或需決策」時出現——那才是你該花時間的地方。

## 一次性設定（三步，約 5 分鐘）

### 第 1 步：確認 repo 路徑
打開 `jamine_auto.ps1`，把最上面的 `$RepoPath` 改成你電腦上 repo 的真實路徑
（目前預設 `C:\Users\X\Documents\SSOT\02_Projects\yubao-tts`，不對就改）。

### 第 2 步：確認 Codex 自動核准旗標
開 PowerShell 跑一次 `codex exec --help`，確認自動執行的旗標。
若不是 `--full-auto`，把 `jamine_auto.ps1` 裡那行的旗標換掉。
（先手動跑一次 `powershell -File jamine_auto.ps1` 確認會動、不會卡在詢問。）

### 第 3 步：註冊每日排程（複製整段貼進 PowerShell，一次搞定）
把路徑換成你的實際路徑後執行：

```powershell
$ps1 = "C:\Users\X\Documents\SSOT\02_Projects\yubao-tts\Jamine_AI_Studio_OS\automation\local_runner\jamine_auto.ps1"
schtasks /create /tn "JaminePa_AutoRunner" /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$ps1`"" /sc daily /st 09:30 /f
```

完成。之後每天早上 09:30 自動跑（挑在雲端 CEO 每日 08:07 出工單之後）。

## 日常怎麼看

- 想確認有沒有跑：看 `automation/local_runner/logs/` 的當日 log
- 想立刻手動跑一次：`schtasks /run /tn "JaminePa_AutoRunner"`
- 想暫停：`schtasks /change /tn "JaminePa_AutoRunner" /disable`
- 想改時間：把上面 `/st 09:30` 換成你要的時間重跑註冊指令

## 前提

- 電腦當天 09:30 要是開機的（筆電闔蓋/關機就不會跑，可改到你固定開機的時段）
- Codex 已 `codex login`、git 能 push（你已完成）
- 聰明省額度：outbox 沒有未回報工單時，腳本直接結束、不呼叫 Codex
