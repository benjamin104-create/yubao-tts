"""每一個畫面的多語言檢查：把畫面一個一個打開，掃有沒有殘留的中文。

為什麼還要這一支：
  · web/i18n.js 掃得到每一張資料表，但它是 node，沒有畫面。
  · tools/check_tags.py 掃得到畫布上的名牌。
  · 兩支都掃不到「覆蓋畫面」—— 村莊、紀錄碑、死亡結算、結局。

而那正是漏最久的地方：使用者用英文玩到死掉，看到的是整片中文的
「你倒下了 / 積分 671 / 本機第 1 名 / 等級歸零、道具全失……」。
掃描沒打開過那個畫面，所以三輪檢查全部給了綠燈。

規則：把畫面打開 → 收集所有「看得見」的文字節點 → 有漢字就是嫌疑犯。
日文用漢字是正常的，所以日文那一欄只在「沒有半個假名」時才算嫌疑，
再扣掉下面那份允許清單。

    python3 tools/check_screens.py
"""
from playwright.sync_api import sync_playwright
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = (ROOT / 'web' / 'index.html').as_uri()

SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}

HAN = re.compile(r'[㐀-鿿]')
KANA = re.compile(r'[぀-ヿ]')

# 本來就該是漢字的東西。清單刻意留短 —— 每多一條就少一分保護，
# 所以每一條都要說得出理由。
ALLOW = {
    '中文', '日本語',          # 語言選擇鈕：永遠顯示自己的語言，這是刻意的
}
ALLOW_JA = {
    '攻', '防', '満腹',        # 日文的狀態列標籤本來就是這幾個漢字
    '言語：日本語',
}
# 由允許的漢字組出來的字串（村莊裡的「攻 +5」「防 +7」）。
# 用樣式而不是把每一個數字都列進清單 —— 清單一長就沒有人會維護它。
ALLOW_JA_RE = [re.compile(r'^[攻防] \+\d+$')]

# 每一個玩家看得到的畫面各來一次。順序有意義：後面的畫面靠前面的狀態。
SCREENS = [
    ('封面', "()=>{ $('cover').classList.remove('gone'); }"),
    ('遊戲中', "()=>{ $('cover').classList.add('gone'); VILLAGE.act=0; newGame(9); refresh(); }"),
    ('背包', "()=>{ for(const h of HERB) G.p.inv.push(mk('herb',h.id));"
             " G.p.inv.push(mk('wand','lava',{known:1}));"
             " G.p.inv.push(mk('weap','drgn',{known:1})); openPanel('inv'); }"),
    ('技能', "()=>{ closePanel(); VILLAGE.jobs={war:{lv:3,prog:0},nin:{lv:2,prog:0}};"
             " syncJobSkills(true); G.p.sp=3; G.p.sch={heal:3,fire:2}; openPanel('magic'); }"),
    ('腳下', "()=>{ closePanel(); G.items[key(G.p.x,G.p.y)]=mk('herb','heal'); openPanel('ground'); }"),
    ('全螢幕地圖', "()=>{ closePanel(); openBigMap(); }"),
    ('選單', "()=>{ $('bigmap').classList.remove('show'); $('menu').classList.add('show'); }"),
    ('村莊', "()=>{ $('menu').classList.remove('show'); VILLAGE.gold=3200;"
             " VILLAGE.stock=[{cat:'weap',id:'steel',up:0,runs:2}]; VILLAGE.act=4; openVillage(); }"),
    ('紀錄碑', "()=>{ VILLAGE.board=[]; G.p.lv=7; G.p.job='war';"
               " submitScore('fall'); submitScore('clear'); submitScore('act:3');"
               " submitScore('out'); openBoard(); }"),
    ('死亡結算', "()=>{ closeBoard(); $('village').classList.remove('show');"
                 " G.p.hp=0; G.over=false; VILLAGE.feather=0; G.p.inv=[]; death(); }"),
    ('天罰', "()=>{ $('over').classList.remove('show'); steal(); }"),
    ('結局', "()=>{ $('over').classList.remove('show'); ending(); }"),
]

VISIBLE = """()=>{
  const out = [];
  const walk = el => {
    const cs = getComputedStyle(el);
    if(cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
    for(const n of el.childNodes){
      if(n.nodeType === 3){ const t = n.textContent.trim(); if(t) out.push(t); }
      else if(n.nodeType === 1) walk(n);
    }
  };
  walk(document.body);
  return out;
}"""


def main():
    bad = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch(**LAUNCH)
        for lang in ('en', 'ja'):
            allow = ALLOW | (ALLOW_JA if lang == 'ja' else set())
            pg = b.new_page(viewport={'width': 393, 'height': 900})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto(HTML)
            pg.wait_for_timeout(400)
            pg.evaluate("(l)=>setLang(l)", lang)
            pg.wait_for_timeout(200)
            pg.click('#start')
            pg.wait_for_timeout(500)
            print('===== %s =====' % lang.upper())
            for name, script in SCREENS:
                try:
                    pg.evaluate(script)
                except Exception as e:
                    print('  ! %s　腳本失敗：%s' % (name, str(e).split('\n')[0][:70]))
                    bad += 1
                    continue
                pg.wait_for_timeout(180)
                # 順手量一次水平溢出。日文的明細比中文長快一倍，
                # 「翻好了但排版爆版」跟「沒翻」對玩家是同一件事。
                over = pg.evaluate("()=>document.documentElement.scrollWidth - innerWidth")
                if over > 2:
                    bad += 1
                    print('  ✗ %s　水平溢出 %d px' % (name, over))
                leak = []
                for t in pg.evaluate(VISIBLE):
                    if not HAN.search(t) or t in allow:
                        continue
                    if lang == 'ja' and KANA.search(t):
                        continue
                    if lang == 'ja' and any(r.match(t) for r in ALLOW_JA_RE):
                        continue
                    if t not in leak:
                        leak.append(t)
                if leak:
                    bad += 1
                    print('  ✗ %s' % name)
                    for l in leak[:12]:
                        print('       ' + l)
                else:
                    print('  ✓ %s' % name)
            if errs:
                print('  ! 執行期錯誤：%s' % errs[:2])
                bad += 1
            pg.close()
        b.close()
    print()
    print('全部通過' if not bad else '有 %d 個畫面沒有完全翻譯' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
