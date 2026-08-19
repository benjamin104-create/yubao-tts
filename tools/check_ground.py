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
        # 這支檢查靠兩個開關：關掉頭目的背光（它把整片地板打亮，
        # 每一列都會算成「身體」，影子永遠找不到），以及開關影子本身
        # （拍三張相減，見下面）。
        # 兩個都要確認真的動得了 —— 哪天被改成 const 或改名，
        # 這裡要立刻講清楚，不能默默地又量回一片什麼都沒驗到的綠燈。
        for knob in ('AURA', 'SHADOW'):
            r = pg.evaluate("""(k)=>{ try{
                    const was = eval(k); eval(k + ' = 0');
                    const now = eval(k); eval(k + ' = ' + was);
                    return now === 0 ? 'ok' : ('改不動，還是 ' + now);
                  }catch(e){ return '例外：' + e.message; } }""", knob)
            if r != 'ok':
                sys.exit('%s 這個開關失效了（%s）—— 量出來的結果不能信' % (knob, r))
        pg.evaluate("()=>{ AURA = 0; }")

        for mid in GROUND + FLYING + BOSSES:
            spot = pg.evaluate(PLACE, mid)
            if spot is None:
                print('  ? %-9s 找不到空地，跳過' % mid)
                continue
            """拍三張，相減 —— 不再猜哪些像素是影子。

               沒有怪 → 有怪但關掉影子 → 有怪也有影子。
               第二張減第一張＝身體，第三張減第二張＝影子，兩者都是精確的，
               沒有任何門檻可以調錯。

               為什麼放棄用亮度差判斷：試了三個版本，被騙了三次。
                 v1「變亮是身體、變暗是影子」→ 精靈的深色外框也讓地板變暗。
                 v2 改成整列分類 + 影子要夠寬夠連續 → 針尾蜂垂下來的腳過關了，
                    但全藏（一身黑忍裝、蹲成大字）的靴子照樣夠寬夠連續，
                    量出「站著的人離地 4.0」，而畫面上他明明踩在影子上。
                 v3 改成驗「影子＝地板 x (1-alpha)」的乘法關係 —— 想法對，
                    但火把的暖光是**畫在實體之後**再疊上去的，
                    三個通道的比例因此各不相同（實測 0.82 / 0.69 / 0.57）。
               每一版都更接近，但每一版都還是在猜。關掉再拍就沒得猜了。 """
            pg.evaluate("()=>{ clock = 0; SHADOW = 0; }")
            pg.wait_for_timeout(240)
            no_shadow = shot(pg)
            pg.evaluate("()=>{ clock = 0; SHADOW = 1; }")
            pg.wait_for_timeout(240)
            with_m = shot(pg)
            pg.evaluate("()=>{ G.mons.length = 0; clock = 0; }")
            pg.wait_for_timeout(240)
            without = shot(pg)

            info = pg.evaluate("()=>({ox:lastOx, oy:lastOy})")
            sx = int((info['ox'] + spot['x'] * T) * RS)
            sy = int((info['oy'] + spot['y'] * T) * RS)
            # 往上兩格、往下一格，飛起來的本體與地上的影子都要框得進來
            x0, x1 = sx - 2 * RS, sx + (T + 2) * RS
            y0, y1 = sy - 2 * T * RS, sy + (T + 4) * RS

            # 不能用「完全相等」比：火把的閃爍是照 performance.now() 算的，
            # 三張截圖之間一定不一樣。但那個雜訊很小 ——
            # 實測整片區域裡，關/開影子之間的差要嘛是 1（閃爍），
            # 要嘛是 16 以上（影子），中間**一個像素都沒有**。
            # 8 就落在那個空隙的正中間：對雜訊有 8 倍餘裕，對訊號有 2 倍。
            # 這是雜訊底線，不是拿來分辨「身體」與「影子」的門檻 ——
            # 那件事已經由「拍三張」處理掉了。
            NOISE = 8
            def moved(p, q):
                return max(abs(p[i] - q[i]) for i in range(3)) >= NOISE

            body_rows, shad_rows = [], []
            for y in range(max(0, y0), min(with_m.height, y1)):
                body = shad = 0
                for x in range(max(0, x0), min(with_m.width, x1)):
                    if moved(no_shadow.getpixel((x, y)), without.getpixel((x, y))):
                        body += 1
                    elif moved(with_m.getpixel((x, y)), no_shadow.getpixel((x, y))):
                        shad += 1
                if body >= 3: body_rows.append(y)
                if shad >= 3: shad_rows.append(y)

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
