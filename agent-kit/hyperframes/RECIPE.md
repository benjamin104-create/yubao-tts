# HyperFrames 短影音 — 實測可用配方

> 這份是我在雲端環境**實際 render 成功**後整理的步驟（含踩到的坑）。本機照做更順（本機有 apt 可裝 ffmpeg）。

## HyperFrames 是什麼
HeyGen 開源的「**agent 寫 HTML/CSS/JS → 算成 MP4**」工具。沒有專有時間軸格式，動畫用 GSAP/CSS/Lottie/Three.js。
GitHub：`heygen-com/hyperframes`，文件：<https://hyperframes.heygen.com>。基本功能**不需要 API key**。

## 系統需求
- Node.js **22+**
- **FFmpeg + FFprobe**（編碼用）
- Headless Chrome（HyperFrames 第一次 render 會自動下載 ~107MB）

## 建立與 render
```bash
npx hyperframes init my-video && cd my-video
npm install
npm run dev      # 瀏覽器預覽（背景跑）
npm run check    # lint + validate
npm run render   # 輸出到 renders/*.mp4
```

## 六步驟流程（你截圖那套）
1. **主題輸入** → 給 Agent 主題
2. **內容規劃** → Agent 寫腳本、分鏡、字幕、素材清單
3. **HeyGen 任務準備** → 整理 avatar / voice / script（要數字人才需要）
4. **數字人生成** → HeyGen 產 A-Roll 解說影片
5. **HyperFrames 編輯** → A-Roll 進 HyperFrames，加 B-Roll / 字幕 / 字卡 / 音效 / motion
6. **預覽與輸出** → preview 對節奏 → render MP4

> HyperFrames 負責的是第 5、6 步（合成與輸出）。第 4 步的數字人要另外接 HeyGen。

## ⚠️ 雲端環境踩到的坑（本機若網路受限也會遇到）
1. **沒有 ffmpeg/ffprobe，且 apt 不能用** → 用 npm 取得免裝版：
   ```bash
   npm i ffmpeg-static ffprobe-static
   # 把這兩個 binary 連到同一個資料夾並加進 PATH
   mkdir -p ~/hfbin
   ln -sf "$(node -e "console.log(require('ffmpeg-static'))")" ~/hfbin/ffmpeg
   ln -sf "$(node -e "console.log(require('ffprobe-static').path)")" ~/hfbin/ffprobe
   export PATH="$HOME/hfbin:$PATH"
   ```
   （只裝 ffmpeg-static 會卡在「FFprobe not found」—— 兩個都要。）
2. **CDN 被擋（jsdelivr 403）→ GSAP 載不到 → 動畫不會動**（症狀：render 卡 45 秒、log 出現
   `Sub-composition timelines not registered`）。解法：**把 GSAP 下載到專案內、用相對路徑引用**：
   ```bash
   npm i gsap && cp node_modules/gsap/dist/gsap.min.js ./gsap.min.js
   ```
   HTML 改成 `<script src="gsap.min.js"></script>`（不要用 CDN）。
3. **composition id 要一致**：根元素 `data-composition-id="root"`，timeline 也註冊成
   `window.__timelines["root"]`，兩邊名字必須對上。

## 最小可動範例（這次成功的開場）
重點：本地 GSAP + id 對齊 + 每個動畫元素用 `from/to` 並註冊 paused timeline。完整檔見本資料夾 `intro-example.html`。

```html
<script src="gsap.min.js"></script>
...
<div id="root" data-composition-id="root" data-start="0" data-duration="3"
     data-width="1920" data-height="1080"> ... </div>
<script>
  const tl = gsap.timeline({ paused: true });
  tl.from("#emoji", { opacity:0, scale:0.2, y:-60, duration:0.8, ease:"back.out(1.7)" }, 0)
    .from("#title", { opacity:0, y:60, duration:0.8 }, 0.3);
  window.__timelines = window.__timelines || {};
  window.__timelines["root"] = tl;   // ← 名字要跟 data-composition-id 一樣
</script>
```
