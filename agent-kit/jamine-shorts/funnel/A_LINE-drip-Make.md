# A. 免費 DIY LINE 養客 drip（Make + LINE Messaging API + Google Sheet）

不用付 MAAC。用你已經會的 Make，自己做「加 LINE → 自動分天推 2–3 則價值 → 導購 Portaly」。

## 0. 一次性準備
1. **LINE 官方帳號**(免費)→ 後台開啟 **Messaging API**。
2. 到 **LINE Developers**：建 Provider → Channel（Messaging API）→ 取得
   - `Channel access token`（長期）
   - `Channel secret`
3. **Webhook**：在 Channel 設定把 Webhook URL 指向 **Make 的 Custom Webhook**，並「啟用 Webhook」。
4. 建一張 Google Sheet **`LINE名單CRM`**，欄位：
   `userId | 暱稱 | 加入日 | 來源關鍵字 | 標籤 | 已推到第幾天 | 階段(養客/導購/已購/退出) | 已購(Y/N) | 備註`

## 場景 1：收名單（即時，加好友就觸發）
Make 場景：
1. **Webhook（Custom webhook）** ← LINE 把事件丟進來。
2. **Iterator** 拆 `events[]`。
3. **Router**：判斷 `events[].type`
   - `follow`（加好友）：
     a. **HTTP – Make a request**：`GET https://api.line.me/v2/bot/profile/{userId}`，Header `Authorization: Bearer {TOKEN}` → 取暱稱。
     b. **Google Sheets – Add a Row**：寫入 userId、暱稱、加入日=now、階段=養客、已推到第幾天=0。
     c. **HTTP**：`POST https://api.line.me/v2/bot/message/push`（推 Day0 歡迎＋小禮物，內容見 B）。
   - `message`（含關鍵字）：可另外回覆（選配）。

## 場景 2：每日 drip（排程，每天跑一次）
Make 場景（左下 Schedule 設「每天 10:00」）：
1. **Google Sheets – Search Rows**：篩 `階段=養客 或 導購` 且 `已購≠Y`。
2. 每列用 **Tools – Set variable** 算 `天數 = 今天 - 加入日`。
3. **Router + Filter** 依天數推對應訊息（都用 HTTP push）：
   | 天數 | 動作 | 推完更新 |
   |---|---|---|
   | 1 | 推 價值1 | 已推=1 |
   | 2 | 推 價值2 | 已推=2 |
   | 3 | 推 價值3＋軟提案 | 已推=3、階段=導購 |
   | 4 | 推 導購（Portaly 連結） | 已推=4 |
   | 6 | 未購→推 溫柔提醒 | 已推=6 |
4. **Google Sheets – Update a Cell**：更新「已推到第幾天 / 階段」。

> 防呆：用「已推到第幾天」避免同一天重複推；`已購=Y` 直接跳過。

## LINE push 範例（HTTP 模組 Body）
```
POST https://api.line.me/v2/bot/message/push
Headers: Authorization: Bearer {Channel access token}
         Content-Type: application/json
Body:
{ "to": "{{userId}}",
  "messages": [ { "type": "text", "text": "（B 裡的訊息）" } ] }
```

## 場景 3：購買回寫（看 Portaly 能力）
- **若 Portaly 有訂單 Webhook/通知** → Make 接 → 在 CRM 把該人 `已購=Y、階段=已購`，停止 drip，推感謝＋邀社群。
  - 對應 userId 的方法：導購連結帶參數（如 `?u={{userId}}`）或用 email 對應。
- **若沒有 Webhook** → 定期匯出 Portaly 訂單，手動/半自動在 CRM 標已購。
  - ⚠️ 先到 Portaly 後台確認有沒有 Webhook / API / 訂單匯出。

## 成本
- LINE OA 免費版：每月有免費訊息額度（超過才付費）。小規模幾乎 0 元。
- Make 免費版：每月約 1,000 ops，數百名單足夠。
- 全程不用付 MAAC。
