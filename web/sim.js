// 把瀏覽器 DOM 打樁，在 node 裡跑遊戲邏輯。
// 目的跟 Godot 那邊的 test_simulation.gd 一樣：邏輯錯誤要在 headless 抓到，
// 而不是等玩家玩到第 10 層才炸。
const fs = require('fs');

function fakeCtx(){
  const noop = () => {};
  return new Proxy({}, {
    get(t, k){
      if(k === 'createRadialGradient') return () => ({ addColorStop: noop });
      if(k === 'canvas') return { width: 320, height: 240 };
      return t[k] !== undefined ? t[k] : noop;
    },
    set(t, k, v){ t[k] = v; return true; }
  });
}
function fakeEl(){
  const el = {
    style:{ setProperty(){}, removeProperty(){}, getPropertyValue(){ return ''; } }, dataset:{}, classList:{ add:()=>{}, remove:()=>{}, toggle:()=>false, contains:()=>false },
    children:[], firstElementChild:{ style:{} },
    width:0, height:0, textContent:'', innerHTML:'', className:'', disabled:false,
    getContext: fakeCtx,
    appendChild(c){ this.children.push(c); return c; },
    addEventListener(){}, onclick:null, focus(){},
  };
  return el;
}
global.document = {
  getElementById: () => fakeEl(),
  createElement: () => fakeEl(),
  querySelectorAll: () => [],
  addEventListener: () => {},
};
global.addEventListener = () => {};
// 視窗尺寸：遊戲會依螢幕方向切換視野格數，打樁成一般桌機尺寸
global.innerWidth = 1280;
global.innerHeight = 900;
global.requestAnimationFrame = () => {};
global.prompt = () => null;

// 直接從單檔 HTML 裡把 <script> 挖出來跑。
// 不另外維護一份 game.js —— 兩份會不同步，而不同步的測試比沒有測試更糟。
const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const m = html.match(/<script>\n"use strict";([\s\S]*)<\/script>/);
if(!m){ console.error('index.html 裡找不到遊戲腳本'); process.exit(2); }
const js = m[1];
// 讓內部函式可以從外面呼叫
eval(js + '\n;globalThis.__api = {' +
  'G:()=>G, newGame, tryMove, endTurn, descend, useItem, DIRS, key, walkable,' +
  'monAt, nameOf, pAtk, pDef, cornerOK, MW, MH, WALL, DOWN, tileAt, rollItem, mk' +
  '};');
const api = globalThis.__api;

// ── BFS 尋路（與實際移動規則一致：8 向 + 牆角規則） ──
function nextStep(G, from, goal){
  if(from.x===goal.x && from.y===goal.y) return null;
  const came = new Map([[api.key(from.x,from.y), null]]);
  const q = [from]; let h = 0;
  while(h < q.length){
    const cur = q[h++];
    for(const d of api.DIRS){
      const nx = cur.x+d[0], ny = cur.y+d[1], k = api.key(nx,ny);
      if(came.has(k) || !api.walkable(nx,ny)) continue;
      if(!api.cornerOK(cur.x,cur.y,nx,ny)) continue;
      came.set(k, cur);
      if(nx===goal.x && ny===goal.y){
        let node = {x:nx,y:ny};
        while(true){
          const par = came.get(api.key(node.x,node.y));
          if(!par) break;
          if(par.x===from.x && par.y===from.y) return [node.x-from.x, node.y-from.y];
          node = par;
        }
        return null;
      }
      q.push({x:nx,y:ny});
    }
  }
  return null;
}

const RUNS = 60, MAX_TURNS = 1500;
let stats = { deaths:0, starve:0, turns:0, floors:0, maxFloor:0, lv:0, items:0, used:0, errs:0, ident:0 };

for(let r=0; r<RUNS; r++){
  try{
    api.newGame(r*7919 + 13);
    const G = api.G();
    let t = 0;
    while(!G.over && t < MAX_TURNS){
      const p = G.p;
      // 餓了就吃
      const food = p.inv.find(i=>i.cat==='food');
      if(p.sat < 25000 && food){ api.useItem(food,false); api.endTurn(); stats.used++; t++; continue; }
      // 低血喝已知回復草
      if(p.hp*3 < p.mhp){
        const h = p.inv.find(i=>i.cat==='herb' && i.id==='heal' && G.known['herb/heal']);
        if(h){ api.useItem(h,false); api.endTurn(); stats.used++; t++; continue; }
      }
      // 安全時盲喝未鑑定草藥（這正是 GDD 設計的正確玩法）
      if(p.hp===p.mhp){
        const unk = p.inv.find(i=>i.cat==='herb' && !G.known['herb/'+i.id]);
        if(unk){ api.useItem(unk,false); api.endTurn(); stats.used++; t++; continue; }
      }
      // 相鄰有怪就打
      let hit = false;
      for(const d of api.DIRS){
        const m = api.monAt(p.x+d[0], p.y+d[1]);
        if(m && api.cornerOK(p.x,p.y,p.x+d[0],p.y+d[1])){ api.tryMove(d[0],d[1]); hit=true; break; }
      }
      if(hit){ t++; continue; }
      // 腳下有東西就撿
      const k = api.key(p.x,p.y);
      if(G.items[k] && p.inv.length < 20){
        p.inv.push(G.items[k]); delete G.items[k]; api.endTurn(); stats.items++; t++; continue;
      }
      // 樓梯就下樓
      if(api.tileAt(p.x,p.y)===api.DOWN){ api.descend(); t++; continue; }
      // 否則走向最近的道具或樓梯
      let goal = G.f.stairs;
      if(p.inv.length < 20){
        let best=null, bd=1e9;
        for(const ik in G.items){
          const ix = ik%api.MW, iy = (ik/api.MW)|0;
          const dd = Math.max(Math.abs(ix-p.x), Math.abs(iy-p.y));
          if(dd < bd){ bd=dd; best={x:ix,y:iy}; }
        }
        if(best) goal = best;
      }
      const step = nextStep(G, {x:p.x,y:p.y}, goal);
      if(!step){ api.endTurn(); t++; continue; }
      api.tryMove(step[0], step[1]);
      t++;
    }
    stats.turns += t;
    stats.floors += G.depth;
    stats.maxFloor = Math.max(stats.maxFloor, G.depth);
    stats.lv += G.p.lv;
    stats.ident += Object.keys(G.known).length;
    if(G.over){ stats.deaths++; if(G.p.sat<=0) stats.starve++; }
  }catch(e){
    stats.errs++;
    console.log('  ✗ 第 %d 場拋出例外：%s', r, e.message);
    console.log(e.stack.split('\n').slice(1,4).join('\n'));
  }
}

const n = RUNS;
console.log('=== 瀏覽器版模擬（%d 場）===\n', n);
console.log('執行期錯誤    : %d', stats.errs);
console.log('死亡          : %d（%s%%）', stats.deaths, (100*stats.deaths/n).toFixed(1));
console.log('  └ 餓死      : %d（%s%%）', stats.starve, (100*stats.starve/n).toFixed(1));
console.log('平均存活回合  : %s', (stats.turns/n).toFixed(0));
console.log('平均到達樓層  : %s（最深 %d）', (stats.floors/n).toFixed(1), stats.maxFloor);
console.log('平均結束等級  : %s', (stats.lv/n).toFixed(1));
console.log('平均鑑定種類  : %s', (stats.ident/n).toFixed(1));
console.log('撿取 %d 件　使用 %d 件', stats.items, stats.used);
process.exit(stats.errs > 0 ? 1 : 0);
