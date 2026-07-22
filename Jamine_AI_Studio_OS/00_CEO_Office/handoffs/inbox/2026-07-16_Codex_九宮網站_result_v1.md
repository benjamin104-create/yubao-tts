STATUS: DONE
任務：WEB-001 九宮腦內革命網站建置 v1

## 交付摘要

- 已依九宮網站需求，在獨立工作分支完成九宮首頁、八個入口／本體頁骨架，以及全站一致的導覽與視覺狀態。
- 變更範圍嚴格限制於 `blog/`，未修改其他路徑。
- 網站工作分支：`agent/grid9-site-v1`
- 網站提交：`be401b0`（建立九宮腦內革命網站 v1）
- 草稿 Pull Request：<https://github.com/benjamin104-create/yubao-tts/pull/9>
- PR 標題：`[WEB] WEB-001 九宮腦內革命網站建置 v1`
- PR 目標分支：`main`
- PR 狀態：Draft／未合併

## 完成內容

### 九宮首頁與入口

- 桌機版採 3 × 3 九宮格：
  - 第一排：白、藍、黑
  - 第二排：綠、核心、灰
  - 第三排：語寶、紅、卡牌
- 九個入口分別連至：
  - 白：`/quiz/`
  - 藍：`/personas/blue/`
  - 黑：`/personas/black/`
  - 綠：`/personas/green/`
  - 核心：`/self/`
  - 灰：`/ziwei/`
  - 語寶：`/yubao/`
  - 紅：`/personas/red/`
  - 卡牌：`/cards/`

### 視覺與互動

- 每格具獨立分類色、左側色軌、標籤與狀態圓點。
- Hover 時提供整卡色洗、上浮、色軌加寬與圓點放大，保留成熟、理性且不浮誇的動態語言。
- 九個世界頁共用相同網站骨架、Header、Footer 與返回九宮格操作。
- 字體改為自託管 Noto 系列，避免依賴外部字體服務。
- 更新 favicon 為九宮色彩識別。

### 響應式

- 桌機維持 3 欄九宮格。
- 手機切換為單欄，並針對 390px 與 420px 以下寬度修正標題、導覽與內容溢位。
- 已逐頁檢查九個入口在 390 × 844 視窗下的顯示與導覽。

## 變更檔案

1. `blog/public/favicon.svg`
2. `blog/src/components/BaseHead.astro`
3. `blog/src/components/Footer.astro`
4. `blog/src/components/Header.astro`
5. `blog/src/components/NineGrid.astro`
6. `blog/src/consts.ts`
7. `blog/src/layouts/BlogPost.astro`
8. `blog/src/layouts/WorldPage.astro`
9. `blog/src/pages/[category]/index.astro`
10. `blog/src/pages/about.astro`
11. `blog/src/pages/cards.astro`
12. `blog/src/pages/index.astro`
13. `blog/src/pages/personas/[persona].astro`
14. `blog/src/pages/quiz.astro`
15. `blog/src/pages/self.astro`
16. `blog/src/styles/global.css`

## 驗證結果

- `npm install`：成功。
- `npm run build`：成功。
- Astro 靜態建置：成功產出 15 個頁面。
- 桌機視覺驗證：1440 × 1000，九格為 3 欄、順序正確、無水平溢位。
- 手機視覺驗證：390 × 844，九宮首頁與九個入口皆無水平溢位。
- Browser console：未發現錯誤或警告。
- `git diff --check`：通過。
- GitHub checks：
  - `Workers Builds: yubao-tts`：通過。
  - `Workers Builds: jaminepa-blog`：失敗；此項亦發生於 `main` 與既有 PR，判定為既存 Cloudflare／專案設定問題。本次 `blog/` 在本機已成功完成 15 頁建置。

## 自我檢查

- [x] 僅修改 `blog/`
- [x] 九宮首頁與九個對應入口完成
- [x] 分類色與 Hover 狀態清楚
- [x] 手機版無水平溢位
- [x] 建置成功
- [x] 已開獨立草稿 PR 到 `main`
- [x] 未直接推送 `main`
- [x] 未自行合併 PR
