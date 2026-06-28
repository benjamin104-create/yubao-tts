#!/usr/bin/env python3
"""
generate_batch.py — 一次生成本次的 5 張頁面，每張 2 版，並產生 outputs/index.html。

用法：
    python scripts/generate_batch.py            # 跑全部 5 張
    python scripts/generate_batch.py page01_cover page05_fourteen_stars  # 只跑指定頁

跑完會在 outputs/ 生成 index.html，可在瀏覽器一次瀏覽、左右比對 v1/v2。
"""
import sys
import pathlib

import generate_image as gi

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"

# 本次先做的 5 張（順序＝展示順序）
PAGES = [
    ("page01_cover", "第一季漫畫封面"),
    ("page02_azhe_pain", "第1話第1頁：阿哲卡住"),
    ("page03_ziwei_door", "第1話第2頁：紫微堂開門"),
    ("page04_life_map", "第1話第3頁：命盤不是判決書，是人生地圖"),
    ("page05_fourteen_stars", "第1話第4頁：十四主星群像"),
]


def build_index(pages):
    """掃描 outputs/ 內已存在的 PNG，產生 index.html。"""
    title_map = dict(pages)
    cards = []
    for stem, _ in pages:
        title = title_map.get(stem, stem)
        versions = sorted(OUTPUTS.glob(f"{stem}_v*.png"))
        finals = sorted(OUTPUTS.glob(f"{stem}_*_final.png"))
        imgs = versions + finals
        if not imgs:
            thumbs = '<div class="empty">（尚未生成）</div>'
        else:
            thumbs = "".join(
                f'<figure><img src="{p.name}" loading="lazy">'
                f'<figcaption>{p.name}</figcaption></figure>'
                for p in imgs
            )
        cards.append(
            f'<section class="card"><h2>{title}</h2>'
            f'<div class="code">{stem}</div>'
            f'<div class="row">{thumbs}</div></section>'
        )

    html = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>潔米爸的占驗派紫微斗數 — 圖片預覽</title>
<style>
  :root {{ --bg:#0b1026; --gold:#d8b061; --ink:#10142b; --cream:#f3e7c9; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--cream);
         font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif; }}
  header {{ padding:28px 20px; text-align:center;
            background:linear-gradient(180deg,#11183b,#0b1026);
            border-bottom:2px solid var(--gold); }}
  header h1 {{ margin:0; color:var(--gold); letter-spacing:3px; font-size:24px; }}
  header p {{ margin:6px 0 0; opacity:.7; font-size:13px; }}
  .wrap {{ max-width:1200px; margin:0 auto; padding:20px; }}
  .card {{ background:var(--ink); border:1px solid #2a325c; border-radius:14px;
           padding:18px; margin:18px 0; }}
  .card h2 {{ margin:0 0 4px; font-size:18px; }}
  .card .code {{ font-family:monospace; color:var(--gold); opacity:.8;
                 font-size:12px; margin-bottom:12px; }}
  .row {{ display:flex; gap:14px; flex-wrap:wrap; }}
  figure {{ margin:0; width:280px; }}
  figure img {{ width:100%; border-radius:10px; border:1px solid #39406b;
                display:block; background:#000; }}
  figcaption {{ font-size:11px; opacity:.6; margin-top:6px;
                font-family:monospace; word-break:break-all; }}
  .empty {{ opacity:.4; font-size:13px; padding:24px; }}
  footer {{ text-align:center; padding:24px; opacity:.5; font-size:12px; }}
</style></head>
<body>
<header>
  <h1>潔米爸的占驗派紫微斗數</h1>
  <p>圖片生成預覽 ‧ 每張 2 版，挑選後再進後製上字（add_text_layout.py）</p>
</header>
<div class="wrap">
{''.join(cards)}
</div>
<footer>gpt-image-2 ‧ 文字一律後製 ‧ outputs/index.html</footer>
</body></html>
"""
    out = OUTPUTS / "index.html"
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"\n[index] 已生成 {out}")
    return out


def main():
    args = sys.argv[1:]
    if args:
        wanted = set(args)
        pages = [p for p in PAGES if p[0] in wanted]
        if not pages:
            print("找不到指定頁面，可用：", [p[0] for p in PAGES])
            sys.exit(1)
    else:
        pages = PAGES

    for stem, title in pages:
        print(f"\n=== {title} ({stem}) ===")
        try:
            gi.generate(stem)
        except SystemExit:
            raise
        except Exception as e:
            print(f"  ✗ 失敗：{e}")

    # 不論成功與否，都用「實際存在的檔案」重建 index
    build_index(PAGES)


if __name__ == "__main__":
    main()
