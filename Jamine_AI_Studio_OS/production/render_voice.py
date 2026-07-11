"""render_voice.py — 批次把配音腳本合成語音（09_Voice）。

沿用本 repo tts_gateway.py 已驗證的 Google Cloud TTS 請求格式，
但目標語言改成國語旁白/對白（cmn-TW），並依 Character Bible 給每個角色固定聲線。

⚠️ 誠實說明：語寶的「中文」在前端是用瀏覽器內建語音（browser provider），後端不合成；
   要在後端/批次產生國語配音，需 Google Cloud TTS 金鑰（cmn-TW 語音）。
   本沙箱無金鑰且無法連外，故預設 --dry-run：驗證腳本、組出每句 payload，不呼叫 API。

角色聲線（對應 03_Characters 的「聲音」段）：
  潔米爸 → cmn-TW-Wavenet-C（男·低沉·慢）   speakingRate 0.85
  阿哲   → cmn-TW-Wavenet-B（男·中·偏快）   speakingRate 1.05
  小薇   → cmn-TW-Wavenet-A（女·清亮·穩）   speakingRate 1.0

環境變數（真跑時）：GOOGLE_TTS_KEY

用法：
  python render_voice.py <voice_cue_sheet.md> <輸出資料夾> [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
from pathlib import Path

VOICES = {
    "潔米爸": {"name": "cmn-TW-Wavenet-C", "rate": 0.85, "pitch": -2.0, "slug": "jamie-dad"},
    "阿哲":   {"name": "cmn-TW-Wavenet-B", "rate": 1.05, "pitch": 0.0,  "slug": "ah-zhe"},
    "小薇":   {"name": "cmn-TW-Wavenet-A", "rate": 1.0,  "pitch": 1.0,  "slug": "xiao-wei"},
}
DEFAULT_VOICE = {"name": "cmn-TW-Wavenet-B", "rate": 1.0, "pitch": 0.0, "slug": "narrator"}


def parse_cue_sheet(path: Path) -> list[dict]:
    """讀配音腳本 markdown 表格，回傳有台詞的列。"""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6 or cells[0] in {"#", ""} or set("".join(cells)) <= set("-: "):
            continue
        rows.append({"shot": cells[0], "char": cells[1], "emotion": cells[2],
                     "sec": cells[3], "line": cells[5]})
    return rows


def build_payload(char: str, text: str) -> dict:
    v = VOICES.get(char, DEFAULT_VOICE)
    return {
        "input": {"text": text},
        "voice": {"languageCode": "cmn-TW", "name": v["name"]},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": v["rate"], "pitch": v["pitch"]},
    }


def synth_google(key: str, payload: dict) -> bytes:
    import urllib.request
    req = urllib.request.Request(
        f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        return base64.b64decode(json.loads(r.read().decode())["audioContent"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cue_sheet")
    ap.add_argument("outdir")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prefix", default="JMD_S01_E01")
    a = ap.parse_args()

    rows = parse_cue_sheet(Path(a.cue_sheet))
    key = os.environ.get("GOOGLE_TTS_KEY", "")
    dry = a.dry_run or not key

    outdir = Path(a.outdir)
    (outdir / "payloads").mkdir(parents=True, exist_ok=True)

    print(f"=== render_voice ===  台詞 {len(rows)} 句  "
          f"{'DRY-RUN（未實際合成）' if dry else 'LIVE'}")
    if dry and not key:
        print("ℹ️  未偵測到 GOOGLE_TTS_KEY → 自動切 dry-run。")

    for r in rows:
        v = VOICES.get(r["char"], DEFAULT_VOICE)
        text = re.sub(r"…$", "。", r["line"]).strip()
        payload = build_payload(r["char"], text)
        out = f"{a.prefix}_voice_{v['slug']}_{r['shot'].zfill(3)}_v01.mp3"
        (outdir / "payloads" / f"{out}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if dry:
            print(f"  shot {r['shot']}: [{r['char']}/{v['name']}] 「{text}」→ {out}")
        else:
            try:
                (outdir / out).write_bytes(synth_google(key, payload))
                print(f"  shot {r['shot']}: ✅ {out}")
            except Exception as e:  # noqa: BLE001
                print(f"  shot {r['shot']}: ❌ {type(e).__name__}: {e}")

    if dry:
        print(f"\npayload 已寫到 {outdir/'payloads'}。設 GOOGLE_TTS_KEY 後拿掉 --dry-run 即真合成。")


if __name__ == "__main__":
    main()
