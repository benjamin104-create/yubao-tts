"""build_shots.py — 一鍵批次：分鏡 → 全部 Shot Prompt 卡 + 素材報告 + 配音腳本。

這就是 Production Pipeline 第 ④⑤ 步的自動化：讀分鏡表，逐列用 Prompt Engine
展開成完整 Prompt，寫成 Shot Prompt 卡；同時跑素材比對與配音腳本。

用法：
  python build_shots.py <storyboard.md> <輸出資料夾> [--project JMD --season 01 --episode 01]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import asset_check
import prompt_engine
import studio
import voice_cue_sheet

CARD = """# {stem} — Shot Prompt 卡（自動產生）

## 六格輸入

| 欄位 | 值 |
|------|-----|
| 角色 | {char} |
| 情緒 | {emotion} |
| 場景 | {scene} |
| 運鏡 | {camera} |
| 光線 | {lighting} |

## 引擎輸出（完整 Prompt）

```
{prompt}
```

## 生成結果

| 欄位 | 內容 |
|------|------|
| 生成工具 | Kling / Seedance |
| 輸出檔 | `{video}`（待生成） |
| 狀態 | ☐ 待生成 |
| 對白/旁白 | {dialogue} |
"""


def run(storyboard: Path, outdir: Path, project: str, season: str, episode: str):
    outdir.mkdir(parents=True, exist_ok=True)
    libs = studio.load_libraries()
    chars = studio.load_characters()
    anchors = studio.load_anchors()
    rows = studio.parse_storyboard(storyboard)

    prefix = f"{project}_S{season}_E{episode}"
    made = 0
    last_key = None          # carry-forward：上一個成功比對的地點
    carried, unresolved = [], []
    matrix = []              # Prompt 驗證矩陣：每鏡頭角色 trigger 是否嵌入
    for row in rows:
        num = row["#"].zfill(3)
        stem = f"{prefix}_shot_{num}_v01"
        scene = row.get("場景", "").strip()
        key = prompt_engine.match_scene_key(scene, libs)
        if key:
            last_key = key
        elif last_key:
            carried.append(row["#"])          # 用了上一鏡地點
        else:
            unresolved.append(row["#"])        # 完全無地點可用
        prompt = prompt_engine.build_from_shot(row, chars, libs,
                                               fallback_key=last_key, anchors=anchors)
        # 特徵查核：本鏡頭每個角色的 [SLUG] trigger 是否確實嵌入 prompt
        slugs = studio.split_characters(row.get("角色", ""), chars["_name_to_slug"])
        for s in slugs:
            a = anchors.get(s, {})
            tag = f"[{s.upper()}]"
            matrix.append({
                "shot": num, "slug": s,
                "trigger_ok": tag in prompt,
                "costume": a.get("costume", {}).get("id", "—"),
                "seed": a.get("seed", "—"),
            })
        card = CARD.format(
            stem=stem,
            char=row.get("角色", "—"),
            emotion=row.get("情緒", ""),
            scene=row.get("場景", ""),
            camera=row.get("運鏡", ""),
            lighting=row.get("光線", ""),
            prompt=prompt,
            video=f"{prefix}_shot_{num}_kling_v01.mp4",
            dialogue=row.get("對白/旁白", "").replace("|", "/"),
        )
        (outdir / f"{stem}.md").write_text(card, encoding="utf-8")
        made += 1
    print(f"✅ 產出 {made} 張 Shot Prompt 卡 → {outdir}")
    if carried:
        print(f"[地點] {len(carried)} 鏡沿用上一鏡地點（carry-forward）：{carried}")
    if unresolved:
        print(f"⚠️  [地點] {len(unresolved)} 鏡無地點可解析，請於分鏡補地點：{unresolved}")

    # 素材比對（缺口 #1）
    _, known, missing = asset_check.check(storyboard)
    print(f"\n[素材] 已登記 {len(known)} 種；缺 {len(missing)} 種：{sorted(missing)}")

    # 配音腳本（缺口 #2/#3）
    vsheet = outdir / f"{prefix}_voice_cue_sheet.md"
    vsheet.write_text(voice_cue_sheet.build(storyboard), encoding="utf-8")
    print(f"[配音] 已寫出 {vsheet.name}")

    # Prompt 驗證矩陣（角色一致性上鎖）
    _write_matrix(outdir / f"{prefix}_prompt_validation_matrix.md", matrix, prefix)
    fails = [m for m in matrix if not m["trigger_ok"]]
    print(f"[驗證矩陣] {len(matrix)} 個角色出場，trigger 全嵌入："
          f"{'✅' if not fails else '❌ 缺 '+str([m['shot'] for m in fails])}")


def _write_matrix(path: Path, matrix, prefix):
    lines = [f"# {prefix} — Prompt 驗證矩陣",
             "",
             "> 由 build_shots 自動產生。查核每鏡頭每個角色的 `[SLUG]` trigger 是否逐字嵌入 Prompt，"
             "並列出鎖定的服裝 id 與 seed。trigger✅ = 角色核心特徵已強制帶入。",
             "",
             "| shot | 角色 | trigger 嵌入 | 服裝 id | seed |",
             "|------|------|:---:|--------|------|"]
    for m in matrix:
        lines.append(f"| {m['shot']} | {m['slug']} | {'✅' if m['trigger_ok'] else '❌'} "
                     f"| {m['costume']} | {m['seed']} |")
    fails = [m for m in matrix if not m["trigger_ok"]]
    lines += ["", f"**結果：{len(matrix)} 個角色出場，"
              f"{'全部 trigger 已嵌入 ✅' if not fails else '有 '+str(len(fails))+' 個缺 trigger ❌'}**"]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("outdir")
    ap.add_argument("--project", default="JMD")
    ap.add_argument("--season", default="01")
    ap.add_argument("--episode", default="01")
    args = ap.parse_args()
    run(Path(args.storyboard), Path(args.outdir),
        args.project, args.season, args.episode)


if __name__ == "__main__":
    main()
