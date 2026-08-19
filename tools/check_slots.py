#!/usr/bin/env python3
"""魔法欄與技能欄：帶得上身的數量真的有上限嗎。

為什麼要一支：這一組改動全部在 UI 裡 —— 面板列了幾列、點下去有沒有換格、
選完有沒有退出。node 的邏輯測試完全掃不到（它們不開面板），
而「魔法面板列出全部法術」這種退化不會報錯，只會讓冒險中的視窗
變回原本那張長清單，也就是使用者要求改掉的那件事。

順便驗一條只有跑起來才知道的：**加點之後新開的法術會自動帶上**。
不自動帶的話，玩家加完點看到「學會了 X」然後回到一張空的魔法欄 ——
他不知道還要去另一張表按一下，那讀起來就是「魔法壞了」。

    python3 tools/check_slots.py
"""

import functools, http.server, os, pathlib, threading
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT/'web'))
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = 'http://127.0.0.1:%d/index.html' % srv.server_address[1]
SB='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
L={'executable_path':SB} if os.path.exists(SB) else ({'executable_path':'/opt/pw-browsers/chromium'} if os.path.exists('/opt/pw-browsers/chromium') else {})
with sync_playwright() as pw:
    b = pw.chromium.launch(**L); p = b.new_page(viewport={'width':1280,'height':900})
    errs=[]; p.on('pageerror', lambda e: errs.append(str(e)))
    p.goto(url); p.wait_for_function('typeof newGame === "function"')
    r = p.evaluate("""() => {
      const out=[]; const ok=(n,c,note)=>out.push([!!c,n,note||'']);
      VILLAGE.act=0; newGame(4242);
      const p=G.p;
      // 給足點數，把兩系點到 3 —— 開出好幾個法術
      p.sp=10; p.sch.heal=3; p.sch.bolt=3;
      openPanel('magic'); renderPanel();
      ok('魔法欄是 '+SPELL_SLOTS+' 格', p.spells.length===SPELL_SLOTS, '實際 '+p.spells.length);
      ok('技能欄是 '+SLOTS+' 格', p.slots.length===SLOTS, '實際 '+p.slots.length);
      const avail = spellsFor(p).length;
      ok('開出了多個法術', avail > SPELL_SLOTS, '共 '+avail+' 個');
      // 面板上「帶在身上」的列數不會超過格數
      const rows = [...document.querySelectorAll('#list .spell')].length;
      ok('冒險面板沒有把全部法術列出來', rows <= SPELL_SLOTS + SLOTS + 4,
         '列了 '+rows+' 列，法術共 '+avail+' 個');
      // 打開魔法技能表
      panelMode='spellpick'; renderPanel();
      const prows=[...document.querySelectorAll('#list .spell')];
      ok('魔法技能表列出全部法術', prows.length===avail, '列了 '+prows.length+' / '+avail);
      // 挑一個沒帶的
      p.spells[0]=null; p.spells[1]=null; panelMode='spellpick'; renderPanel();
      [...document.querySelectorAll('#list .spell')][0].click();
      ok('點一個就帶上了', p.spells.filter(Boolean).length===1, JSON.stringify(p.spells));
      ok('選完就退出到魔法面板', panelMode==='magic', panelMode);
      // 帶滿之後再挑一個 → 擠掉最早的
      panelMode='spellpick'; renderPanel();
      [...document.querySelectorAll('#list .spell')][1].click();
      const two=p.spells.filter(Boolean).length;
      panelMode='spellpick'; renderPanel();
      [...document.querySelectorAll('#list .spell')][2].click();
      ok('帶滿之後再選會擠掉最早的', p.spells.filter(Boolean).length===SPELL_SLOTS,
         JSON.stringify(p.spells));
      // 再點一次已經帶著的 → 卸下
      const first=p.spells[0];
      panelMode='spellpick'; renderPanel();
      const row=[...document.querySelectorAll('#list .spell')]
        .find((r,i)=>spellsFor(p)[i].id===first);
      row.click();
      ok('再點一次就卸下', !p.spells.includes(first), JSON.stringify(p.spells));
      // 加點會自動帶上
      p.spells=[null,null]; p.sp=3;
      panelMode='magic'; renderPanel();
      const plus=[...document.querySelectorAll('#list button')].find(b=>b.textContent==='＋');
      if(plus) plus.click();
      ok('加點之後會自動帶上', p.spells.filter(Boolean).length>0, JSON.stringify(p.spells));
      return out;
    }""")
    b.close()
bad=0
for good,name,note in r:
    print(('  ✓ ' if good else '  ✗ ')+name+(('　'+note) if note else '')); bad += not good
for e in errs: print('  ✗ 頁面錯誤：'+e); bad+=1
print('\n%d 項，%d 失敗' % (len(r)+len(errs), bad))
raise SystemExit(1 if bad else 0)
