# 潔米爸書房（jaminepa.com）

用 [Astro](https://astro.build) 打造的個人部落格，部署在 Cloudflare 上。

## 內容分類

| 分類 | 網址 | 內容 |
|------|------|------|
| 語寶 | `/yubao/` | 育兒觀、語言自學、旅遊、各國地理文化歷史 |
| 紫微筆記 | `/ziwei/` | 紫微斗數自學筆記、紫微斗數漫畫 |

## 如何發佈新文章

1. 在 `src/content/blog/yubao/` 或 `src/content/blog/ziwei/` 裡新增一個 `.md` 檔案（檔名用英文，例如 `my-first-trip.md`，它會成為網址的一部分）。
2. 檔案開頭照這個格式填：

```markdown
---
title: 文章標題
description: 一兩句話的摘要（會顯示在列表和搜尋結果）
pubDate: 2026-07-13
category: yubao        # 語寶用 yubao，紫微筆記用 ziwei
tags: [育兒]
---

這裡開始用 Markdown 寫內文。
```

3. 存檔後推上 GitHub 的 `main` 分支，Cloudflare 會自動重新建置並發佈，約 1～2 分鐘後生效。

## 圖片

放進 `public/images/`，文章內用 `![說明](/images/檔名.jpg)` 引用。

## 本機開發（選用）

```bash
npm install     # 第一次先安裝套件
npm run dev     # 開發預覽，瀏覽 http://localhost:4321
npm run build   # 建置，輸出到 dist/
```

## 部署設定（Cloudflare）

- 建置指令：`npm run build`
- 輸出資料夾：`dist`
- Workers 部署設定在 `wrangler.jsonc`
