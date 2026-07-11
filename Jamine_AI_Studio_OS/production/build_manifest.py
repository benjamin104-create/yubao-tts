"""build_manifest.py — 從分鏡 + Shot Prompt 卡組出機器可讀的 render manifest。

manifest 是「要生成什麼」的唯一真相來源；render_video.py / render_voice.py 都吃它。

用法：
  python build_manifest.py <storyboard.md> <shot卡資料夾> <輸出 manifest.json> \
      [--project JMD --season 01 --episode 01 --tool kling --aspect 2.39:1]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 借用 automation/ 的分鏡解析
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automation"))
import studio  # noqa: E402


def _prompt_from_card(card: Path) -> str:
    if not card.exists():
        return ""
    m = re.search(r"```\s*\n(.*?)\n```", card.read_text(encoding="utf-8"), re.DOTALL)
    return m.group(1).strip() if m else ""


def build(storyboard: Path, cards_dir: Path, project: str, season: str,
          episode: str, tool: str, aspect: str) -> dict:
    rows = studio.parse_storyboard(storyboard)
    prefix = f"{project}_S{season}_E{episode}"
    jobs = []
    for row in rows:
        num = row["#"].zfill(3)
        card = cards_dir / f"{prefix}_shot_{num}_v01.md"
        sec = re.sub(r"[^\d.]", "", row.get("秒", "")) or "5"
        jobs.append({
            "shot": num,
            "prompt": _prompt_from_card(card),
            "duration_sec": float(sec),
            "aspect": aspect,
            "tool": tool,
            "output": f"{prefix}_shot_{num}_{tool}_v01.mp4",
            "characters": row.get("角色", "—"),
            "dialogue": row.get("對白/旁白", ""),
            "status": "pending",
        })
    return {
        "project": project, "season": season, "episode": episode,
        "aspect": aspect, "tool": tool, "count": len(jobs), "jobs": jobs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("cards_dir")
    ap.add_argument("out")
    ap.add_argument("--project", default="JMD")
    ap.add_argument("--season", default="01")
    ap.add_argument("--episode", default="01")
    ap.add_argument("--tool", default="kling")
    ap.add_argument("--aspect", default="2.39:1")
    a = ap.parse_args()
    manifest = build(Path(a.storyboard), Path(a.cards_dir), a.project,
                     a.season, a.episode, a.tool, a.aspect)
    Path(a.out).write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    empty = [j["shot"] for j in manifest["jobs"] if not j["prompt"]]
    print(f"✅ manifest：{manifest['count']} 個 job → {a.out}")
    if empty:
        print(f"⚠️  {len(empty)} 個鏡頭找不到 Prompt 卡：{empty}")


if __name__ == "__main__":
    main()
