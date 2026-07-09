# 《潔米爸占驗紫微》漫畫半自動生產線

把原本「Claude 寫腳本 → 手動貼給 ChatGPT 生圖」的流程，改造成可重複執行的
pipeline。**文字不再由 AI 畫進圖裡**：圖像模型只畫無文字的畫面，中文對白、
旁白、金框、頁碼全部由排版引擎以真實字型繪製——改稿不必重新生圖、永遠沒有錯字。

```
comic/
├── style/
│   ├── STYLE_GUIDE.md      # 視覺風格規格書(由既有成品逆向整理)
│   ├── style_anchor.txt    # 每格 prompt 共用的風格錨點
│   ├── characters.md       # 角色外觀設定(中文+英文 prompt)
│   └── refs/               # ★把既有成品頁放這裡, 生圖時作為風格參考圖
├── episodes/ep16/
│   ├── script.md           # 人類可讀腳本 ←【檢查點1: 作者審核故事】
│   └── panels.json         # 機器可讀分鏡(畫面prompt+對白)
├── pipeline/
│   ├── generate_art.py     # 呼叫圖像模型逐格生圖(OpenAI/Gemini 可切換)
│   └── assemble.py         # 排版引擎: 金框+直式文字+泡泡+頁碼
├── art/ep16/               # 生成的分格畫 ←【檢查點2: 作者審核畫面】
└── out/ep16/               # 完成頁面 page_01.png …
```

## 每一話的流程

```bash
# 0) 一次性: 把 4~5 張既有成品頁放進 comic/style/refs/

# 1) 腳本(Claude 產出) → 作者審 script.md, 有修改就同步改 panels.json

# 2) 生圖(需要 API key, 只畫「無文字」畫面)
export OPENAI_API_KEY=sk-...        # 或 GEMINI_API_KEY=...
python3 comic/pipeline/generate_art.py comic/episodes/ep16

# 3) 排版(不需要 API key, 隨時可跑; 缺圖的格子會以佔位圖呈現)
python3 comic/pipeline/assemble.py comic/episodes/ep16

# 4) 作者看 comic/out/ep16/ 成品。哪格不滿意就重生成那一格:
python3 comic/pipeline/generate_art.py comic/episodes/ep16 --panels p3a --force
python3 comic/pipeline/assemble.py comic/episodes/ep16 --pages 3
```

## 人工檢查點(刻意保留)

| 檢查點 | 檔案 | 通過條件 |
|---|---|---|
| 1. 故事/命理內容 | `episodes/epNN/script.md` | 作者勾選審核備註 |
| 2. 畫面風格一致 | `art/epNN/*.png` 或 `out/epNN/*.png` | 作者逐頁確認, 不合格單格重生成 |

## 風格一致性的三道保險

1. `style_anchor.txt` 逐字嵌入每一格 prompt 開頭。
2. `characters.md` 的角色 prompt 逐字重複使用, 不改寫。
3. `style/refs/` 的既有成品頁隨每次 API 呼叫送出當參考圖。

## 分工(誠實版)

- **Claude 做得到**: 腳本、占驗派命理內容、分鏡、prompt、排版引擎、風格規格、
  自動化程式、(未來)用視覺能力檢查生成結果是否走樣。
- **Claude 做不到**: 直接畫出工筆水彩畫質的點陣圖 → 這一步交給
  `gpt-image-1` 或 `gemini-2.5-flash-image`(擇一, 設對應環境變數即可)。

## 依賴

```bash
pip3 install pillow requests
```

字型 `fonts/NotoSerifTC.ttf` 缺少時 `assemble.py` 會自動下載(Google Fonts, OFL 授權)。
