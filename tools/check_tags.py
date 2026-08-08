"""名牌位置檢查：名牌有沒有真的貼在它標的那個東西上。

為什麼需要一支專門的測試：名牌錯位不會報錯、字也是對的，
看起來只是「排版怪怪的」。而用眼睛看截圖只抓得到
「剛好被拍進去」的那幾個 —— 這個 bug 就是這樣躲過好幾輪截圖驗收的
（道具剛好都在畫面左半邊，出問題的夾值沒有生效）。

做法：對每一個真的畫出來的名牌，從世界座標算出它該在的 x，
跟實際的 style.left 相減。三種視窗 x 七顆種子。

    python3 tools/check_tags.py
"""
from playwright.sync_api import sync_playwright
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
html = (ROOT / 'web' / 'index.html').as_uri()

# 這個沙箱裡 chromium 預先裝在固定位置；CI 上則是 playwright 自己裝的，
# 讓它自己找。寫死路徑會讓這支測試「只有在我的機器上跑得起來」。
SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}

# lastOx/lastOy 是 draw() 裡算的，而 draw() 跑在 rAF 上 ——
# 同一個 evaluate 裡設完鏡頭馬上量，量到的是上一幀的偏移，
# 所有名牌都會被判成出界而消失。所以要等兩幀。
SETUP = """(seed)=>new Promise(done=>{
  LANG='zh'; VILLAGE.act=0; newGame(seed); G.floor=2; buildFloor(); vision();
  camX = G.p.x - VW/2 + .5; camY = G.p.y - VH/2 + .5;
  refresh();
  requestAnimationFrame(()=>requestAnimationFrame(()=>{ updateTags(); done(1); }));
})"""

MEASURE = """()=>{
  const rect = cv.getBoundingClientRect();
  const s = rect.width / cv.width;
  const wx = x => (lastOx + x*16 + 8) * s;
  const map = {};
  for(const m of G.mons) if(G.seen[key(m.x,m.y)]===2) map[locName('mon',m.d)] = m.x;
  for(const k in G.items) map[nameOf(G.items[k])] = k % MW;
  for(const k in G.gold)  map[G.gold[k]+' G']     = k % MW;
  map['下樓'] = G.f.stairs.x;
  const out = [];
  for(const e of document.querySelectorAll('#tags .tag')){
    if(e.style.display === 'none') continue;
    const t = e.textContent;
    if(!(t in map)) continue;
    out.push({txt:t, want:wx(map[t]), got:parseFloat(e.style.left)});
  }
  return {rectW:rect.width, cvW:cv.width, rows:out};
}"""

HAN = re.compile(r'[\u3400-\u9fff]')
KANA = re.compile(r'[\u3040-\u30ff]')

# 讓場上同時有怪（帶狀態）、道具、金錢、陷阱、樓梯，一次收齊所有種類的名牌
LANGSCAN = """(cfg)=>new Promise(done=>{
  LANG = cfg.lang;
  VILLAGE.act = cfg.act; newGame(cfg.seed);
  const p = G.p;
  for(const d of DIRS.slice(0,4)){
    const x=p.x+d[0], y=p.y+d[1];
    if(walkable(x,y) && !monAt(x,y)) spawnMon(MONS[0], x, y);
  }
  G.items[key(p.x,p.y)] = mk('herb','heal');
  G.gold[key(p.x,p.y)]  = 50;
  G.traps[key(p.x,p.y)] = 1;
  for(const m of G.mons) m.st['睡'] = 5;
  vision();
  camX = p.x - VW/2 + .5; camY = p.y - VH/2 + .5;
  refresh();
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
    updateTags();
    done([...document.querySelectorAll('#tags .tag')]
      .filter(e=>e.style.display!=='none').map(e=>e.textContent));
  }));
})"""

bad = 0
with sync_playwright() as pw:
    b = pw.chromium.launch(**LAUNCH)
    for w,h,lbl in [(393,780,'phone 393'), (360,640,'phone 360'), (1280,900,'desk 1280')]:
        pg = b.new_page(viewport={'width':w,'height':h}, device_scale_factor=2,
                        has_touch=w<800, is_mobile=w<800)
        pg.goto(html); pg.wait_for_timeout(400)
        pg.click('#start'); pg.wait_for_timeout(500)
        worst, n, worstT = 0, 0, None
        for seed in (7, 21, 44, 88, 101, 205, 333):
            pg.evaluate(SETUP, seed); pg.wait_for_timeout(80)
            r = pg.evaluate(MEASURE)
            for row in r['rows']:
                d = abs(row['got'] - row['want']); n += 1
                if d > worst: worst, worstT = d, row
        mark = '✗' if worst > 12 else '✓'
        print('%s %-11s 畫布 CSS %.0f / 內部 %d　量了 %d 個名牌　最大水平偏移 %.1f px'
              % (mark, lbl, r['rectW'], r['cvW'], n, worst))
        if worst > 12:
            bad += 1
            print('     最糟：「%s」該在 %.1f，實際 %.1f' % (worstT['txt'], worstT['want'], worstT['got']))
        pg.close()

    # ── 第二段：名牌上的字有沒有翻 ──────────────────────────────
    # 這一段跟上面的位置檢查放在同一支，是因為它們需要的是同一件昂貴的東西：
    # 一個真的把畫布畫出來的瀏覽器。web/i18n.js 掃得到所有資料表，
    # 但掃不到「畫在畫布上的名牌」—— 而那正是漏了最久的地方：
    # 「Cave Rat·睡」名字翻了、狀態沒翻，比整句沒翻更刺眼。
    pg = b.new_page(viewport={'width': 393, 'height': 780})
    pg.goto(html); pg.wait_for_timeout(400)
    pg.click('#start'); pg.wait_for_timeout(500)
    for lang in ('en', 'ja'):
        leak = set()
        for act in range(15):
            for seed in (11, 77):
                for t in pg.evaluate(LANGSCAN, {'lang': lang, 'act': act, 'seed': seed}):
                    if not HAN.search(t):
                        continue
                    # 日文用漢字是正常的，有假名就當它是日文
                    if lang == 'ja' and KANA.search(t):
                        continue
                    leak.add(t)
        mark = '✗' if leak else '✓'
        print('%s %-11s 畫布名牌殘留 %d 種%s'
              % (mark, lang, len(leak), ('：' + '、'.join(sorted(leak)[:5])) if leak else ''))
        if leak:
            bad += 1
    pg.close()
    b.close()
print()
print('全部通過' if not bad else '有 %d 項不合格' % bad)
sys.exit(1 if bad else 0)
