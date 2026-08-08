from playwright.sync_api import sync_playwright
import pathlib, sys
html = pathlib.Path('/home/user/yubao-tts/web/index.html').resolve().as_uri()

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

bad = 0
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
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
    b.close()
sys.exit(1 if bad else 0)
