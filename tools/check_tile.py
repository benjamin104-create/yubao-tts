#!/usr/bin/env python3
"""地形的解析度與色數。

使用者：「我要的是『特魯內克大冒險』的遊戲畫面等級」「如果是遊戲畫面
因為格數導致細緻度問題的話，你趕快幫我改善」。

量出來的問題不是格數，是**地形跟角色不在同一個解析度上**：

    角色  外部手繪圖，怪 32x32、頭目 48x48，中位 12~25 色 —— 1:1 畫上去
    地形  13 個地貌全部 16x16、地板最多 9 色，而且一張外部圖都沒有

而地形佔畫面九成五的面積。整個畫面裡面積最大的東西解析度只有角色的
一半，每個藝術像素在螢幕上是角色的四倍大 —— 那就是「很糙」的來源。

這一支把修好的狀態釘住。三件事，每一件都對應一個真的會回頭的退化：

  1. 原生尺寸 >= TP（32）。有人把某個地貌新的地磚照舊寫成 T=16 的畫布，
     遊戲照跑、色也對，只是那一章又回到半解析度 —— 沒有任何測試會叫。
  2. 2x2 同色率要夠低。**光看尺寸不夠**：把 16x16 放大兩倍存成 32x32
     也會通過第 1 條，而那沒有多出任何資訊。同色率就是在問
     「這 32x32 裡真的有 32x32 的資訊嗎」。
  3. 色數要落在手繪像素圖的範圍裡。太少＝沒有明暗層次；太多＝噪點
     （第一版加了 ±2 的顆粒，一張磚變成 176 色，那不是精緻，是髒）。

    python3 tools/check_tile.py
"""

import functools
import http.server
import json
import os
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 色數只留**上限**。上限 72：對照組是 4bpp 一組調色盤 16 色的年代，
# 我們有多組色帶疊在一張磚上，所以放寬，但不能放到「每個像素都差一點點」
# 那一邊去。
#
# 下限本來是 8，理由寫著「太少＝沒有明暗層次」。那個推論對，但**色數是
# 錯的代理**，而且是在只量得到程式畫的磚的年代訂的。手繪磚交進來之後
# 量出來：水晶／山道／荊棘的 floor0 都只有 5 色，卻各自有 5 個乾淨的
# 明度階、跨度 124~196 —— 那不是平，那正是那個年代的做法
# （一張地磚四到六色是常態）。
#
# 所以改成直接量它本來就想量的東西：明暗階數與明度跨度。
COL_MAX = 72
# 至少四階、跨度至少 40，才算「有光有影」。
STEP_MIN, SPAN_MIN = 4, 40
# 終章的虛空刻意是平的。那一章的 intro 就寫著「這裡沒有牆，也沒有天花板」——
# 一面有磚縫與風化的牆會把那句話講反。所以只有它的下限放寬，
# 而且**指名放寬**：全面調低下限的話，哪一天別的地貌變成一片死板，
# 這條檢查也不會叫了。
FLAT_OK = {'void': 2}
# 2x2 同色率上限。平坦的走道磚本來就沒什麼結構可以浮雕，所以不要求
# 每一張都低 —— 要求的是**整組的中位數**夠低，以及沒有整組都是平的。
UNI_MEDIAN_MAX = 0.80


def serve():
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Q, directory=str(ROOT / 'web'))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, 'http://127.0.0.1:%d/index.html' % srv.server_address[1]


SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}
if not LAUNCH and os.path.exists('/opt/pw-browsers/chromium'):
    LAUNCH = {'executable_path': '/opt/pw-browsers/chromium'}

# 量測全部在瀏覽器裡做：把畫布搬到 Python 再算一次，只是多一層可能出錯的
# 轉檔。這裡要的是「遊戲真的會畫出來的那一張」，那就在遊戲裡量。
MEASURE = """(theme)=>{
  const t = tilesFor(theme);
  const one = (c) => {
    const x = c.getContext('2d');
    const d = x.getImageData(0,0,c.width,c.height).data;
    const cols = new Set();
    for(let i=0;i<d.length;i+=4) if(d[i+3] > 8) cols.add((d[i]<<16)|(d[i+1]<<8)|d[i+2]);
    // 2x2 同色率：每個 2x2 方塊內部四個像素完全相同的比例
    let tot = 0, same = 0;
    const at = (px,py)=>{ const i=(py*c.width+px)*4;
      return (d[i]<<24)|(d[i+1]<<16)|(d[i+2]<<8)|d[i+3]; };
    for(let by=0; by+1<c.height; by+=2) for(let bx=0; bx+1<c.width; bx+=2){
      const a = at(bx,by);
      tot++;
      if(a===at(bx+1,by) && a===at(bx,by+1) && a===at(bx+1,by+1)) same++;
    }
    // 明度階數與跨度：這兩個才是「有沒有明暗層次」的直接量法。
    // 色數只是代理，而且對手繪磚是錯的代理 —— 見下面 COL_MIN 的註解。
    const ls = [...new Set([...cols].map(v =>
      Math.round(0.2126*((v>>16)&255) + 0.7152*((v>>8)&255) + 0.0722*(v&255))))]
      .sort((a,b)=>a-b);
    let steps = ls.length ? 1 : 0;
    for(let i=1;i<ls.length;i++) if(ls[i]-ls[i-1] >= 4) steps++;
    const span = ls.length ? ls[ls.length-1]-ls[0] : 0;
    return {w:c.width, h:c.height, cols:cols.size, uni: tot ? same/tot : 1,
            steps, span};
  };
  const out = {};
  t.floor.forEach((c,i)=> out['floor'+i] = one(c));
  t.corr.forEach((c,i)=> out['corr'+i] = one(c));
  out.wall = one(t.wall); out.wallface = one(t.wallFace);
  t.blocker.forEach((c,i)=> out['blocker'+i] = one(c));
  return out;
}"""


READY = """() => {
  if(typeof ART_TILE_AVAILABLE === 'undefined') return false;
  for(const th in ART_TILE_AVAILABLE){
    const slist = ART_TILE_AVAILABLE[th] || [];
    if(!slist.length) continue;
    const ts = tilesFor(th);
    if(slist.some(f => f.indexOf('floor') === 0)){
      const img = roomFloorFor(ts, macroFloorsFor(th), 4, 4);
      if(!(img && img._externalTile)) return false;
    }
    if(slist.some(f => f.indexOf('corr') === 0)){
      const c = corridorFloorFor(ts, 4, 4);
      if(!(c && c._externalTile)) return false;
    }
    if(slist.indexOf('wall') >= 0){
      const w = externalTileQuarter(ts.wall, 4, 4);
      if(!(w && w._externalTile)) return false;
    }
  }
  return true;
}"""


def wait_for_tiles(pg):
    """等到手繪地磚**真的**載完再開始量。

    這一段是踩出來的：檢查原本只等固定的 2.3 秒就問「有沒有用到手繪成品」，
    但地磚是非同步載入的（artImage 的 im.onload）。六十幾張圖沒載完的時候，
    那一題的答案是「沒有」—— 於是同一份程式碼、同一批圖，
    跑十次紅兩次。實測：crystal 的走道與牆面隨機報「沒有使用手繪成品」。

    CI 紅就不部署，所以不穩定的檢查等於「有時候推不上去，重跑一次又好了」，
    那比沒有檢查更糟 —— 大家會開始習慣性重跑，真的壞掉那次也照重跑。

    超時不當成錯：真的沒接上的話，後面逐一地貌的檢查會指名是哪一個、
    哪一個部位，那個訊息比這裡丟一個例外有用得多。
    """
    try:
        pg.wait_for_function(READY, timeout=20000)
    except Exception:
        print('（等手繪地磚載入逾時 —— 下面會指出是哪一個地貌沒接上）')


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
        wait_for_tiles(pg)

        TP = pg.evaluate('()=>TP')
        themes = pg.evaluate('()=>Object.keys(THEMES)')
        slots = pg.evaluate('()=>TILE_SLOTS')
        print('地磚應有的原生尺寸 TP = %d（一格在畫布上的像素數）' % TP)
        print('部位 %d 種：%s\n' % (len(slots), '、'.join(slots)))

        print('%-11s %-9s %-7s %s' % ('地貌', '原生尺寸', '色數', '2x2同色（中位）'))
        for th in themes:
            m = pg.evaluate(MEASURE, th)
            unis = sorted(v['uni'] for v in m.values())
            med = unis[len(unis) // 2]
            sizes = {v['w'] for v in m.values()}
            cols = [v['cols'] for v in m.values()]
            bad = []
            lo = FLAT_OK.get(th, STEP_MIN)
            for slot, v in m.items():
                if v['w'] < TP or v['h'] < TP:
                    bad.append('%s 只有 %dx%d' % (slot, v['w'], v['h']))
                if v['cols'] > COL_MAX:
                    bad.append('%s %d 色（上限 %d）—— 那不是精緻，是噪點'
                               % (slot, v['cols'], COL_MAX))
                if v['steps'] < lo or (lo > 2 and v['span'] < SPAN_MIN):
                    bad.append('%s 沒有明暗層次：%d 階、跨度 %d（要 %d 階、跨度 %d）'
                               % (slot, v['steps'], v['span'], lo, SPAN_MIN))
            if med > UNI_MEDIAN_MAX:
                bad.append('整組都是平的：2x2 同色中位 %.0f%%（上限 %.0f%%）'
                           % (med * 100, UNI_MEDIAN_MAX * 100))
            mark = '✓' if not bad else '✗'
            print('%s %-9s %-9s %2d~%-4d %.0f%%'
                  % (mark, th, '×'.join(str(s) for s in sorted(sizes)),
                     min(cols), max(cols), med * 100))
            for msg in bad:
                print('    ✗ ' + msg)
                fails.append('%s：%s' % (th, msg))

        # 外部手繪地磚：有幾張、尺寸對不對。沒有不是錯 —— 那是這條管線
        # 的正常狀態（跟怪物的圖一樣可以一張一張換）。
        tdir = ROOT / 'web' / 'art' / 'tile'
        have = sorted(p.relative_to(tdir).as_posix() for p in tdir.glob('*/*.png')) \
            if tdir.exists() else []
        print('\n外部手繪地磚 %d 張' % len(have))
        # 放進資料夾卻沒登記在 ART_TILE_AVAILABLE 的圖，開發版根本不會去載 ——
        # 檔案在、遊戲跑、畫面卻沒變，而且沒有任何錯誤訊息。
        # （單檔版走 ART_DATA 所以會生效，於是變成「網站上沒有、打包後才有」
        #   這種最難查的差異。）
        avail = pg.evaluate('()=>ART_TILE_AVAILABLE')
        for rel in have:
            th, fn = rel.split('/')[0], rel.split('/')[1][:-4]
            if fn not in (avail.get(th) or []):
                fails.append('%s：沒有登記在 ART_TILE_AVAILABLE' % rel)
                print("  ✗ %-28s 檔案在，但沒登記 —— 開發版不會載它。"
                      "把 '%s' 加進 ART_TILE_AVAILABLE['%s']" % (rel, fn, th))
        for th, slist in (avail or {}).items():
            for fn in slist:
                if '%s/%s.png' % (th, fn) not in have:
                    fails.append('ART_TILE_AVAILABLE 登記了不存在的 %s/%s.png' % (th, fn))
                    print('  ✗ 登記了 %s/%s.png，但檔案不在' % (th, fn))
        # 有 macro 的章節以前會「檔案載到了，遊戲卻仍畫舊的 2x2 大板」。
        # 直接問正式的房間地板選擇函式，確認外部成品真的走到畫面上；同時
        # 確認它不會再被程序材質疊第二遍。這不是檔案檢查能抓到的錯。
        for th, slist in (avail or {}).items():
            if not any(fn.startswith('floor') for fn in slist):
                continue
            routed = pg.evaluate("""th=>{
              const ts=tilesFor(th), img=roomFloorFor(ts,macroFloorsFor(th),4,4);
              const corr=corridorFloorFor(ts,4,4), wall=externalTileQuarter(ts.wall,4,4);
              return {external:!!(img&&img._externalTile), decorate:tileNeedsProceduralDetail(img),
                      corrExternal:!!(corr&&corr._externalTile), wallExternal:!!(wall&&wall._externalTile)};
            }""", th)
            if not routed.get('external'):
                fails.append('%s：房間仍被舊 macro 地板蓋住' % th)
                print('  ✗ %-28s 已載入，但房間仍選到舊的程序地板' % (th + '/floor*.png'))
            elif routed.get('decorate'):
                fails.append('%s：手繪房間仍被程序材質覆寫' % th)
                print('  ✗ %-28s 仍會疊上舊的程序材質' % (th + '/floor*.png'))
            elif not routed.get('corrExternal') or not routed.get('wallExternal'):
                fails.append('%s：走道或牆面未走外部成品路徑' % th)
                print('  ✗ %-28s 走道或牆面沒有使用手繪成品' % th)
            else:
                print('  ✓ %-28s 房間、走道、牆面實際使用手繪成品' % th)
        if have:
            from PIL import Image
            for rel in have:
                im = Image.open(tdir / rel)
                slot = rel.split('/')[1][:-4]
                ok = im.width == im.height and im.width >= TP and im.width % TP == 0
                if slot not in slots:
                    fails.append('%s：部位名稱不在 TILE_SLOTS 裡' % rel)
                    print('  ✗ %-28s 部位名稱不對（要是 %s 其中之一）' % (rel, '/'.join(slots)))
                elif not ok:
                    fails.append('%s：%dx%d' % (rel, im.width, im.height))
                    print('  ✗ %-28s %dx%d —— 要是正方形，而且是 %d 的整數倍'
                          % (rel, im.width, im.height, TP))
                else:
                    print('  ✓ %-28s %dx%d' % (rel, im.width, im.height))
        b.close()
    srv.shutdown()

    fails += check_prompt_palettes()

    print()
    if fails:
        print('%d 項不合格' % len(fails))
        return 1
    print('全部通過')
    return 0


def check_prompt_palettes():
    """提示詞裡寫的色盤，要跟 pixelize.py 真正量化過去的那一組**逐字相同**。

    這兩份東西天生會分家：`docs/art_prompts_tile.md` 是給影像模型看的，
    `TILE_PALETTES` 是轉檔時真正用的。哪天有人只改其中一邊，
    生圖時瞄準 A 組顏色、轉檔時被吸到 B 組，出來的磚就整批偏色 ——
    而且尺寸、色數、登記全部合格，沒有任何一條既有規則會叫。

    所以這裡直接把兩邊拿來對。
    """
    import re
    doc_path = ROOT / 'docs' / 'art_prompts_tile.md'
    tool_path = ROOT / 'tools' / 'pixelize.py'
    if not doc_path.exists() or not tool_path.exists():
        return []

    import importlib.util
    spec = importlib.util.spec_from_file_location('_pz', tool_path)
    pz = importlib.util.module_from_spec(spec)
    argv, sys.argv = sys.argv, ['_pz']
    try:
        spec.loader.exec_module(pz)
    except SystemExit:
        pass
    finally:
        sys.argv = argv

    doc = doc_path.read_text(encoding='utf-8')
    secs = re.findall(r'### \d+\. `([a-z]+)`(.*?)(?=\n### |\n## )', doc, re.S)
    print('\n提示詞的色盤與轉檔色盤（%d 個地貌）' % len(secs))

    bad = []
    for theme, body in secs:
        m = re.search(r'Palette anchored to:(.*?)—', body, re.S)
        code = pz.TILE_PALETTES.get(theme)
        if not m:
            bad.append('%s：提示詞裡找不到 Palette 那一行' % theme)
            print('  ✗ %-10s 找不到 Palette 那一行' % theme); continue
        if code is None:
            bad.append('%s：pixelize.py 沒有這個地貌' % theme)
            print('  ✗ %-10s pixelize.py 沒有這個地貌' % theme); continue
        want = [c.lower() for c in re.findall(r'#([0-9a-fA-F]{6})', m.group(1))]
        if want != [c.lower() for c in code]:
            bad.append('%s：提示詞與轉檔色盤不一致' % theme)
            print('  ✗ %-10s 色盤不一致\n      提示詞：%s\n      轉檔　：%s'
                  % (theme, ' '.join(want), ' '.join(code)))
        else:
            print('  ✓ %-10s %d 色一致' % (theme, len(code)))

    missing = sorted(set(pz.TILE_PALETTES) - {t for t, _ in secs})
    if missing:
        bad.append('提示詞漏了地貌：%s' % '、'.join(missing))
        print('  ✗ pixelize.py 有、但提示詞沒寫：%s' % '、'.join(missing))
    return bad


sys.exit(main())
