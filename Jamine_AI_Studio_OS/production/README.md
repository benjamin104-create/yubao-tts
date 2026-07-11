# 🎥 Production — Phase 3

> 把 Prompt / 配音腳本，實際送去外部服務生成 MP4 / MP3 的批次工具。
> 純 Python 標準庫。**真跑需要你自己的金鑰**（見下），沙箱環境只能 dry-run。

---

## 工具

| 檔案 | 做什麼 |
|------|--------|
| `build_manifest.py` | 分鏡 + Shot 卡 → `render_manifest.json`（生成的唯一真相來源） |
| `render_video.py` | manifest → Kling / Seedance 批次生成 MP4（dry-run 預設） |
| `render_voice.py` | 配音腳本 → Google Cloud TTS 國語配音（dry-run 預設），角色固定聲線 |

## 流程

```
07_Prompts（40 Shot 卡）┐
06_Storyboard（秒/對白）├─► build_manifest.py ─► 08_Video/…/render_manifest.json
                        │                              │
07_Prompts 配音腳本 ────┘                              ├─► render_video.py ─► MP4 →08_Video
                                                       └─► render_voice.py ─► MP3 →09_Voice
                                                                    │
                                                              10_Edit（DaVinci）
```

## 真跑需要的金鑰（沙箱沒有）

| 服務 | 環境變數 | 用途 |
|------|----------|------|
| Kling / Seedance | `VIDEO_API_KEY`, `VIDEO_ENDPOINT` | 文生影片 |
| Google Cloud TTS | `GOOGLE_TTS_KEY` | 國語（cmn-TW）配音 |

> 未設金鑰時，兩支 render 腳本會**自動切 dry-run**：驗證 + 寫出每個請求 payload，不呼叫外部。
> 完整指令與規模見 `08_Video/JMD/S01/E01/STATUS.md`。

## 誠實邊界

- `render_video.build_payload()` 是**通用文生影片範本**。不同 provider（Kling / Seedance）
  的欄位名不同，真接前請對照該 provider 當前 API 文件微調——我不臆造特定廠商的欄位細節。
- `render_voice.py` 的 Google TTS 請求格式**沿用本 repo `tts_gateway.py` 已驗證的寫法**，
  只把語音改成國語 `cmn-TW` 並依角色設定聲線，可信度較高。
- 語寶前端的「中文」是瀏覽器內建語音（browser provider），**後端不合成國語**；
  電影旁白/對白要在後端批次產生，就走 Google Cloud TTS 這條（本工具即是）。

## 產物（generated，已 gitignore）

- `payloads/`：dry-run 寫出的每個請求 JSON（可人工檢查）。
- `*.mp4` / `*.mp3`：真跑產生的素材（二進位，不進版控）。
