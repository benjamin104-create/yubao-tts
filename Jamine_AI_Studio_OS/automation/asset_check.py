"""asset_check.py — 缺口 #1 修補：素材需求自動比對。

掃分鏡的「需用素材」欄，比對 04_Assets 素材庫索引，
自動列出「庫裡還沒有」的素材，不必人工肉眼找。

用法：
  python asset_check.py ../06_Storyboard/JMD/S01/E01/JMD_S01_E01_storyboard_v01.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import studio


def check(storyboard_path: Path):
    rows = studio.parse_storyboard(storyboard_path)
    known = studio.load_asset_slugs()
    needed: dict[str, list[str]] = {}
    for row in rows:
        for tok in studio.split_assets(row.get("需用素材", "")):
            needed.setdefault(tok, []).append(row["#"])
    missing = {k: v for k, v in needed.items() if k not in known}
    return needed, known, missing


def main():
    if len(sys.argv) < 2:
        print("用法：python asset_check.py <storyboard.md>")
        sys.exit(1)
    path = Path(sys.argv[1])
    needed, known, missing = check(path)
    print(f"分鏡共引用 {len(needed)} 種素材，素材庫已登記 {len(known)} 種。")
    if not missing:
        print("✅ 全部素材皆已入庫。")
        return
    print(f"\n⚠️  缺 {len(missing)} 種素材（需製作並登記 04_Assets）：")
    for slug, shots in sorted(missing.items()):
        print(f"  - {slug:32s} 首次出現於 shot {shots[0]}（共 {len(shots)} 鏡）")


if __name__ == "__main__":
    main()
