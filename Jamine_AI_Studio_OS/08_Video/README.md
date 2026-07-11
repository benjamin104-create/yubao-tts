# 08 — 影片生成 (Video)

> Shot Prompt → Kling / Seedance → MP4。影片生成中心。

## 流程

```
07_Prompts 的 Shot Prompt 卡
        │  批次送入
   Kling / Seedance
        │
      MP4（單鏡頭）
        │  命名 + 入庫
   08_Video/{PROJECT}/S{季}/E{集}/
        │
     交 10_Edit（DaVinci）
```

## 命名

`{PROJECT}_S{季}_E{集}_shot_{編號}_{工具}_v{版本}.mp4`
例：`JMD_S01_E01_shot_012_kling_v01.mp4`

## 生成守則

- 一律用 Prompt Engine 的輸出，不臨場手改角色外型（會破壞一致性）。
- 同一鏡頭多版本全部保留（`v01`, `v02`），由 QA / Editor 挑選。
- 可重用的畫面元素回報 `04_Assets` 登記入庫。

## 子路徑

```
08_Video/{PROJECT}/S{季}/E{集}/
```

## Phase 2 自動化目標

DeepSeek Production Worker 批次：讀分鏡表 → 逐列生成 → 自動命名 → 自動歸檔。
