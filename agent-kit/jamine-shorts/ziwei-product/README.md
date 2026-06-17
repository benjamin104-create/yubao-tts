# 進階紫微筆記 — 產品製作 pipeline

潔米爸紫微數位筆記（PDF）的製圖、去背、排版工具與素材。

## 內容
- `scripts/diecut_ip.py` — IP 貼圖去背（rembg AI 抓人物保留白衣 + 平滑白邊 die-cut）。`python3 diecut_ip.py 來源 輸出`
- `scripts/build_book.py` — PIL 排版引擎，把校對內容生成「精裝書 PDF」（封面+使用說明+各宮命盤圖+詳表+結語）。
- `templates/命盤放射圖_範本.html` — 命盤放射圖（中央宮位+四周主星輻射），改 stars 陣列即可換宮。1450×1450，render 後抽幀。
- `templates/landing頁.html` — 白底發表會 Landing（白底貼圖免去背）。
- `ip/` — 9 款潔米爸 IP 去背乾淨版（avatar/好耶/不客氣/拜託/休息一下/可以喔/馬上到/先忙囉/在嗎）。
- `封面.png` — 第1部封面。

## 設計規格
- 品牌：暗暖底 #0d0a07 / 金 #E0A24E / 米白文字。Landing 用白底 #fbf6ec。
- 命盤圖不放 IP（避免去背切到手）；IP 放封面(圓頭貼)、白底頁、宣傳圖。
- 校對內容來源：`../../ziwei-notes/`（第1部已校對定稿）。

## 製作流程
1. 校對 `ziwei-notes/` → 商品版內容。
2. 各宮用 `命盤放射圖_範本.html` 改資料 → HyperFrames render → PNG。
3. `build_book.py` 生成詳表頁 + 組 PDF（用系統 /etc/alternatives/fonts-japanese-gothic.ttf，繁中紫微術語可正確顯示）。
4. 上 Portaly 數位商品（第1部 NT$300 / 全套 NT$990）。

## 依賴
Node22 + HyperFrames + ffmpeg-static/ffprobe-static（render）；Python：rembg、Pillow、img2pdf。

## ⚠️ 字型（重要）
PDF 詳表頁**必須用正版繁體中文字型 Noto Sans TC**，不可用系統的日文 Gothic（會缺字「內哪娛懂歲產說闆」等→變方框怪字）。
下載：`curl -L -o NotoSansTC.ttf "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf"`
`build_book.py` 內 `FONT` 指向該檔；標題用變數字型 wght=700 加粗。
