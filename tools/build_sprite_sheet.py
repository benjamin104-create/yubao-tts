#!/usr/bin/env python3
"""從 web/index.html 產生美術驗收頁 web/sprite_sheet.html。

為什麼要用產生的：驗收頁需要跟遊戲用「同一份」精靈與地形程式碼。
第一版是手工複製過去的，結果遊戲改了色盤、驗收頁還停在舊版本 ——
一個永遠顯示舊東西的驗收頁，比沒有驗收頁更危險。

切法：index.html 的 <script> 從 `"use strict";` 到「地圖生成」註解為止，
剛好就是美術層（色盤 / 精靈資料 / 程序化地形 / 道具圖示生成器），
後面才是地圖與遊戲邏輯。這條界線本來就存在，這支工具只是照著切。

用法：
    python3 tools/build_sprite_sheet.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "web", "index.html")
DST = os.path.join(ROOT, "web", "sprite_sheet.html")

ART_END = "/* ─── 地圖生成"

SHELL = """<meta charset="utf-8"><title>sprite sheet — 深淵行商人</title>
<style>
body{background:#14110f;color:#e8dcc0;font-family:system-ui,sans-serif;margin:0;padding:20px}
h1{font-size:15px;letter-spacing:.18em;color:#e8dcc0;font-weight:600;margin:0 0 4px}
p.note{font-size:11.5px;color:#a99a7e;margin:0 0 18px;line-height:1.6}
h2{font-size:13px;letter-spacing:.2em;color:#c9973f;margin:22px 0 10px;font-weight:600}
.grid{display:flex;flex-wrap:wrap;gap:14px}
.cell{text-align:center;font-size:10px;color:#a99a7e;width:104px}
.cell canvas{image-rendering:pixelated;width:96px;height:96px;background:#232c32;display:block;margin-bottom:4px}
.cell.tall{width:104px}
.cell.tall canvas{width:96px;height:144px}
</style>
<h1>美術驗收表</h1>
<p class="note">全部放大到 6 倍。驗收標準：關掉名稱也要認得出是什麼，
同類道具之間要有輪廓差異（只換顏色不算）。<br>
此頁由 <code>tools/build_sprite_sheet.py</code> 從 <code>web/index.html</code> 產生，
不要手改 —— 改了下次重建就沒了。</p>
<div id="out"></div>
<script>
"""

TAIL = """
/* ─── 驗收頁渲染 ─────────────────────────────────────────────── */
const out = document.getElementById('out');
function sec(t){ const h=document.createElement('h2'); h.textContent=t; out.appendChild(h);
  const g=document.createElement('div'); g.className='grid'; out.appendChild(g); return g; }
function add(g, cv, label){
  const d=document.createElement('div'); d.className='cell';
  const c=document.createElement('canvas'); c.width=16;c.height=16;
  c.getContext('2d').drawImage(cv,0,0);
  d.appendChild(c); const s=document.createElement('div'); s.textContent=label; d.appendChild(s);
  g.appendChild(d);
}
const NAMES={player:'玩家',rat:'洞穴鼠',slime:'藍史萊姆',goblin:'綠哥布林',shroom:'醉步蕈',
 imp:'投石妖精',grub:'食腐蟲',skeleton:'骷髏兵',wolf:'疾風狼',mage:'詛咒法師',
 golem:'徘徊石像',turret:'水晶砲台',knight:'深淵騎士'};
let g = sec('生物骨架：顏色 / 年齡 / 帽子');
add(g, makeBlob('#',{star:true,dark:'@'}), '主角');
[['l','綠'],['q','藍'],['u','金'],['b','棕'],['6','灰'],['m','薄荷']].forEach(([c,n])=>
  add(g, makeBlob(c), '村人·'+n));
add(g, makeBlob('b',{age:'old'}), '老人');
add(g, makeBlob('l',{age:'child'}), '小孩');
[['helm','戰士盔'],['cone','黑魔尖帽'],['hood','白魔頭巾'],
 ['cap','盜賊皮帽'],['plume','獵人羽帽'],['horn','狂戰角盔']].forEach(([h,n])=>
  add(g, makeBlob('#',{star:true,dark:'@',hat:h}), n));

g = sec('主角與裝備外觀');
add(g, heroSprite(-1,-1,null), '徒手');
['木棒','銅之劍','長槍','鋼之劍','秘銀之劍'].forEach((n,i)=>add(g, heroSprite(i,-1,null), n));
['皮之盾','木之盾','鋼之盾','鏡之盾'].forEach((n,i)=>add(g, heroSprite(-1,i,null), n));
add(g, heroSprite(4,3,'helm'), '秘銀+鏡盾+盔');

g = sec('怪物 12');
for(const k in SPR) add(g, atlas[k], NAMES[k]||k);
g = sec('地形');
TILE_ART.floor.forEach((c,i)=>add(g,c,'房間地板'+i));
TILE_ART.corr.forEach((c,i)=>add(g,c,'通道'+i));
add(g,TILE_ART.wall,'牆'); add(g,TILE_ART.wallFace,'牆(有立面)');
add(g,TILE_ART.stairs,'樓梯'); add(g,TILE_ART.rock,'未探索岩盤');
add(g,goldIcon,'金錢'); add(g,trapIcon,'陷阱');
g = sec('地標：一章一個（2 格寬 x 3 格高）');
function addTall(g, cv, label){
  const d=document.createElement('div'); d.className='cell tall';
  const c=document.createElement('canvas'); c.width=32;c.height=48;
  c.getContext('2d').drawImage(cv,0,0);
  d.appendChild(c); const s=document.createElement('div'); s.textContent=label; d.appendChild(s);
  g.appendChild(d);
}
[['forest','巨樹'],['beast','巨獸頭骨'],['mountain','界碑'],['lake','石燈籠'],
 ['wood','鳥居'],['mirror','立鏡'],['crystal','水晶簇'],['spire','守望像'],
 ['briar','守望像(紅)'],['void','裂隙'],['stone','礦車']].forEach(([t,n])=>{
  const th = THEMES[t]; addTall(g, makeLandmark(th.mark, th.ramp), n);
});

g = sec('草藥 14 種外觀');
for(let i=0;i<14;i++) add(g, makeHerb(i), 'herb_'+String(i).padStart(2,'0'));
g = sec('卷軸 11 種外觀');
for(let i=0;i<11;i++) add(g, makeScroll(i), 'scroll_'+String(i).padStart(2,'0'));
g = sec('杖 9 種外觀');
for(let i=0;i<9;i++) add(g, makeWand(i), 'wand_'+String(i).padStart(2,'0'));
g = sec('壺 6 種外觀');
for(let i=0;i<6;i++) add(g, makePot(i), 'pot_'+String(i).padStart(2,'0'));
g = sec('食物 / 武器 / 盾牌');
for(let i=0;i<3;i++) add(g, makeFood(i), '食物'+i);
for(let i=0;i<5;i++) add(g, makeWeapon(i), '武器'+i);
for(let i=0;i<4;i++) add(g, makeShield(i), '盾牌'+i);
</script>
"""


def main():
    html = open(SRC, encoding="utf-8").read()
    m = re.search(r'<script>\n"use strict";([\s\S]*)</script>', html)
    if not m:
        sys.exit("在 %s 裡找不到遊戲腳本" % SRC)
    script = m.group(1)

    if ART_END not in script:
        sys.exit("找不到美術層的結尾標記 %r —— index.html 的結構變了" % ART_END)
    art = script[:script.index(ART_END)]

    # 這一頁不跑遊戲，所以美術層裡不能留下對 G / 地圖的依賴。
    # 真有依賴就代表切錯地方，寧可在這裡爆掉也不要產出一頁壞掉的驗收表。
    # `G.` 後面一定接識別字。不這樣限制的話，多語言詞條裡的
    # "Picked up {n} G." 會被當成引用了遊戲狀態 —— 守衛誤報比不報更煩，
    # 因為它會讓人開始忽略守衛。
    checks = [(r"\bG\.[A-Za-z_$]", "G."), (r"\bMW\b", "MW"), (r"\bgenFloor\b", "genFloor")]
    for pat, bad in checks:
        if re.search(pat, art):
            sys.exit("美術層引用了遊戲狀態 %r —— 切點需要重新檢查" % bad)

    open(DST, "w", encoding="utf-8").write(SHELL + '"use strict";' + art + TAIL)
    print("寫出 %s（美術層 %d 行）" % (DST, art.count("\n")))


if __name__ == "__main__":
    main()
