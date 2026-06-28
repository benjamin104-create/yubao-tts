#!/usr/bin/env python3
"""
generate_image.py — 用 OpenAI Image API (gpt-image-2) 生成單一頁面的漫畫圖。

用法：
    python scripts/generate_image.py page01_cover
    python scripts/generate_image.py page01_cover --n 2
    python scripts/generate_image.py page01_cover --size 1024x1536 --quality high

規則：
    - 每張圖預設輸出 IMAGE_N (預設 2) 個版本，方便挑選。
    - 一律輸出 PNG 到 outputs/<page>_vN.png。
    - 送進 API 的 prompt = style.md + characters.md + <page>.md，
      只擷取各檔 ===PROMPT START=== / ===PROMPT END=== 之間的英文（中文說明不送出）。
    - 不讓 AI 生成中文／任何文字（規則寫在 style.md）。

設定來自 .env（見 .env.example）。本檔不會在沒有金鑰時硬跑。
"""
import os
import sys
import base64
import argparse
import pathlib

from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
OUTPUTS = ROOT / "outputs"

load_dotenv(ROOT / ".env")

MODEL = os.getenv("IMAGE_MODEL", "gpt-image-2")
SIZE = os.getenv("IMAGE_SIZE", "1024x1536")
QUALITY = os.getenv("IMAGE_QUALITY", "high")
DEFAULT_N = int(os.getenv("IMAGE_N", "2"))

PROMPT_START = "===PROMPT START==="
PROMPT_END = "===PROMPT END==="


def extract_prompt(md_path: pathlib.Path) -> str:
    """擷取 md 檔中 ===PROMPT START=== / ===PROMPT END=== 之間的文字。
    若無標記，回傳整檔內容。"""
    text = md_path.read_text(encoding="utf-8")
    if PROMPT_START in text and PROMPT_END in text:
        chunk = text.split(PROMPT_START, 1)[1].split(PROMPT_END, 1)[0]
        return chunk.strip()
    return text.strip()


def build_prompt(page: str) -> str:
    """組合 style + characters + page 三段 prompt。"""
    page_file = page if page.endswith(".md") else f"{page}.md"
    parts = []
    for name in ("style.md", "characters.md", page_file):
        p = PROMPTS / name
        if not p.exists():
            raise FileNotFoundError(f"找不到 prompt 檔：{p}")
        parts.append(extract_prompt(p))
    return "\n\n".join(parts)


def generate(page: str, n: int = DEFAULT_N, size: str = SIZE,
             quality: str = QUALITY, model: str = MODEL,
             ref_images=None) -> list:
    """呼叫 API 生成 n 個版本，存成 PNG，回傳檔案路徑清單。"""
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "未偵測到 OPENAI_API_KEY。\n"
            "請先 `cp .env.example .env` 並在 .env 填入你的金鑰，再執行。"
        )

    client = OpenAI()
    prompt = build_prompt(page)
    stem = page[:-3] if page.endswith(".md") else page
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    print(f"[generate] model={model} size={size} quality={quality} n={n}")
    print(f"[generate] page={stem}  prompt_chars={len(prompt)}")

    # --- 純文字生成（預設路徑）---
    # 角色一致性需求出現時，可改走 images.edit 帶 ref_images（見 README「進階」）。
    if ref_images:
        # 預留骨架：用參考圖做 image-to-image / 風格延續
        files = [open(p, "rb") for p in ref_images]
        try:
            result = client.images.edit(
                model=model, image=files, prompt=prompt, size=size, n=n,
            )
        finally:
            for f in files:
                f.close()
    else:
        try:
            result = client.images.generate(
                model=model, prompt=prompt, size=size, quality=quality, n=n,
            )
        except Exception as e:
            msg = str(e).lower()
            # 若 gpt-image-2 對此帳號未開通／不存在，自動退回 gpt-image-1
            if model != "gpt-image-1" and (
                "model" in msg and ("not found" in msg or "does not exist"
                in msg or "unsupported" in msg or "invalid" in msg or "404" in msg)
            ):
                print(f"  ! 模型 {model} 無法使用，自動改用 gpt-image-1 重試…")
                result = client.images.generate(
                    model="gpt-image-1", prompt=prompt, size=size,
                    quality=quality, n=n,
                )
            else:
                raise

    saved = []
    for i, item in enumerate(result.data, 1):
        b64 = getattr(item, "b64_json", None)
        if not b64:
            # 某些模型回 URL；保險處理
            url = getattr(item, "url", None)
            if url:
                import urllib.request
                out = OUTPUTS / f"{stem}_v{i}.png"
                urllib.request.urlretrieve(url, out)
                saved.append(out)
                print(f"  ✓ {out.name} (from url)")
                continue
            raise RuntimeError("API 回應沒有 b64_json 也沒有 url。")
        out = OUTPUTS / f"{stem}_v{i}.png"
        out.write_bytes(base64.b64decode(b64))
        saved.append(out)
        print(f"  ✓ {out.name}")
    return saved


def main():
    ap = argparse.ArgumentParser(description="生成單頁漫畫圖 (gpt-image-2)")
    ap.add_argument("page", help="prompts/ 內的頁面名，如 page01_cover")
    ap.add_argument("--n", type=int, default=DEFAULT_N, help="版本數（預設 2）")
    ap.add_argument("--size", default=SIZE)
    ap.add_argument("--quality", default=QUALITY)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--ref", nargs="*", default=None,
                    help="（進階）參考圖路徑，啟用 image-to-image 風格延續")
    args = ap.parse_args()

    generate(args.page, n=args.n, size=args.size, quality=args.quality,
             model=args.model, ref_images=args.ref)


if __name__ == "__main__":
    main()
