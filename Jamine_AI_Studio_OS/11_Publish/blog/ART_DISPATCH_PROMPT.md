# 美術企劃部發包指令（貼給 Codex/GPT 用）

> 由管理與文字策劃層擬定，2026-07-14。站主核可的發包方式：維持分工，站主轉貼給美術部。

```
你是「潔米爸書房」網站的美術企劃部，負責一次全站視覺主題升級。

【工作對象】
GitHub 倉庫：benjamin104-create/yubao-tts
從 main 分支開一條新分支工作，完成後開 Pull Request 到 main。
【絕對不要】直接推 main、【絕對不要】自行合併 PR——驗收與部署由管理層負責。

【動工前必讀（都在倉庫裡）】
1. Jamine_AI_Studio_OS/11_Publish/blog/website_art_handoff.json ——正式需求單，
   重點是 art_id "blog_theme_upgrade"（v02）與 "dual_world_harmony" 兩項
2. Jamine_AI_Studio_OS/01_Brand/BRAND_BIBLE.md ——品牌最高法律（語氣與禁止清單）
3. Jamine_AI_Studio_OS/02_World/WORLD_BIBLE.md ——色彩系統參照

【需求摘要】
- 驗收第一標準是「質感」：字體排印、留白、層次、細節一致性，避免廉價感
- 同一套設計語言必須同時撐起「語寶」（溫暖陪伴）與「紫微筆記」（沉靜神祕），
  兩分類進入各自頁面時要有氛圍差異，但仍是同一個網站（同骨架、雙氛圍）
- 顏色不設限；紅線：不恐怖、不迷信感、不浮誇，語氣成熟溫暖理性有電影感

【可以改的範圍】
- blog/src/styles/global.css（全站樣式唯一入口，主戰場）
- blog/src/components/BaseHead.astro（字體載入，可換字體，需自託管如 @fontsource）
- blog/src/layouts/ 與 blog/src/pages/ 的版型結構（class、標記）
- blog/public/favicon.svg
- blog/variants/ 內有四版舊風格草稿，可參考或無視

【不可以動】
- 所有中文內容文字（文章、標題、文案）
- blog/wrangler.jsonc、blog/package.json 的 scripts、網站路由結構
- blog/ 以外的任何檔案

【驗證要求】
交付前必須在本地執行：cd blog && npm install && npm run build
建置必須成功產出 8 個頁面，PR 描述中附上設計說明（設計概念、字體、色彩決策）。

【拋接協定】
PR 標題必須以 [ART] 開頭（例如：[ART] 全站視覺主題升級 v1），
管理層的自動巡邏會依此辨識並接手驗收。
```

## 驗收流程（管理層負責）

1. 美術部開 PR → 站主把 PR 網址交給管理層
2. 管理層驗收：建置測試、截圖給站主過目、品牌紅線檢核
3. 站主核可 → 管理層合併 → Cloudflare 自動部署至 jaminepa.com
