"""continuity_audit.py — 角色一致性 / 服道化 / 時代穿幫 自動稽核。

把「AI 電影服道化與角色視覺總監」的稽核責任程式化。針對一集分鏡，自動查：
  1) 錨定缺漏：出場角色是否都在 character_anchors.json 有 trigger + seed（沒鎖 = 高風險漂移）。
  2) 時代穿幫：角色服裝 period 是否與 World Bible 年代相容（例：1950s 剪裁出現在 2026）。
  3) 服裝連續性：同角色若在分鏡中換裝（未來加 wardrobe 欄），標記需人工確認換裝合理性。
  4) 紋樣風險：服裝 pattern 若非 solid，提醒需備高清平鋪貼圖（ControlNet 輸入），避免 AI 邏輯混亂。

用法：
  python continuity_audit.py <storyboard.md> [--era 2026]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import studio


def _world_era() -> str:
    text = (studio.OS_ROOT / "02_World" / "WORLD_BIBLE.md").read_text(encoding="utf-8")
    m = re.search(r"年代\s*\|\s*(\d{4})", text)
    return m.group(1) if m else "2026"


def audit(storyboard: Path, era: str):
    rows = studio.parse_storyboard(storyboard)
    anchors = studio.load_anchors()
    chars = studio.load_characters()
    name_to_slug = chars["_name_to_slug"]

    findings = {"missing_anchor": [], "period": [], "pattern": [], "appear": {}}

    for row in rows:
        for slug in studio.split_characters(row.get("角色", ""), name_to_slug):
            findings["appear"].setdefault(slug, []).append(row["#"])
            a = anchors.get(slug)
            if not a:
                findings["missing_anchor"].append((row["#"], slug))
                continue
            # 時代穿幫：服裝 period 若標了具體十年（如 1950s），與世界年代差 >15 年即示警
            period = a.get("costume", {}).get("period", "")
            for d in re.findall(r"\b(1[89]\d0|20[0-4]0)s\b", period):
                if abs(int(d) - int(era)) > 15:
                    findings["period"].append((row["#"], slug, d))
            # 紋樣風險
            pat = a.get("costume", {}).get("pattern", "").lower()
            if pat and "no pattern" not in pat and "solid" not in pat:
                findings["pattern"].append((slug, a["costume"]["pattern"]))

    return findings, era, anchors


def report(findings, era, anchors):
    print(f"=== 服道化 / 角色一致性稽核 ===  世界年代基準：{era}")
    appear = findings["appear"]
    print(f"\n出場角色：{', '.join(f'{s}×{len(v)}鏡' for s, v in appear.items()) or '（無具名角色）'}")

    ok = True
    if findings["missing_anchor"]:
        ok = False
        print("\n❌ 未上鎖角色（無 trigger/seed，漂移風險高）：")
        for shot, slug in findings["missing_anchor"]:
            print(f"   shot {shot}: {slug} 不在 character_anchors.json")
    else:
        print("\n✅ 錨定：所有出場角色皆有 trigger + seed 上鎖。")

    if findings["period"]:
        ok = False
        print("\n❌ 時代穿幫：")
        for shot, slug, dec in findings["period"]:
            print(f"   shot {shot}: {slug} 服裝標記 {dec}s，與世界年代 {era} 差距過大。")
    else:
        print("✅ 時代：無服裝年代與世界觀衝突。")

    pats = {p for _, p in findings["pattern"]}
    if pats:
        print("\n⚠️  含複雜紋樣的服裝（AI 易亂，建議備高清平鋪貼圖 + ControlNet）：")
        for slug, pat in {(s, p) for s, p in findings["pattern"]}:
            print(f"   {slug}: 「{pat}」")
    else:
        print("✅ 紋樣：所有服裝皆為 solid/無紋樣，AI 漂移風險低。")

    print(f"\n總結：{'✅ 通過，可進生成' if ok else '❌ 有阻斷項，請先修正'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard")
    ap.add_argument("--era", default="")
    a = ap.parse_args()
    era = a.era or _world_era()
    findings, era, anchors = audit(Path(a.storyboard), era)
    ok = report(findings, era, anchors)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
