# JMD S01E01 — 生成狀態 (Phase 3)

> 誠實記錄：哪些已完成、哪些卡在「需要外部服務金鑰」。

## 進度

| 階段 | 狀態 | 產出 |
|------|------|------|
| 劇本 | ✅ 完成 | `05_Scripts/…/JMD_S01_E01_script_v01.md` |
| 分鏡（40 鏡） | ✅ 完成 | `06_Storyboard/…/…_storyboard_v01.md` |
| Shot Prompt（40 支） | ✅ 完成（自動生成） | `07_Prompts/JMD/S01/E01/` |
| 配音腳本 | ✅ 完成 | `…_voice_cue_sheet.md`（24 句台詞） |
| Render manifest | ✅ 完成 | `render_manifest.json`（40 job） |
| **影片生成** | ⛔ **待你的金鑰** | Kling / Seedance |
| **配音合成** | ⛔ **待你的金鑰** | Google Cloud TTS（cmn-TW） |
| 剪輯 | ⏳ 待素材 | DaVinci |

## 為什麼影片/配音還沒生成

這個開發沙箱環境**沒有 Kling / Seedance / Google 金鑰，且對外連線被限制**
（連免費的意傳台語 TTS 都被 proxy 擋：`403 CONNECT tunnel failed`）。
所以「真的產生 MP4／MP3」這一步，必須在**你自己的環境、用你的金鑰**跑。

工具已經寫好、也在 dry-run 驗證過會正確組出每一個請求。你只要設好金鑰、拿掉 `--dry-run`。

## 一鍵真跑（在你自己的機器）

```bash
cd Jamine_AI_Studio_OS/production

# 影片（Kling / Seedance）
export VIDEO_API_KEY=你的金鑰
export VIDEO_ENDPOINT=https://<provider>/v1/videos      # 依 provider 文件
python3 render_video.py ../08_Video/JMD/S01/E01/render_manifest.json ../08_Video/JMD/S01/E01

# 配音（Google Cloud TTS，國語 cmn-TW）
export GOOGLE_TTS_KEY=你的金鑰
python3 render_voice.py ../07_Prompts/JMD/S01/E01/JMD_S01_E01_voice_cue_sheet.md ../09_Voice/JMD/S01/E01
```

## 規模與粗估

- 影片：40 鏡，合計約 **192 秒**成片素材。
- 配音：**24 句**國語台詞（潔米爸 / 阿哲 兩種聲線）。
- 剪輯：素材備齊後匯入 DaVinci，依分鏡順序 + 配音 + 字幕（見 `10_Edit`）。

## dry-run 已產出的可檢查物

- `payloads/`：每個鏡頭 / 每句台詞的完整請求 JSON（真跑會送出的內容，可先人工檢查）。
- `render_manifest.json`：40 個 job 的機器可讀清單。
