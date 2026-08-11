"""版面檢查：玩家非看到不可的東西，有沒有真的在畫面上。

為什麼要專門一支：這個 repo 已經出過兩次同一類 bug，而且兩次都不報錯 ——
  · 村莊的「再次下潛」按鈕在手機上被推到摺線下面，玩家以為卡住了
  · 桌機上整條血量狀態列被推到視窗**上緣之外**，而且捲不回來
    （body 是 `display:flex; align-items:center`，flex 置中在內容過高時
     會往上下兩邊一起溢出，上面那一半沒有捲軸可以到達）
    使用者的原話：「hp 那一條狀態列被蓋掉，需要到螢幕 50% 才看得清楚」。

這一類失敗的共同點是：程式沒有壞、字也是對的、測試全綠 ——
只是玩家看不到。看不到就等於沒有。

檢查兩件事，缺一不可：
  1. 元素的矩形完全落在視窗內
  2. 元素的中心點**真的點得到**（elementFromPoint 打到自己或自己的後代）

第 2 條是必要的：`#cabinet` 有 overflow:hidden，被它切掉的東西
矩形座標看起來還在文件裡，實際上一個像素都畫不出來。
只驗矩形的話，手把被切掉一半這種事會整支綠燈通過。

    python3 tools/check_layout.py
"""
from playwright.sync_api import sync_playwright
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = (ROOT / 'web' / 'index.html').as_uri()

SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}

# 真實的視窗尺寸。桌機那幾個刻意放矮的 —— 1280x620 就是使用者回報的那一台
# （1280 寬的螢幕扣掉瀏覽器的分頁列與網址列，剩下大約 620 高）。
SIZES = [
    (1280, 620, 'desktop 1280x620'),
    (1366, 660, 'laptop  1366x660'),
    (1440, 720, 'laptop  1440x720'),
    (1024, 600, 'small   1024x600'),
    (1920, 900, 'wide    1920x900'),
    (820, 1180, 'tablet   820x1180'),
    (393, 780, 'phone    393x780'),
    (360, 640, 'phone    360x640'),
    (393, 560, 'phone    393x560'),
]

# 非看到不可的東西。這份清單短，是因為它列的是「看不到就不能玩」的那幾個。
MUST_SEE = ['#sign', '#hud', '#hp', '#hpbar', '#mp', '#game']

PROBE = """(sels)=>{
  const out = [];
  const seen = (sel)=>{
    const e = document.querySelector(sel);
    if(!e) return {sel, ok:false, why:'找不到元素'};
    const cs = getComputedStyle(e);
    if(cs.display === 'none' || cs.visibility === 'hidden')
      return {sel, ok:false, why:'被隱藏'};
    const r = e.getBoundingClientRect();
    if(r.width < 1 || r.height < 1) return {sel, ok:false, why:'尺寸為 0'};
    if(r.top < 0 || r.left < 0 || r.bottom > innerHeight || r.right > innerWidth)
      return {sel, ok:false,
              why:'超出視窗　top ' + Math.round(r.top) + '　bottom ' + Math.round(r.bottom)
                  + '　（視窗高 ' + innerHeight + '）'};
    // 中心點真的看得到嗎 —— 被 overflow:hidden 切掉的東西矩形還在，但畫不出來
    const hit = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
    if(!hit || !(e.contains(hit) || hit.contains(e)))
      return {sel, ok:false, why:'中心點被蓋住或被裁切：' + (hit ? (hit.id ? '#'+hit.id : hit.tagName) : 'null')};
    return {sel, ok:true};
  };
  for(const s of sels) out.push(seen(s));
  return {
    rows: out,
    overflowX: document.documentElement.scrollWidth - innerWidth,
    // 垂直可以捲（有捲軸就到得了），但橫向捲是永遠的版面 bug
  };
}"""


def main():
    bad = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch(**LAUNCH)
        for w, h, tag in SIZES:
            pg = b.new_page(viewport={'width': w, 'height': h},
                            has_touch=w < 800, is_mobile=w < 800)
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto(HTML)
            pg.wait_for_timeout(350)
            pg.click('#start')
            pg.wait_for_timeout(900)

            r = pg.evaluate(PROBE, MUST_SEE)
            fails = [x for x in r['rows'] if not x['ok']]
            over = r['overflowX']
            mark = '✓' if (not fails and over <= 2) else '✗'
            print('%s %-18s' % (mark, tag), end='')
            if over > 2:
                print('　水平溢出 %d px' % over, end='')
            print()
            for f in fails:
                print('     %-10s %s' % (f['sel'], f['why']))
            if fails or over > 2:
                bad += 1

            # 村莊：那顆「前往下一章」的按鈕曾經在手機上掉到摺線外
            pg.evaluate("()=>{ VILLAGE.act=1; VILLAGE.gold=3000; openVillage(); }")
            pg.wait_for_timeout(400)
            v = pg.evaluate(PROBE, ['#vgo', '#vboard'])
            vf = [x for x in v['rows'] if not x['ok']]
            if vf:
                bad += 1
                print('     村莊：')
                for f in vf:
                    print('       %-10s %s' % (f['sel'], f['why']))
            # ── 保險絲：就算版面因故變太高，上緣也不能被推出畫面 ──
            # body 是 flex 置中，而 flex 置中在內容過高時會往**上下兩邊**溢出，
            # 上面那一半沒有捲軸可以到達 —— 這正是使用者遇到的那個 bug。
            # 上面的 fitCanvas() 修好之後內容永遠塞得下，這條保險絲就
            # 再也不會被觸發，也就永遠測不到。所以這裡刻意把它撐爆，
            # 確認 `align-items:safe center` 真的把溢出趕到下面（捲得到）。
            if w > 620:
                pg.evaluate("""()=>{
                  document.querySelector('#cabinet').style.maxHeight = 'none';
                  const wr = document.querySelector('#screenwrap');
                  wr.style.maxWidth = 'none'; wr.style.width = '1600px';
                }""")
                pg.wait_for_timeout(150)
                top = pg.evaluate("()=>Math.round(document.querySelector('#hud').getBoundingClientRect().top)")
                if top < 0:
                    bad += 1
                    print('     保險絲：版面撐爆時狀態列被推到視窗外（top %d）'
                          '　—— 需要 align-items:safe center' % top)

            if errs:
                bad += 1
                print('     ! 執行期錯誤 %s' % errs[:2])
            pg.close()
        b.close()
    print()
    print('全部通過' if not bad else '有 %d 種視窗尺寸不合格' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
