"""voice_cue_sheet.py — 缺口 #2 + #3 修補。

#2：從分鏡自動抽出配音腳本（逐鏡頭：角色 / 台詞 / 情緒 / 秒），直接餵語寶 TTS。
#3：估算台詞時長（中文 ≈ 5 字/秒），若超過鏡頭秒數即標警告。

用法：
  python voice_cue_sheet.py <storyboard.md> [輸出.md]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import studio

CH_PER_SEC = 5.0  # 中文口白粗估語速


def _speech(cell: str) -> str:
    """從「對白/旁白」欄取實際台詞；純環境描述（（…））回空字串。"""
    cell = cell.strip()
    if not cell or cell.startswith("（") and cell.endswith("）"):
        return ""
    # 取冒號後的內容（潔：… / 旁白：…）；沒有冒號則視為無台詞
    if "：" in cell:
        return cell.split("：", 1)[1].strip()
    return ""


def _char_count(text: str) -> int:
    return len(re.sub(r"[^一-鿿]", "", text))


def build(storyboard_path: Path) -> str:
    rows = studio.parse_storyboard(storyboard_path)
    out = ["# 配音腳本 (Voice Cue Sheet) — 自動產生",
           "",
           "> 由 `automation/voice_cue_sheet.py` 從分鏡抽出。餵給 09_Voice / 語寶 TTS。",
           "> ⏱ 欄位：估時 = 中文字數 ÷ 5。⚠️ = 台詞可能塞不下鏡頭秒數（缺口 #3）。",
           "",
           "| # | 角色 | 情緒 | 秒 | 估時 | 台詞 |",
           "|---|------|------|----|------|------|"]
    warnings = 0
    for row in rows:
        line = _speech(row.get("對白/旁白", ""))
        if not line:
            continue
        sec = re.sub(r"[^\d.]", "", row.get("秒", "")) or "0"
        sec_f = float(sec) if sec else 0.0
        est = _char_count(line) / CH_PER_SEC
        flag = " ⚠️" if est > sec_f > 0 else ""
        if flag:
            warnings += 1
        out.append(f"| {row['#']} | {row.get('角色','—')} | {row.get('情緒','')} "
                   f"| {sec} | {est:.1f}s{flag} | {line} |")
    out.append("")
    out.append(f"**估時超秒警告：{warnings} 處** —— 交 Editor 調整鏡頭長度或精簡台詞。")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("用法：python voice_cue_sheet.py <storyboard.md> [輸出.md]")
        sys.exit(1)
    src = Path(sys.argv[1])
    md = build(src)
    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text(md, encoding="utf-8")
        print(f"已寫出：{sys.argv[2]}")
    else:
        print(md)


if __name__ == "__main__":
    main()
