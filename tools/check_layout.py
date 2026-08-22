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
  /* 算圖解析度有沒有真的生效。這條看起來多餘，但它抓過一個不會報錯的 bug：
     fitViewport() 只比對格數，桌機開場時格數本來就等於預設值，於是直接
     return，畫布一直停在 HTML 屬性寫的尺寸 —— 邏輯尺寸對、外部圖也載進來了，
     只是全部在半解析度上算圖。畫面看起來只是「有點糊」，很像本來就這樣。 */
  if(cv.width !== SW*RS || cv.height !== SH*RS)
    out.push({sel:'算圖解析度', ok:false,
              why:'畫布 ' + cv.width + 'x' + cv.height +
                  '　應為 ' + (SW*RS) + 'x' + (SH*RS) + '（邏輯 ' + SW + 'x' + SH + ' × ' + RS + '）'});
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

            # 訊息視窗（特魯內克那種跳出來的對話框）真的看得到嗎。
            #
            # 它不能列進 MUST_SEE：安靜四秒它就自己收起來了，
            # 而「該在的時候在」跟「一直都在」是兩件不同的事。
            #
            # 這一條抓過的 bug 很具體：視窗貼在機殼下緣，而虛擬手把
            # 是 z-index 20 的絕對定位 —— 三行字整段被十字鍵壓在底下，
            # 沒有錯誤、沒有警告，只是玩家永遠讀不到「哪一隻在打你」。
            mw = pg.evaluate("""()=>{
              say('大老鼠 的攻擊！　主角 受到 6 點傷害。','bad');
              say('主角 的攻擊！　大老鼠 倒下了。','good');
              say('撿到了 回復草。');
              refresh();
              const e = document.getElementById('msgwin');
              if(!e) return {ok:false, why:'找不到訊息視窗'};
              const cs = getComputedStyle(e);
              if(cs.display === 'none') return {ok:false, why:'有訊息卻沒有顯示'};
              const r = e.getBoundingClientRect();
              if(r.width < 40 || r.height < 10)
                return {ok:false, why:'尺寸太小 ' + Math.round(r.width) + 'x' + Math.round(r.height)};
              if(r.bottom > innerHeight + 1 || r.top < -1)
                return {ok:false, why:'超出視窗 top ' + Math.round(r.top) +
                                      ' bottom ' + Math.round(r.bottom) + ' / ' + innerHeight};
              /* 三個取樣點都要真的看得到 —— 只驗中心的話，被手把蓋掉半邊
                 仍然會過，而被蓋掉的那半邊正好是最舊的那一行。

                 量之前要先把 pointer-events 打開：訊息視窗本身是
                 pointer-events:none（它不該擋住點地圖），而
                 elementFromPoint 會直接穿過那種元素，回報底下的畫布 ——
                 於是「沒有被蓋住」也會被判成被畫布蓋住。
                 打開之後回報的才是真正畫在它**上面**的東西。 */
              const pe = e.style.pointerEvents;
              e.style.pointerEvents = 'auto';
              let bad = null;
              for(const fx of [0.15, 0.5, 0.85]){
                const px = r.left + r.width * fx, py = r.top + r.height / 2;
                const hit = document.elementFromPoint(px, py);
                if(!hit || !(e.contains(hit) || hit.contains(e))){
                  bad = '被蓋住（x ' + Math.round(fx*100) + '%）：' +
                        (hit ? (hit.id ? '#'+hit.id : hit.className || hit.tagName) : 'null');
                  break;
                }
              }
              e.style.pointerEvents = pe;
              if(bad) return {ok:false, why:bad};
              // 三行都要在
              if(e.childElementCount !== 3)
                return {ok:false, why:'只有 ' + e.childElementCount + ' 行'};
              return {ok:true};
            }""")
            if not mw['ok']:
                print('     %-10s %s' % ('#msgwin', mw['why']))
                bad += 1

            # 背包圖示的畫布不能比來源的圖小。
            #
            # CSS 把那些畫布顯示成 24~34 px，但畫布本身一直是 16x16。
            # 以前無所謂（來源就是 16px 的程式畫圖），接上 32px 的外部圖之後，
            # 同一段程式會先把 32 壓成 16、再由 CSS 放大回去 ——
            # 一來一回丟掉一半的細節。它不會報錯，只是背包裡的圖比地上的糊，
            # 兩個畫面又不會同時出現，所以幾乎不可能自己發現。
            if w > 620:
                ic = pg.evaluate("""()=>{
                  G.p.inv.length = 0;
                  const out = [];
                  for(const d of HERB.slice(0, 6)) G.p.inv.push(mk('herb', d.id, {known:1}));
                  openPanel('inv');
                  for(const c of document.querySelectorAll('#panel canvas')){
                    const src = c.dataset.srcw ? +c.dataset.srcw : null;
                    out.push(c.width);
                  }
                  closePanel();
                  // 來源有多大：直接問 atlas 裡那幾張草的圖
                  const srcs = G.p.inv.map(it => iconOf(it).width);
                  return {canvas: out, src: srcs};
                }""")
                small = [(cw, sw) for cw, sw in zip(ic['canvas'], ic['src']) if cw < sw]
                if small:
                    bad += 1
                    print('     背包圖示被壓小了：畫布 %s，來源 %s'
                          % (small[0][0], small[0][1]))

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
