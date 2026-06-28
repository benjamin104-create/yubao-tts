@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 潔米爸紫微斗數 - 一鍵生圖
echo ============================================
echo   潔米爸的占驗派紫微斗數 - 一鍵生圖 (Windows)
echo ============================================
echo.

REM --- 1. 檢查 Python ---
where python >nul 2>nul
if errorlevel 1 (
  echo [錯誤] 找不到 Python。
  echo.
  echo 請先到 https://www.python.org/downloads/ 下載安裝，
  echo 安裝時務必勾選最底下的 "Add python.exe to PATH"，
  echo 裝好後重新雙擊本檔即可。
  echo.
  pause
  exit /b 1
)

REM --- 2. 安裝套件 ---
echo [1/3] 安裝必要套件中...（第一次比較久，請稍候 1-3 分鐘）
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
  echo [錯誤] 套件安裝失敗，請把畫面截圖給我。
  pause
  exit /b 1
)

REM --- 3. 取得金鑰 ---
if defined OPENAI_API_KEY goto :run
if exist ".env" (
  echo [2/3] 偵測到 .env，將使用其中的金鑰。
  goto :run
)
echo.
echo [2/3] 請貼上你的 OpenAI 金鑰（在視窗上按右鍵可貼上），然後按 Enter：
set /p OPENAI_API_KEY=金鑰 sk-... :
if not defined OPENAI_API_KEY (
  echo [錯誤] 沒有輸入金鑰。
  pause
  exit /b 1
)

:run
echo.
echo [3/3] 開始生成 5 張 x 2 版（共 10 張），每張約 10-30 秒，請耐心等待...
echo.
python scripts\generate_batch.py
if errorlevel 1 (
  echo.
  echo [提醒] 過程出現錯誤。把上面的紅字/英文訊息截圖給我，我幫你判斷。
  echo        常見：金鑰錯、OpenAI 額度不足、或帳號的圖片生成尚未開通。
  pause
  exit /b 1
)

echo.
echo ============================================
echo   完成！正在打開預覽 outputs\index.html ...
echo ============================================
start "" "outputs\index.html"
echo.
echo 圖片都在 outputs\ 資料夾裡（每張 2 版 _v1 _v2）。
echo 挑好後可再跑後製上字。有問題把畫面截給我即可。
pause
