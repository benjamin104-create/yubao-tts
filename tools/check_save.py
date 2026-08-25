#!/usr/bin/env python3
"""存檔在真的瀏覽器裡到底存不存得住。

web/save.js 量的是「存檔格式讀回來對不對」，那是 node，沒有畫面 ——
它掃不到「玩家關掉分頁再打開，封面上有沒有『繼續冒險』」。
而那正是使用者踩到的：

    「為什麼我昨天試玩打半天，結果沒有紀錄？今天早上玩又從頭開始？」

量出來的原因：中途存檔只在「下樓梯」與「踩到紀錄之環」時寫，
所以**第一層從來沒有存檔點**。在第一層探索一小時再關掉分頁，
localStorage 裡是空的，重開連「繼續冒險」都不會出現 ——
沒有任何錯誤訊息，玩家只知道自己的一個下午不見了。

這一支把修好的狀態釘住，兩件事：

  1. 一進迷宮就有存檔點，關掉分頁再開，封面要有「繼續冒險」。
  2. 讀檔不會憑空多出道具。這一條是**修法本身踩出來的**：
     第一版想得更貼心 —— 離開分頁時存「當下這一刻」。結果讀檔是用
     種子重建整層，地上的東西全部復活，而背包裡撿走的那一份還在，
     實測 7 件變 13 件。樓層起點才是安全的存檔點，因為那一刻
     玩家還沒撿走任何東西。

    python3 tools/check_save.py
"""

import functools
import http.server
import os
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN_KEY = 'claude-abyss-run'

SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}
if not LAUNCH and os.path.exists('/opt/pw-browsers/chromium'):
    LAUNCH = {'executable_path': '/opt/pw-browsers/chromium'}


def serve():
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Q, directory=str(ROOT / 'web'))
    # localStorage 走 http 才穩 —— file:// 的來源在某些瀏覽器是不透明的，
    # 那會讓這支檢查因為「存不進去」而紅，指向完全錯誤的地方。
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, 'http://127.0.0.1:%d/index.html' % srv.server_address[1]


def enter(pg, url):
    """開新分頁 → 按下開始 → 跳過開場 → 站在第一層。"""
    pg.goto(url)
    pg.wait_for_timeout(1600)
    pg.get_by_text('DESCEND').first.click()
    pg.wait_for_timeout(1400)
    try:
        pg.get_by_text('Skip prologue').first.click()
    except Exception:
        pass
    pg.wait_for_timeout(1600)


def main():
    fails = []

    def ok(cond, msg):
        print(('  ✓ ' if cond else '  ✗ ') + msg)
        if not cond:
            fails.append(msg)

    srv, URL = serve()
    with sync_playwright() as pw:
        b = pw.chromium.launch(**LAUNCH)

        print('=== 第一層就要有存檔點 ===')
        ctx = b.new_context(viewport={'width': 1280, 'height': 800})
        pg = ctx.new_page()
        enter(pg, URL)
        floor = pg.evaluate('()=>G.floor')
        has = pg.evaluate("()=>!!localStorage.getItem('%s')" % RUN_KEY)
        ok(floor == 1, '確認人在第一層（實際 %s）—— 不是的話這條測到的是別的東西' % floor)
        ok(has, '一進迷宮就寫了存檔點')
        # 在第一層走一走再關掉，模擬「玩了半天沒下樓」
        for _ in range(20):
            pg.keyboard.press('ArrowRight')
            pg.keyboard.press('ArrowDown')
        pg.wait_for_timeout(400)
        pg.close()
        pg2 = ctx.new_page()
        pg2.goto(URL)
        pg2.wait_for_timeout(1800)
        vis = pg2.evaluate("()=>{const b=document.getElementById('resume');"
                           "return b ? !b.hidden : false}")
        ok(vis, '關掉分頁再打開，封面上有「繼續冒險」')

        print('\n=== 讀檔不會憑空多出道具 ===')
        # 把地上的東西全部收進背包，再關掉分頁、讀檔回來。
        # 總數（背包＋地上）必須守恆 —— 不守恆就是重建整層時把東西發了第二次。
        before = pg2.evaluate("""()=>{
          const b=document.getElementById('resume'); if(b && !b.hidden) b.click();
          return 1;
        }""")
        pg2.wait_for_timeout(2000)
        picked = pg2.evaluate("""()=>{
          let n=0;
          for(const k in G.items){ const it=G.items[k];
            if(!it.shop && G.p.inv.length<20){ G.p.inv.push(it); delete G.items[k]; n++; } }
          return {moved:n, inv:G.p.inv.length, ground:Object.keys(G.items).length};
        }""")
        ok(picked['moved'] > 0,
           '這一層地上真的有東西可以撿（%d 件）—— 沒有的話這條會通過得沒有意義'
           % picked['moved'])
        total_before = picked['inv'] + picked['ground']
        pg2.close()
        pg3 = ctx.new_page()
        pg3.goto(URL)
        pg3.wait_for_timeout(1800)
        pg3.evaluate("()=>{const b=document.getElementById('resume'); if(b) b.click();}")
        pg3.wait_for_timeout(2200)
        after = pg3.evaluate("()=>({inv:G.p.inv.length, ground:Object.keys(G.items).length})")
        total_after = after['inv'] + after['ground']
        ok(total_after == total_before,
           '讀檔前後道具總數守恆（背包＋地上：%d → %d）'
           % (total_before, total_after))
        b.close()
    srv.shutdown()

    print()
    if fails:
        print('%d 項不合格' % len(fails))
        return 1
    print('全部通過')
    return 0


sys.exit(main())
