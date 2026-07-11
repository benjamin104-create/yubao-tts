# 製作流程 (Production Pipeline)

> 一部作品從無到有，怎麼跑完整條線。誰接誰、AI 在哪一段接手。

---

## 端到端流程

```
                    ┌── 01 Brand ──┐
   永遠固定的基底 ───┤   02 World    ├──► 每個環節都先讀
                    └── 03 Char ────┘

  ①  Screenwriter (Claude)   ── 依 Bible 寫劇本 ──►  05_Scripts
  ②  Director   (Claude)     ── 審核品牌合規/弧線 ──►  過關才往下
  ③  Cinematographer         ── 拆 ~40 鏡頭、定運鏡/光線 ──►  06_Storyboard
  ④  Prompt Engineer (DeepSeek) ── 六格 → 3000字 Prompt ──►  07_Prompts
       └ 組合 camera / emotion / lighting 三庫 + 04_Assets 重用
  ⑤  Production Worker (DeepSeek) ── 批次生成 ──►  Kling/Seedance ──►  08_Video (MP4)
  ⑥  Voice (語寶 TTS)         ── 角色固定聲線 ──►  09_Voice (WAV)
  ⑦  Editor                  ── DaVinci 剪輯/字幕/節奏 ──►  10_Edit (final MP4)
  ⑧  QA Agent                ── 全程巡檢一致性/缺鏡頭 ──►  回報
  ⑨  Marketing Manager       ── 拆多平台內容 ──►  11_Publish
  ⑩  封存 + 回收素材          ──►  12_Archive (+ 更新 04_Assets)
```

---

## 每個交接點的「完成定義」(Definition of Done)

| 交接 | 完成條件 |
|------|----------|
| 劇本 → 分鏡 | Director 通過品牌合規 + 情緒弧線收在釋懷 |
| 分鏡 → Prompt | 每個鏡頭都有場景/情緒/運鏡/光線四欄 |
| Prompt → 影片 | 角色用定裝錨句、素材優先重用 |
| 影片 → 剪輯 | 鏡頭齊全、命名正確、QA 無缺鏡頭 |
| 剪輯 → 發布 | 定稿 `_FINAL`、字幕乾淨、回扣信念句 |
| 發布 → 封存 | 可重用素材已回登 `04_Assets` |

---

## Roadmap 對照

| Phase | 這條線的哪幾段自動化 |
|-------|---------------------|
| Phase 1（本次） | 全線的**規格與 Bible** 建好——人可以照著跑 |
| Phase 2 | ①②④⑤ 由 Claude/DeepSeek 自動接手（拆劇本、生 Prompt、批次生成、整理版本） |
| Phase 3 | 正式跑《潔米爸》S01，累積素材資產 |
| Phase 4 | ⑨ 內容工廠全自動拆解 |

---

## 一致性三支柱（整條線的品質底線）

1. **角色一致** ← Character Bible 定裝錨句
2. **世界一致** ← World Bible 冷暖光線
3. **品牌一致** ← Brand Bible 禁止清單 + 信念句

QA Agent 的工作，就是守住這三根柱子。
