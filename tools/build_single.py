#!/usr/bin/env python3
"""把 web/ 打包成一個完全不依賴網路的單一 HTML。

為什麼需要：這款遊戲的賣點是「一個檔案打開就能玩」。接上外部美術之後
那個性質其實破了 —— 圖是分開的 44 個檔案，用 file:// 打開時
瀏覽器還會因為同源限制擋掉一部分讀取。

做法是把 web/art/ 底下每一張 PNG 轉成 data URI，塞進一個
`ART_DATA` 表，再讓遊戲裡那一行 `im.src = ART_DATA[id] || url` 去用它。
遊戲那邊只多一個變數，網站版完全不受影響。

**鍵要跟 adoptArt 呼叫時用的一模一樣**，因為那一行是用 id 去查表：
  art/mon/rat.png    → 'rat'
  art/weapon/club.png→ 'weapon#club'
  art/boss/b_oni.png → 'b_oni'
  art/item/herb00.png→ 'herb#0'
弄錯的話不會報錯，只是那張圖悄悄退回程式畫的版本 —— 所以最後會驗一次。

    python3 tools/build_single.py [輸出路徑]
"""

import base64
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / 'web'
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'dist' / 'index.html'


def key_for(rel):
    """檔案路徑 → adoptArt 用的鍵。對不上就回 None，讓呼叫端報錯。"""
    parts = rel.replace('\\', '/').split('/')
    # art/tile/<地貌>/<部位>.png —— 外部手繪地磚。
    # 跟 anim 一樣是三層，鍵的形狀也刻意一樣（'類別:群組#名字'）。
    if len(parts) == 3 and parts[0] == 'tile' and parts[2].endswith('.png'):
        return 'tile:%s#%s' % (parts[1], parts[2][:-4])
    if len(parts) == 3 and parts[0] == 'anim':
        cat, filename = parts[1], parts[2]
        if cat in ('hero', 'hat', 'weapon', 'shield', 'mon', 'boss') and filename.endswith('.png'):
            return 'anim:%s#%s' % (cat, filename[:-4])
        return None
    if len(parts) != 2:
        return None
    cat, name = parts[0], parts[1][:-4]
    if cat in ('mon', 'boss'):
        return name
    # 主角是分層合成的：身體一層、帽子一層。鍵用「類別#名字」，
    # 跟 art/item 的「類別#編號」同一個形狀 —— adoptArt 那邊也是這樣查的。
    if cat in ('hero', 'hat', 'weapon', 'shield', 'village', 'map'):
        return '%s#%s' % (cat, name)
    if cat == 'item':
        m = re.fullmatch(r'([a-z]+)(\d+)', name)
        return '%s#%d' % (m.group(1), int(m.group(2))) if m else None
    return None


MIME = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.webp': 'image/webp'}


def data_uri(raw, suffix):
    return 'data:%s;base64,%s' % (MIME[suffix],
                                  base64.b64encode(raw).decode('ascii'))


# 哪些是「畫」、哪些是「精靈」。這條界線決定能不能用有損壓縮：
# 村莊與旅程圖是五萬到九萬色的手繪插畫，q82 的 WebP 看不出差別；
# 怪物、主角、地磚是像素圖，一點振鈴就毀了輪廓，所以一律無損
# （WebP 無損是**逐像素完全相同**，不是「幾乎一樣」）。
ILLUSTRATION = ('village', 'map', 'promo')


def to_webp(raw, lossy):
    """轉成 WebP。只在打包時做 —— web/art/ 底下的原圖一個位元組都不會動，
    網站版永遠是原檔。轉不動（沒有 Pillow）就回 None，讓呼叫端退回原圖。"""
    try:
        from PIL import Image
    except ImportError:
        return None
    import io
    im = Image.open(io.BytesIO(raw))
    im = im.convert('RGBA') if 'A' in im.getbands() else im.convert('RGB')
    buf = io.BytesIO()
    if lossy:
        im.save(buf, 'WEBP', quality=82, method=6)
    else:
        im.save(buf, 'WEBP', lossless=True, method=6)
    out = buf.getvalue()
    return out if len(out) < len(raw) else None


def pack(raw, suffix, top, full):
    """一張圖 → (bytes, 副檔名)。full=True 就原封不動。"""
    if full:
        return raw, suffix
    out = to_webp(raw, lossy=(top in ILLUSTRATION))
    return (out, '.webp') if out else (raw, suffix)


def embed_promo(html, full):
    """封面與開場炭筆畫：CSS 的 url() 與 JS 的預載都要換成 data URI。

    這幾張跟精靈圖走的是完全不同的路 —— 它們是 CSS background-image，
    不經過 adoptArt，所以 ART_DATA 那一套完全碰不到它們。漏掉的話
    單檔版離線打開會是「封面全黑、開場動畫四張全黑」，而遊戲照樣跑得動：
    又是一次沒有錯誤訊息的失效。

    只收**畫面上真的引用到的**那幾張。純宣傳海報（key-art v2～v5，
    合計 12 MB）遊戲從來不讀，塞進來只是讓每個玩家多下載 12 MB。
    """
    promo = WEB / 'art' / 'promo'
    if not promo.is_dir():
        sys.exit('找不到 web/art/promo/ —— 封面與開場動畫的圖不在了')

    used, total_raw, total_out = [], 0, 0
    for f in sorted(promo.iterdir()):
        ref = 'url("art/promo/%s")' % f.name
        if ref not in html:
            continue                      # 純宣傳海報：畫面上沒有人引用
        raw = f.read_bytes()
        total_raw += len(raw)
        raw, suffix = pack(raw, f.suffix.lower(), 'promo', full)
        total_out += len(raw)
        html = html.replace(ref, 'url("%s")' % data_uri(raw, suffix))
        used.append(f.name)

    if not used:
        sys.exit('index.html 沒有引用任何 promo 圖 —— 是不是改了檔名？')

    # 開場那四張一定要在。少一張的話畫面是「第 N 幕全黑」，不會有錯誤訊息。
    # 它們**只**從 CSS 進來一次：JS 那邊的預載清單在單檔版是空的，
    # 因為 data URI 已經在文件裡，沒有什麼可以先抓 ——
    # 再列一次就會是同樣四張各內嵌兩份，單檔平白多 1.3 MB。
    for i in (1, 2, 3, 4):
        f = promo / ('prologue-charcoal-%d-v1.jpg' % i)
        if f.name not in used:
            sys.exit('開場第 %d 張炭筆畫沒有進去（%s）' % (i, f.name))

    return html, used, total_raw, total_out


def verify_sprites(art):
    """精靈圖必須**逐像素**跟原檔一樣。

    「無損」是壓縮參數的承諾，不是事實 —— 參數打錯一個字（lossless 漏掉、
    走到有損那一支）不會報錯，只會讓每一隻怪的輪廓多一圈振鈴，
    而那要放到畫面上才看得出來，通常是玩家先看到。所以這裡真的解回來比對。

    插畫（村莊、旅程圖、封面、開場）是有損的，本來就會不一樣，不在這裡驗；
    它們的尺寸沒有被改，那是上面轉檔那一支保證的。

    量出來的一件事，順手記著：Pillow 12 對**帶 alpha** 的圖，就算給了
    quality 也還是走無損 —— 精靈圖全部有 alpha，所以連 quality=10 都
    逐像素相同。這條驗證因此在今天看起來像多餘的，但它防的是明天：
    哪天有一張精靈圖沒有 alpha（或先被拍平成 RGB），有損就真的生效了，
    而那只會表現成「怪物的輪廓毛毛的」，沒有人會收到錯誤訊息。
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return                       # 沒有 Pillow 就沒轉檔，原樣進去，不必驗
    import io
    root = WEB / 'art'
    same = bad = 0
    for path in sorted(root.rglob('*.png')):
        rel = str(path.relative_to(root))
        if rel.replace('\\', '/').split('/')[0] in ILLUSTRATION:
            continue
        k = key_for(rel)
        if k is None or k not in art:
            continue
        raw = base64.b64decode(art[k].split(',', 1)[1])
        a = Image.open(io.BytesIO(raw)).convert('RGBA')
        b = Image.open(path).convert('RGBA')
        if a.size != b.size or ImageChops.difference(a, b).getbbox() is not None:
            bad += 1
            print('  ✗ 壓縮之後像素變了：%s' % rel, file=sys.stderr)
        else:
            same += 1
    if bad:
        sys.exit('有 %d 張精靈圖被壓壞了 —— 單檔版的美術會跟網站版不一樣' % bad)
    print('  精靈圖 %d 張逐像素比對過，與原檔完全相同' % same)


def main():
    # 預設就壓縮。精靈圖走**無損** WebP（逐像素相同），插畫走 q82 ——
    # 不壓的話單檔版是 10.1 MB，那個大小已經違背了「一個檔案打開就能玩」。
    # --full 保留原檔位元組，給需要完全原始畫質的場合。
    full = '--full' in sys.argv[1:]
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    global OUT
    if args:
        OUT = pathlib.Path(args[0])
    html = (WEB / 'index.html').read_text(encoding='utf-8')

    art = {}
    unknown = []
    raw_total = out_total = 0
    root = WEB / 'art'
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            if not f.endswith('.png'):
                continue
            path = pathlib.Path(dirpath) / f
            rel = str(path.relative_to(root))
            # promo/ 底下同時放著兩種完全不同的東西：遊戲跑起來真的會用到的
            # 封面與開場炭筆畫（下面 embed_promo() 處理，一定要進來），
            # 以及純宣傳海報（12 MB，遊戲從頭到尾不會讀它）。
            # 這裡一律跳過，交給 embed_promo() 去挑「畫面上真的引用到的」。
            if rel.replace('\\', '/').startswith('promo/'):
                continue
            k = key_for(rel)
            if k is None:
                unknown.append(rel)
                continue
            raw = path.read_bytes()
            raw_total += len(raw)
            raw, suffix = pack(raw, '.png', rel.replace('\\', '/').split('/')[0], full)
            out_total += len(raw)
            art[k] = data_uri(raw, suffix)

    if unknown:
        sys.exit('這些檔案的路徑對不上任何鍵，先確認命名：\n  ' + '\n  '.join(unknown))
    if not art:
        sys.exit('web/art/ 底下沒有 PNG —— 打包出來會跟網站版一樣，沒有意義')

    # 封面與開場炭筆畫（CSS 的 url()）＋ 開場預載用的鍵
    html, promo_used, promo_raw, promo_out = embed_promo(html, full)

    # 塞在遊戲腳本的最前面。用 var 不用 const：它要覆蓋後面那個 `let ART_DATA`
    # 是不可能的（同一個作用域會衝突），所以改成在 let 之後才指派。
    payload = 'ART_DATA = ' + '{' + ','.join(
        '%s:"%s"' % (('"%s"' % k), v) for k, v in sorted(art.items())) + '};'

    anchor = 'let ART_DATA = null;'
    if anchor not in html:
        sys.exit('index.html 裡找不到 %r —— 那個鉤子被改掉了' % anchor)
    html = html.replace(anchor, anchor + '\n' + payload, 1)

    # 字型也要進來。它們是 CSS 裡的 url()，跟圖走的是完全不同的路 ——
    # 忘了處理的話，單檔版會去打網路要一個不存在的相對路徑，
    # 然後**安靜地**退回系統字型：檔案打得開、遊戲跑得動、只是字變回原樣。
    # 那正是這款遊戲最常見的失效方式，所以下面驗到底。
    fonts = 0
    fdir = WEB / 'font'
    for f in sorted(fdir.glob('*.woff2')) if fdir.is_dir() else []:
        ref = 'url("font/%s")' % f.name
        if ref not in html:
            sys.exit('%s 沒有被 index.html 引用 —— 是不是改了檔名？' % f.name)
        b64 = base64.b64encode(f.read_bytes()).decode('ascii')
        html = html.replace(ref, 'url("data:font/woff2;base64,%s")' % b64)
        fonts += 1
    if not fonts:
        sys.exit('web/font/ 底下沒有 woff2 —— 先跑 tools/build_font.py')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')

    # 驗一次：每一張圖都真的進去了，而且沒有殘留的相對路徑會去打網路。
    miss = [k for k in art if '"%s":"data:image/' % k not in html]
    if miss:
        sys.exit('有 %d 個鍵沒寫進去：%s' % (len(miss), miss[:5]))
    if 'url("font/' in html:
        sys.exit('還有字型是用相對路徑引用的 —— 單檔版離線打開會沒有字型')
    # 封面與開場那幾張是 CSS 背景，載不到的時候畫面只會是一片黑，
    # 不會有任何錯誤 —— 所以這裡要驗到底，一個相對路徑都不留。
    verify_sprites(art)
    if 'url("art/' in html:
        left = re.findall(r'url\("(art/[^"]+)"\)', html)
        sys.exit('還有圖是用相對路徑引用的，單檔版離線打開會是黑的：\n  '
                 + '\n  '.join(sorted(set(left))))

    size = OUT.stat().st_size
    print('寫出 %s' % OUT)
    print('  內嵌 %d 張圖、%d 套字型，總計 %.1f MB' % (len(art), fonts, size / 1048576))
    print('  其中封面與開場動畫 %d 張' % len(promo_used))
    rt, ot = raw_total + promo_raw, out_total + promo_out
    if full:
        print('  --full：原檔位元組，未轉檔（%.1f MB 美術）' % (rt / 1048576))
    else:
        print('  美術 %.1f MB → %.1f MB（精靈無損、插畫 q82；原圖未更動）'
              % (rt / 1048576, ot / 1048576))


main()
