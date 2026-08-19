#!/usr/bin/env python3
"""主角的分層合成，在圖真的到之前先驗一次。

為什麼要有這一支：主角跟怪物不一樣。怪物是一張圖換一張圖，換錯了打開就看到；
主角是**四層疊出來的** —— 身體 × 帽子 × 盾 × 武器，六種體型 × 十種顏色 ×
九頂帽子 × 八把武器 × 六面盾 = 25920 種組合。接線接錯的話，
最常見的下場不是「畫面壞掉」，而是「圖悄悄沒被用到」：
遊戲照跑、看起來跟以前一模一樣，因為它退回了程式畫的那一版。

而且這條路上有三個只有真的疊起來才會發現的坑：
  1. 換顏色是色階置換 —— 換錯範圍會把眼白跟星芒一起染色（十種有九種是壞的）
  2. 圖是非同步載進來的，載進來的時候三份快取（主角、造型選單、封面）
     全部還是舊的，忘了作廢就要等玩家換一次造型才會更新
  3. 帽子一張圖兩個用途（戴在頭上／掉在地上），少接一邊不會報錯

所以這一支自己生一組**假的**主角與帽子圖（用色盤裡指定的那五個色），
接進去，然後問：身體換到了嗎、顏色換對了嗎、眼白有沒有被染到、
帽子疊上去了嗎、地上的圖示換到了嗎、武器還畫得出來嗎。

假圖是刻意的 —— 它讓這一支在「真的圖還沒生出來」的時候就能跑，
而那正是需要它的時候。真的圖到了之後由 check_art.py 驗畫得好不好。

    python3 tools/check_hero.py
"""

import functools
import http.server
import os
import pathlib
import re
import shutil
import struct
import sys
import tempfile
import threading
import zlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')

SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}
if not LAUNCH and os.path.exists('/opt/pw-browsers/chromium'):
    LAUNCH = {'executable_path': '/opt/pw-browsers/chromium'}


def table(name, pat):
    """從 index.html 裡讀清單，不在這裡手抄一份。

    手抄的下場是加了第七種體型之後，這一支還在驗那六種 —— 而新加的
    那一種正好是最可能出問題的。"""
    i = SRC.index(name)
    got = re.findall(pat, SRC[i:SRC.index('};' if '{' in name else '];', i)], re.M)
    # 空清單會讓後面每一項「六種互不相同」都變成 0 === 0 的假通過 ——
    # 第一次跑這一支就是這樣：正則少了 MULTILINE，體型讀成零個，
    # 假圖一張都沒生，而檢查全綠。空的就當場停。
    if not got:
        sys.exit('從 index.html 讀不到 %s —— 正則跟不上原始碼了' % name)
    return got


SKINS = table('const BLOB_SKINS = {', r'^  ([a-z]+): \[')
HATS = table('const HAT = [', r"\{id:'([a-z]+)'")
COLS = re.findall(r"'(.)'", SRC[SRC.index('const BLOB_COLS = ['):SRC.index('];', SRC.index('const BLOB_COLS = ['))])
PAL = dict(re.findall(r"'(.)':'(#[0-9a-f]{6})'", SRC[SRC.index('const PAL = {'):SRC.index('};', SRC.index('const PAL = {'))]))
RAMP = {}
_r = SRC[SRC.index('const BLOB_RAMP = {'):SRC.index('};', SRC.index('const BLOB_RAMP = {'))]
for m in re.finditer(r"'(.)': \['(.)','(.)','(.)'\]", _r):
    RAMP[m.group(1)] = [m.group(2), m.group(3), m.group(4)]


def rgb(ch):
    h = PAL[ch]
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


def png(pixels, w=32, h=32):
    """最小的 PNG 寫出器。這一支只需要生幾張純色方塊，
    為此拉一個影像函式庫進來（而且要跟 CI 的版本對齊）不划算。"""
    raw = b''.join(b'\x00' + b''.join(bytes(pixels[y][x]) for x in range(w))
                   for y in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw))
            + chunk(b'IEND', b''))


CLEAR = (0, 0, 0, 0)


def body_png(n=0):
    """假的身體：描邊 + 三階陶土 + 兩顆眼白。

    位置照 BLOB_SKINS 那一段的解剖約定（32 尺度）：
    頭頂在 y6、眼睛在 y12、腳底貼齊 y31。"""
    p = [[CLEAR] * 32 for _ in range(32)]
    for y in range(6, 32):
        for x in range(4, 28):
            p[y][x] = rgb('#') + (255,)
    for y in range(6, 32):                       # 左右描邊
        p[y][4] = p[y][27] = rgb('0') + (255,)
    for x in range(4, 28):                       # 上下描邊
        p[6][x] = p[31][x] = rgb('0') + (255,)
    for y in range(7, 10):                       # 左上受光
        for x in range(5, 12):
            p[y][x] = rgb('*') + (255,)
    for y in range(26, 31):                      # 右下暗面
        for x in range(16, 27):
            p[y][x] = rgb('@') + (255,)
    for y in range(11, 15):                      # 兩顆眼白 —— 換色時不准被染到
        for x in list(range(7, 11)) + list(range(21, 25)):
            p[y][x] = rgb('+') + (255,)
    # 每一張留一個不同的記號。六張一模一樣的話，「六種體型互不相同」
    # 就驗不到「載進來的圖有沒有被塞進正確的那一格」——
    # 而那正是這種 for 迴圈最典型的接錯法。
    p[17][18 + n] = rgb('0') + (255,)
    return png(p)


def hat_png():
    """假的帽子：只佔 y0~y10，其餘透明。
    佔滿整格的話就分不出「疊上去了」跟「把身體蓋掉了」。"""
    p = [[CLEAR] * 32 for _ in range(32)]
    for y in range(0, 11):
        for x in range(6, 26):
            p[y][x] = rgb('v') + (255,)
    return png(p)


JS = r"""
(() => {
  const out = [];
  const ok = (name, cond, note) => out.push([!!cond, name, note || '']);

  // 讀畫布上某一格的顏色。同源 http 底下不會被污染，讀得回來。
  const probe = (cv, x, y) => {
    const c = document.createElement('canvas');
    c.width = c.height = cv.width;
    const g = c.getContext('2d');
    g.imageSmoothingEnabled = false;
    g.drawImage(cv, 0, 0, cv.width, cv.height);
    const d = g.getImageData(x, y, 1, 1).data;
    return '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
  };
  const same = (a, b) => {
    if(a.width !== b.width) return false;
    const g = (cv) => { const c = document.createElement('canvas');
      c.width = c.height = cv.width; const x = c.getContext('2d');
      x.imageSmoothingEnabled = false; x.drawImage(cv, 0, 0, cv.width, cv.width);
      return x.getImageData(0, 0, cv.width, cv.width).data.join(','); };
    return g(a) === g(b);
  };

  const CFG = %s;

  for(const sk of CFG.skins) ok('身體圖載到了 ' + sk, !!HERO_ART[sk]);
  for(const h of CFG.hats)   ok('帽子圖載到了 ' + h, !!HAT_ART_IMG[h]);

  // 主角的合成畫布要是 32 —— 還是 16 就代表整個外部圖的路徑沒走到
  ok('主角合成在 32 的畫布上', atlas.player.width === 32, '實際 ' + atlas.player.width);

  // 換顏色：身體那一格要換成該色階的中階，眼白與描邊一格都不准動
  for(const col of CFG.cols){
    const c = tintHero('blob', col);
    if(!c){ ok('換色 ' + col, false, 'tintHero 回 null'); continue; }
    ok('換色 ' + col + ' 身體換到了', probe(c, 14, 20) === CFG.mid[col],
       probe(c, 14, 20) + ' 應為 ' + CFG.mid[col]);
    ok('換色 ' + col + ' 眼白沒被染到', probe(c, 8, 12) === CFG.white,
       probe(c, 8, 12));
    ok('換色 ' + col + ' 描邊沒被染到', probe(c, 4, 20) === CFG.dark,
       probe(c, 4, 20));
  }
  // 十種顏色要真的是十種。少一種不會報錯，只是兩個選項長得一樣
  const seen = {};
  for(const col of CFG.cols){
    const c = tintHero('blob', col);
    if(c) seen[probe(c, 14, 20)] = 1;
  }
  ok('十種顏色互不相同', CFG.cols.length > 1 && Object.keys(seen).length === CFG.cols.length,
     '只有 ' + Object.keys(seen).length + ' 種');

  // 六種體型要真的是六張不同的圖
  const shapes = {};
  for(const sk of CFG.skins){
    const c = document.createElement('canvas'); c.width = c.height = 32;
    const x = c.getContext('2d'); x.imageSmoothingEnabled = false;
    x.drawImage(HERO_ART[sk], 0, 0, 32, 32);
    shapes[x.getImageData(0, 0, 32, 32).data.join(',')] = 1;
  }
  ok('六種體型互不相同', CFG.skins.length > 1 && Object.keys(shapes).length === CFG.skins.length,
     '只有 ' + Object.keys(shapes).length + ' 種');

  // 帽子要疊得上去，而且九頂互不相同
  const bare = heroSprite(-1, -1, null, 'blob', '#');
  const hatted = {};
  for(const h of CFG.hats){
    const c = heroSprite(-1, -1, h, 'blob', '#');
    ok('戴上 ' + h + ' 有變化', !same(bare, c));
    hatted[probe(c, 16, 4)] = 1;
  }
  // 假圖九頂同色，所以這裡只驗「疊上去的位置是頭頂那幾排」
  ok('帽子疊在頭頂', probe(heroSprite(-1, -1, CFG.hats[0], 'blob', '#'), 16, 4)
                     === CFG.hatcol);

  // 掉在地上的圖示也要換到，而且要跟戴著的是同一頂
  for(let i = 0; i < CFG.hats.length; i++)
    ok('地上的圖示換到了 ' + CFG.hats[i], atlas['hat#' + i] && atlas['hat#' + i].width === 32);

  // 裝備仍然畫得出來 —— 換了身體的圖之後最容易掉的就是這一層
  ok('拿了武器看得出來', !same(bare, heroSprite(0, -1, null, 'blob', '#')));
  ok('拿了盾看得出來',   !same(bare, heroSprite(-1, 0, null, 'blob', '#')));
  ok('換武器看得出來',   !same(heroSprite(0, -1, null, 'blob', '#'),
                              heroSprite(7, -1, null, 'blob', '#')));

  // 造型選單與封面的快取要跟著作廢 —— 沒作廢的話它們會停在程式畫的舊主角
  ok('造型選單用的是同一份', blobFor('#', 'blob').width === 32);
  const cov = document.getElementById('coverart');
  ok('封面用的是同一份', cov && cov.width === 32, cov ? '' + cov.width : '沒有封面');

  return out;
})()
"""


def run(page, url, cfg):
    page.goto(url)
    page.wait_for_function('typeof heroSprite === "function"')
    # 圖是非同步載的。等到全部就位再問 —— 這裡等的是遊戲自己的表，
    # 不是等固定秒數：固定秒數在 CI 上遲早會有一次剛好不夠。
    page.wait_for_function(
        'Object.keys(HERO_ART).length === %d && Object.keys(HAT_ART_IMG).length === %d'
        % (len(SKINS), len(HATS)), timeout=15000)
    return page.evaluate(JS % cfg)


def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='hero-'))
    try:
        shutil.copytree(ROOT / 'web', tmp / 'web')
        (tmp / 'web' / 'art' / 'hero').mkdir(parents=True, exist_ok=True)
        (tmp / 'web' / 'art' / 'hat').mkdir(parents=True, exist_ok=True)
        for n, sk in enumerate(SKINS):
            (tmp / 'web' / 'art' / 'hero' / (sk + '.png')).write_bytes(body_png(n))
        for h in HATS:
            (tmp / 'web' / 'art' / 'hat' / (h + '.png')).write_bytes(hat_png())

        h = functools.partial(http.server.SimpleHTTPRequestHandler,
                              directory=str(tmp / 'web'))
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]

        import json
        cfg = json.dumps({
            'skins': SKINS, 'hats': HATS, 'cols': COLS,
            'mid': {c: PAL[RAMP[c][1]] for c in COLS},
            'white': PAL['+'], 'dark': PAL['0'], 'hatcol': PAL['v'],
        }, ensure_ascii=False)

        with sync_playwright() as pw:
            b = pw.chromium.launch(**LAUNCH)
            res = run(b.new_page(), url, cfg)
            b.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    bad = 0
    for good, name, note in res:
        print(('  ✓ ' if good else '  ✗ ') + name + (('　' + note) if note else ''))
        bad += not good
    print('\n%d 項檢查，%d 項失敗' % (len(res), bad))
    sys.exit(1 if bad else 0)


main()
