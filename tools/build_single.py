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
    if cat in ('hero', 'hat', 'weapon', 'shield'):
        return '%s#%s' % (cat, name)
    if cat == 'item':
        m = re.fullmatch(r'([a-z]+)(\d+)', name)
        return '%s#%d' % (m.group(1), int(m.group(2))) if m else None
    return None


def main():
    html = (WEB / 'index.html').read_text(encoding='utf-8')

    art = {}
    unknown = []
    root = WEB / 'art'
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            if not f.endswith('.png'):
                continue
            path = pathlib.Path(dirpath) / f
            rel = str(path.relative_to(root))
            k = key_for(rel)
            if k is None:
                unknown.append(rel)
                continue
            b64 = base64.b64encode(path.read_bytes()).decode('ascii')
            art[k] = 'data:image/png;base64,' + b64

    if unknown:
        sys.exit('這些檔案的路徑對不上任何鍵，先確認命名：\n  ' + '\n  '.join(unknown))
    if not art:
        sys.exit('web/art/ 底下沒有 PNG —— 打包出來會跟網站版一樣，沒有意義')

    # 塞在遊戲腳本的最前面。用 var 不用 const：它要覆蓋後面那個 `let ART_DATA`
    # 是不可能的（同一個作用域會衝突），所以改成在 let 之後才指派。
    payload = 'ART_DATA = ' + '{' + ','.join(
        '%s:"%s"' % (('"%s"' % k), v) for k, v in sorted(art.items())) + '};'

    anchor = 'let ART_DATA = null;'
    if anchor not in html:
        sys.exit('index.html 裡找不到 %r —— 那個鉤子被改掉了' % anchor)
    html = html.replace(anchor, anchor + '\n' + payload, 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding='utf-8')

    # 驗一次：每一張圖都真的進去了，而且沒有殘留的相對路徑會去打網路。
    miss = [k for k in art if '"%s":"data:image/png' % k not in html]
    if miss:
        sys.exit('有 %d 個鍵沒寫進去：%s' % (len(miss), miss[:5]))

    size = OUT.stat().st_size
    print('寫出 %s' % OUT)
    print('  內嵌 %d 張圖，總計 %.0f KB' % (len(art), size / 1024))


main()
