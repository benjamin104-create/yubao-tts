# 06 — 分鏡 (Storyboard)

把劇本拆成 ~40 個可生成的鏡頭。這一層是**劇本**與**Prompt 引擎**之間的橋。

- 範本：[`_TEMPLATE_storyboard.md`](_TEMPLATE_storyboard.md)
- 拆鏡：Cinematographer Agent 決定運鏡/光線；DeepSeek 批次展開（Phase 2）
- 每一列 → 一張 `07_Prompts` 的 Shot Prompt 卡 → 一支 `08_Video` 影片

## 子路徑

```
06_Storyboard/{PROJECT}/S{季}/E{集}/
```
