#!/usr/bin/env python3
"""逐格呼叫圖像模型生成「無文字」分格畫。

用法:
    export OPENAI_API_KEY=sk-...      # 或 GEMINI_API_KEY=...
    python3 comic/pipeline/generate_art.py comic/episodes/ep16 [--panels p1a,p2b]
                                            [--provider openai|gemini] [--force]

規則:
  - 每格 prompt = style_anchor.txt + 分格描述(角色/場景 token 自動展開)。
  - comic/style/refs/ 內的既有成品頁會作為風格參考圖一併送出(最多 3 張)。
  - 已存在 comic/art/ep<N>/<panel_id>.png 時跳過(--force 重生成)。
  - 文字一律不畫進圖裡，由 assemble.py 排版。
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("請先安裝 requests: pip3 install requests")

ROOT = Path(__file__).resolve().parent.parent  # comic/
STYLE_ANCHOR = (ROOT / "style" / "style_anchor.txt").read_text(encoding="utf-8").strip()
REFS_DIR = ROOT / "style" / "refs"
MAX_REFS = 3


def load_refs() -> list[Path]:
    if not REFS_DIR.exists():
        return []
    refs = sorted(p for p in REFS_DIR.iterdir()
                  if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    return refs[:MAX_REFS]


def expand(prompt: str, meta: dict) -> str:
    tokens = {**meta.get("cast", {}), **meta.get("scene", {})}
    for key, value in tokens.items():
        prompt = prompt.replace("{%s}" % key, value)
    return f"{STYLE_ANCHOR}\n\nScene: {prompt}"


# ---------------------------------------------------------------- OpenAI --
def gen_openai(prompt: str, refs: list[Path], out: Path):
    key = os.environ["OPENAI_API_KEY"]
    headers = {"Authorization": f"Bearer {key}"}
    if refs:
        files = [("image[]", (p.name, p.read_bytes(), "image/png")) for p in refs]
        data = {"model": "gpt-image-1", "prompt":
                prompt + "\n\nMatch exactly the art style, palette, linework and "
                "character designs of the attached reference pages.",
                "size": "1536x1024", "quality": "high"}
        r = requests.post("https://api.openai.com/v1/images/edits",
                          headers=headers, data=data, files=files, timeout=600)
    else:
        r = requests.post("https://api.openai.com/v1/images/generations",
                          headers={**headers, "Content-Type": "application/json"},
                          json={"model": "gpt-image-1", "prompt": prompt,
                                "size": "1536x1024", "quality": "high"},
                          timeout=600)
    r.raise_for_status()
    out.write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))


# ---------------------------------------------------------------- Gemini --
def gen_gemini(prompt: str, refs: list[Path], out: Path):
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    parts = [{"inline_data": {"mime_type": "image/png",
                              "data": base64.b64encode(p.read_bytes()).decode()}}
             for p in refs]
    parts.append({"text": ("Match exactly the art style, palette, linework and "
                           "character designs of the reference pages above.\n\n"
                           if refs else "") + prompt})
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": parts}]}, timeout=600)
    r.raise_for_status()
    for part in r.json()["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            out.write_bytes(base64.b64decode(part["inlineData"]["data"]))
            return
    raise RuntimeError("Gemini 回應中沒有圖片: " + json.dumps(r.json())[:500])


PROVIDERS = {"openai": gen_openai, "gemini": gen_gemini}


def pick_provider(arg: str | None) -> str:
    if arg:
        return arg
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    sys.exit("請設定 OPENAI_API_KEY 或 GEMINI_API_KEY")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--panels", help="只生成某幾格, 例: p1a,p2b")
    ap.add_argument("--provider", choices=list(PROVIDERS))
    ap.add_argument("--force", action="store_true", help="覆蓋已存在的圖")
    args = ap.parse_args()

    meta = json.loads((Path(args.episode_dir) / "panels.json").read_text(encoding="utf-8"))
    art_dir = ROOT / "art" / f"ep{meta['episode']}"
    art_dir.mkdir(parents=True, exist_ok=True)
    provider = pick_provider(args.provider)
    refs = load_refs()
    only = set(args.panels.split(",")) if args.panels else None
    print(f"provider={provider}  參考圖 {len(refs)} 張")

    todo = [p for page in meta["pages"] for p in page["panels"]
            if (only is None or p["id"] in only)]
    for i, panel in enumerate(todo, 1):
        out = art_dir / f"{panel['id']}.png"
        if out.exists() and not args.force:
            print(f"[{i}/{len(todo)}] {panel['id']} 已存在, 跳過")
            continue
        print(f"[{i}/{len(todo)}] 生成 {panel['id']} …")
        try:
            PROVIDERS[provider](expand(panel["art"], meta), refs, out)
            print("   ->", out)
        except Exception as exc:  # noqa: BLE001 — 單格失敗不中斷整批
            print(f"   !! {panel['id']} 失敗: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
