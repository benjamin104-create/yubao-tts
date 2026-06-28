# Windows 一鍵生圖 — 照這 4 步做就好

> 目標：在你自己的 Windows 電腦上，用你已儲值的 OpenAI 額度，一次生成 5 張 × 2 版漫畫圖。
> 你電腦的網路沒有被擋，所以一定跑得起來（雲端那邊是被公司政策擋住才不行）。

## 步驟 1：裝 Python（只需第一次）

1. 打開 https://www.python.org/downloads/
2. 按黃色大鈕 **Download Python**，下載後執行安裝檔
3. ⚠️ **安裝畫面最下面，務必勾選「Add python.exe to PATH」**，再按 Install
4. 裝完按 Close

## 步驟 2：下載這個專案

1. 打開這個網址（會直接下載整包 ZIP）：
   `https://github.com/benjamin104-create/yubao-tts/archive/refs/heads/claude/ziwei-doushu-manga-script-60y37d.zip`
2. 下載後，在檔案總管對 ZIP **按右鍵 → 解壓縮全部**
3. 進到解壓出來的資料夾，一路點進去找到 **`ziwei-manga`** 這個資料夾

## 步驟 3：雙擊執行

1. 在 `ziwei-manga` 資料夾裡，找到 **`run_windows.bat`**，**雙擊它**
2. （若出現「Windows 已保護你的電腦」藍色視窗 → 按「**其他資訊**」→「**仍要執行**」）
3. 它會自動裝套件，然後問你要金鑰：
   - 在黑色視窗裡**按滑鼠右鍵**就能貼上，貼上你的 `sk-...` 金鑰，按 **Enter**

## 步驟 4：等它跑完

- 大約 3～8 分鐘，跑完會**自動打開瀏覽器預覽**所有圖
- 圖片檔都存在 `ziwei-manga\outputs\` 裡（每張 2 版：`_v1`、`_v2`）

---

## 跑出來之後

- 喜歡哪張，就用那張去後製上中文字（標題/對白/宮位名）。
- 想上字：在同資料夾開「命令提示字元」，執行
  `python scripts\add_text_layout.py page01_cover`

## 遇到錯誤怎麼辦

把黑色視窗裡的**英文/紅字訊息截圖**傳給我，我直接幫你判斷。最常見三種：
1. **金鑰錯**：重貼一次，注意前後不要有空格。
2. **額度不足 / billing**：去 platform.openai.com 確認 credit 還在。
3. **圖片生成未開通 / model 沒權限**：程式會自動改用 `gpt-image-1` 重試；若還是不行，多半是帳號要先做「組織驗證」，到 platform 的 settings 完成驗證即可。

## 安全提醒

- 你貼在聊天室那把舊金鑰，**用完請去 platform.openai.com → API keys 作廢（Revoke）**。
- 之後在自己電腦用的金鑰，**只留在你電腦、別再貼到任何對話**最安全。
