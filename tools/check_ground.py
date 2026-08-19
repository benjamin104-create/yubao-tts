#!/usr/bin/env python3
"""怪物有沒有真的站在地上。

使用者回報：「我不希望怪獸是懸浮在空中的感覺，目前影子看起來是懸浮在空中，
除非真的本來設定就是會飛的怪獸」。原因是轉檔工具把主體在方框裡置中，
趴著的洞穴鼠因此浮在自己的影子上方四個邏輯單位。

這種 bug 不會報錯：檔案寫得出來、尺寸對、色盤合規、遊戲照跑，
只是看起來怪。而且它只發生在矮胖的角色身上（高瘦的本來就填滿方框），
所以隨手看兩張圖還會覺得沒問題。

量法刻意不去重算遊戲自己的公式（那會變成拿答案對答案）：
同一個畫面拍兩張，一張有怪、一張把怪拿掉，相減。
變亮的像素是身體，變暗的像素是影子 —— 然後只問一句：
**身體的最下緣與影子的最上緣之間，隔了多遠。**
站在地上的要貼著（<= 1 邏輯單位），會飛的要明顯離開（>= 2）。

    python3 tools/check_ground.py
"""

import base64
import functools
import http.server
import io
import os
import pathlib
import sys
import threading

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 這一支必須走 http，不能用 file://。
# 讀畫布像素（toDataURL / getImageData）在 file:// 底下會因為載進來的外部
# PNG 污染畫布而被擋掉 —— 遊戲本身照常顯示，只有「讀回來」不行。
# 其他幾支檢查用 file:// 是因為它們只看 DOM，不讀畫布。
def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler,
                          directory=str(ROOT / 'web'))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, 'http://127.0.0.1:%d/index.html' % srv.server_address[1]

SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}
if not LAUNCH and os.path.exists('/opt/pw-browsers/chromium'):
    LAUNCH = {'executable_path': '/opt/pw-browsers/chromium'}

# 名單從程式裡讀，不手動維護。
# 手寫清單一定會落後於實際換進去的圖 —— 而「沒被檢查到的那幾隻」
# 正好就是最可能出問題的那幾隻（新換的）。
import re as _re

_src = open(ROOT / 'web' / 'index.html', encoding='utf-8').read()
_i = _src.index('const ART_MON = [')
_have = _re.findall(r"'([a-z_]+)'", _src[_i:_src.index('];', _i)])
_j = _src.index('const MONS = [')
_fly = set(_re.findall(r"\{id:'([a-z_]+)',[^\n]*fly:1", _src[_j:_src.index('\n];', _j)]))

GROUND = [m for m in _have if m not in _fly]
FLYING = [m for m in _have if m in _fly]

# 頭目也要驗。牠們用 48px 的圖、在遊戲裡放大 1.6 倍畫 ——
# 兩個跟雜魚都不一樣的數字，正是「以為沒問題」最容易出事的地方。
_b = _src.index('const ART_BOSS = [')
BOSSES = _re.findall(r"'(b_[a-z0-9_]+)'", _src[_b:_src.index('];', _b)])

PLACE = """(mid)=>{
  const p = G.p;
  G.mons.length = 0;
  const d = MONS.find(m => m.id === mid) || BOSS.find(m => m.id === mid);
  if(!d) return null;
  let sp = null;
  for(let r=2; r<=9 && !sp; r++)
    for(let dy=-r; dy<=r && !sp; dy++)
      for(let dx=-r; dx<=r && !sp; dx++)
        if(Math.max(Math.abs(dx), Math.abs(dy)) === r){
          const x = p.x+dx, y = p.y+dy;
          // 上下都要是空的，相減出來的區域才不會被牆的陰影干擾
          if(walkable(x,y) && walkable(x,y-1) && walkable(x,y+1)) sp = [x,y];
        }
  if(!sp) return null;
  const mo = spawnMon(d, sp[0], sp[1]);
  if(mo && G.mons.indexOf(mo) < 0) G.mons.push(mo);
  mo.st = {};                       // 睡著的飛行怪會落地，這裡要牠醒著
  mo.lunge = null;
  for(let y=sp[1]-7; y<=sp[1]+7; y++)
    for(let x=sp[0]-9; x<=sp[0]+9; x++) G.seen[key(x,y)] = 2;
  return {x:sp[0], y:sp[1], fly:!!d.fly};
}"""


def shot(pg):
    data = pg.evaluate("()=>cv.toDataURL()")
    return Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGB')


def main():
    fails = []
    srv, HTML = serve()
    with sync_playwright() as pw:
        b = pw.chromium.launch(**LAUNCH)
        pg = b.new_page(viewport={'width': 1280, 'height': 900})
        pg.goto(HTML)
        pg.wait_for_timeout(900)
        pg.click('#start')
        pg.wait_for_timeout(1400)
        RS = pg.evaluate("()=>RS")
        T = pg.evaluate("()=>T")

        for mid in GROUND + FLYING + BOSSES:
            spot = pg.evaluate(PLACE, mid)
            if spot is None:
                print('  ? %-9s 找不到空地，跳過' % mid)
                continue
            # 停掉待機起伏，不然兩張圖的相位不同，相減會多出一圈殘影
            pg.evaluate("()=>{ clock = 0; }")
            pg.wait_for_timeout(260)
            with_m = shot(pg)
            pg.evaluate("()=>{ G.mons.length = 0; clock = 0; }")
            pg.wait_for_timeout(260)
            without = shot(pg)

            info = pg.evaluate("()=>({ox:lastOx, oy:lastOy})")
            sx = int((info['ox'] + spot['x'] * T) * RS)
            sy = int((info['oy'] + spot['y'] * T) * RS)
            # 往上兩格、往下一格，飛起來的本體與地上的影子都要框得進來
            x0, x1 = sx - 2 * RS, sx + (T + 2) * RS
            y0, y1 = sy - 2 * T * RS, sy + (T + 4) * RS

            """分類每一列，而不是分類每一個像素。

               第一版是「變亮的算身體、變暗的算影子」，量出來全是負的 ——
               因為精靈自己的深色外框也會讓那一格變暗，於是「影子的上緣」
               永遠落在身體裡面。判準要能分開的是「這一列屬於誰」：
                 有任何一點變亮  → 這一列是身體（外框跟亮面混在一起）
                 只有變暗、沒變亮 → 這一列是落在地板上的影子
               身體與影子因此互斥，量出來的距離才是真的距離。 """
            body_rows, dark_rows = [], []
            for y in range(max(0, y0), min(with_m.height, y1)):
                lit = dark = 0
                for x in range(max(0, x0), min(with_m.width, x1)):
                    dv = sum(with_m.getpixel((x, y))) - sum(without.getpixel((x, y)))
                    if dv > 45: lit += 1
                    elif dv < -14: dark += 1
                if lit: body_rows.append(y)
                elif dark >= 3: dark_rows.append((y, dark))  # 三欄以上才算一道，不是雜點

            # 影子必須是**連續的一整段**，不能是孤零零一兩列。
            #   精靈最下面那一列常常整列都是深色外框，沒有任何一點夠亮，
            #   於是被歸成「影子」—— 位置剛好貼在身體下緣，量出來永遠是 0.5，
            #   連飛在半空的都一樣。實測投石妖精：身體到 9.5，
            #   本體外框留下 10.0/10.5 兩列，真正的影子在 14.0 之後。
            #   影子有 3 個邏輯單位厚（6 個畫布列），所以要求連續 4 列，
            #   既濾得掉外框，也還留著一半的餘裕。 
            # 而且要夠寬。針尾蜂與岩鷹的腳與尾羽是暗色的，
            # 亮不到 lit 的門檻，於是整排被歸成「影子」、剛好貼在身體下方，
            # 量出來又是 0.5 —— 但畫面上牠們明明離地。
            # 真正的影子橫跨幾乎整格（實測暗了 18~24 欄），
            # 垂下來的腳只有 1~16 欄而且參差不齊。寬度用相對值比，
            # 不是寫死的欄數：畫面縮放與怪物大小都會變，比例才穩。
            widest = max([d for _, d in dark_rows] or [0])
            wide_enough = {y for y, d in dark_rows if d >= widest * 0.6}
            shad_rows, run = [], []
            for y in [y for y, _ in dark_rows] + [None]:
                if y is not None and y not in wide_enough:
                    if len(run) >= 4: shad_rows.extend(run)
                    run = []
                    continue
                if run and y is not None and y == run[-1] + 1:
                    run.append(y); continue
                if len(run) >= 4: shad_rows.extend(run)
                run = [] if y is None else [y]

            body_lo = body_rows[-1] if body_rows else None
            # 影子要找身體下方的第一道 —— 上方的變暗是精靈擋住的光，不是影子
            below = [y for y in shad_rows if body_lo is not None and y > body_lo]
            shad_hi = below[0] if below else None
            if body_lo is None:
                print('  ✗ %-9s 相減後看不到身體（沒畫出來？）' % mid)
                fails.append(mid)
                continue
            if shad_hi is None:
                # 站在地上的東西，影子被自己的身體完全擋住是**正常的** ——
                #   史萊姆與四足獸貼著地面，牠們的下緣就是接觸面，
                #   影子本來就露不出來。那正是「沒有懸空」的證據。
                #   會飛的就不一樣：影子必須在身體下方看得到，
                #   看不到的話讀起來就是「這張圖位置畫錯了」。 
                if spot['fly']:
                    print('  ✗ %-9s 會飛卻看不到影子 —— 沒有影子就讀不出高度' % mid)
                    fails.append(mid)
                else:
                    print('  ✓ %-9s 影子被身體完全遮住（貼著地面）' % mid)
                continue

            gap = (shad_hi - body_lo) / float(RS)      # 換算成邏輯單位
            if spot['fly']:
                okk = gap >= 2
                want = '會飛，要離地 >= 2'
            else:
                okk = gap <= 1
                want = '站著，要貼地 <= 1'
            print('  %s %-9s 身體下緣到影子上緣 %.1f 邏輯單位（%s）'
                  % ('✓' if okk else '✗', mid, gap, want))
            if not okk:
                fails.append(mid)

        b.close()
    srv.shutdown()

    print('\n%d 隻，%d 隻不合格' % (len(GROUND) + len(FLYING) + len(BOSSES), len(fails)))
    sys.exit(1 if fails else 0)


main()
