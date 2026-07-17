# ================================================================
# 小潔米株式會社・本機自動執行器 (Local Auto Runner)
# 每天由 Windows 排程自動跑：拉取最新指令 → 叫 Codex 執行 outbox 未回報的工單
# 設定一次即可，之後全自動，老闆不需再手動當傳令兵。
# ================================================================

# ---- 只需改這一行：你 repo 的實際路徑 ----
$RepoPath = "C:\Users\X\Documents\SSOT\02_Projects\yubao-tts"
$Branch   = "claude/digital-marketing-ceo-project-uzws8r"
# ------------------------------------------------

$LogDir = Join-Path $RepoPath "Jamine_AI_Studio_OS\automation\local_runner\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir ("run_{0:yyyy-MM-dd_HHmm}.log" -f (Get-Date))

function Say($m){ $line = "[{0:HH:mm:ss}] $m" -f (Get-Date); Write-Output $line; Add-Content $Log $line }

Say "=== 本機自動執行器啟動 ==="
Set-Location $RepoPath

# 1) 拉最新指令
Say "git fetch + checkout + pull ..."
git fetch origin $Branch 2>&1 | ForEach-Object { Say $_ }
git checkout $Branch 2>&1 | ForEach-Object { Say $_ }
git pull origin $Branch 2>&1 | ForEach-Object { Say $_ }

# 2) 檢查 outbox 是否有未回報的工單（有對應 inbox result 就算已回報）
$OutBox = "Jamine_AI_Studio_OS\00_CEO_Office\handoffs\outbox"
$InBox  = "Jamine_AI_Studio_OS\00_CEO_Office\handoffs\inbox"
$pending = $false
Get-ChildItem $OutBox -Filter *.md -File -ErrorAction SilentlyContinue | ForEach-Object {
    $resultName = ($_.BaseName + "_result")
    if (-not (Get-ChildItem $InBox -Filter ($_.BaseName + "*result*") -File -ErrorAction SilentlyContinue)) {
        $pending = $true
    }
}

if (-not $pending) {
    Say "outbox 無未回報工單，結束（不呼叫 Codex，節省額度）。"
    Say "=== 完成 ==="
    exit 0
}

# 3) 叫 Codex 執行（非互動、自動核准）
Say "偵測到未回報工單 → 呼叫 Codex ..."
# 註：--full-auto 讓 Codex 自動執行不逐步詢問；若你的 Codex 版本旗標不同，
#     先跑一次 `codex exec --help` 確認，並把下面這行換成對應旗標。
codex exec --full-auto "讀取並遵守 Jamine_AI_Studio_OS/00_CEO_Office/handoffs/CODEX_RUNNER.md，處理 outbox 中所有尚未回報的指令包，完成後 commit 並 push" 2>&1 | ForEach-Object { Say $_ }

Say "=== 完成（Codex 已執行，成果應已 push 回 GitHub）==="
