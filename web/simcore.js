// 共用的無頭執行環境：把瀏覽器 DOM 打樁，再從 index.html 挖出遊戲腳本來跑。
//
// 抽成一支的理由跟當初不另外維護 game.js 一樣：sim.js 與 campaign.js
// 各自複製一份打樁，遲早會有一份跟不上 index.html 的改動，
// 而「跟不上的測試」比沒有測試更危險 —— 它會給你一個安心的綠燈。
const fs = require('fs');

function fakeCtx(){
  const noop = () => {};
  return new Proxy({}, {
    get(t, k){
      if(k === 'createRadialGradient' || k === 'createLinearGradient')
        return () => ({ addColorStop: noop });
      if(k === 'createPattern') return () => ({});
      if(k === 'canvas') return { width: 320, height: 240 };
      // 精靈生成會讀寫像素。回傳真的 buffer，頭目描邊那條路徑才跑得到 ——
      // 讓它回 undefined 的話，等於整個美術層都沒被測到。
      if(k === 'getImageData' || k === 'createImageData')
        return (a, b, w, h) => ({ data: new Uint8ClampedArray(4 * ((w||16) * (h||16))),
                                  width: w||16, height: h||16 });
      return t[k] !== undefined ? t[k] : noop;
    },
    set(t, k, v){ t[k] = v; return true; }
  });
}
function fakeEl(){
  return {
    style:{ setProperty(){}, removeProperty(){}, getPropertyValue(){ return ''; } },
    dataset:{},
    classList:{ add:()=>{}, remove:()=>{}, toggle:()=>false, contains:()=>false },
    children:[], firstElementChild:{ style:{} },
    width:0, height:0, textContent:'', innerHTML:'', className:'', disabled:false,
    getContext: fakeCtx,
    appendChild(c){ this.children.push(c); return c; },
    addEventListener(){}, onclick:null, focus(){},
    querySelectorAll(){ return []; }, querySelector(){ return null; },
    closest(){ return null; }, setPointerCapture(){},
    getBoundingClientRect(){ return {top:0,left:0,right:0,bottom:0,width:320,height:240}; },
  };
}
global.document = {
  getElementById: () => fakeEl(),
  createElement: () => fakeEl(),
  querySelectorAll: () => [],
  querySelector: () => null,
  addEventListener: () => {},
  documentElement: { lang: '', style:{}, scrollWidth:1280, scrollHeight:900 },
};
global.addEventListener = () => {};
// 視窗尺寸：遊戲會依螢幕方向切換視野格數，打樁成一般桌機尺寸
global.innerWidth = 1280;
global.innerHeight = 900;
global.getComputedStyle = () => ({ paddingBottom: '0px' });
// 記憶體版的 localStorage：存檔測試需要它，而且它必須真的能存能刪。
// 沒有這一段的話，saveRun() 會被 try/catch 吞掉，測試永遠是綠的。
const __store = new Map();
global.localStorage = {
  getItem: k => (__store.has(k) ? __store.get(k) : null),
  setItem: (k, v) => { __store.set(k, String(v)); },
  removeItem: k => { __store.delete(k); },
  clear: () => __store.clear(),
};
global.requestAnimationFrame = () => {};
global.prompt = () => null;

const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const m = html.match(/<script>\n"use strict";([\s\S]*)<\/script>/);
if(!m){ console.error('index.html 裡找不到遊戲腳本'); process.exit(2); }

eval(m[1] + '\n;globalThis.__api = {' +
  'G:()=>G, VILLAGE:()=>VILLAGE, newGame, tryMove, endTurn, descend, useItem,' +
  'DIRS, key, walkable, monAt, nameOf, pAtk, pDef, cornerOK, MW, MH, WALL, DOWN,' +
  'tileAt, rollItem, mk, WEAP, SHLD, ACTS, BOSS, absDepth, actAt, bossById,' +
  'HAT, OPEN_HAT, ABIL, jobLv, jobRank, abilCost, hatHere, restStep, dwellCheck,' +
  'buildFloor, THEME_SHAPE, ACT_THEME, MONS, death, attack, spawnMon, fireWand, act, BGM,' +
  'bossStats, bossLive, lvMul, overLv, mk, hurtWide, knockPlayer,' +
  'hookSay, saveRun, loadedRun, clearRun, resumeRun, stepOn,' +
  'SKINS, BLOB_SKINS, refreshHero, saveVillage, loadVillage, atlas:()=>atlas,' +
  'POT, potPut, potTake, stashPots, throwItem, sellPrice, clearAct, leaveDungeon, removeItem,' +
  'VILLAGE_STOCK, stockNow, defOf, HALL_FROM, forgeCost, REFINE, refine, schFull, fireTurret, arenaTick, kill, hurtMon, bossWatch, vision,' +
  'i18n:{setLang, LANG:()=>LANG, TX, M, locName, locJob, locAbil, locSpell, locSpellD, locSummon, locAct,' +
  ' locPassive, MASTER_PASSIVE,' +
  ' MONS, BOSS, HAT, ABIL, ABIL_T, SPELLS, SUMMONS, SCHOOLS, ACTS, LOOK, DICT,' +
  ' ITEM_TABLES:[["herb",HERB],["scroll",SCROLL],["wand",WAND],["pot",POT],' +
  ' ["food",FOOD],["weap",WEAP],["shld",SHLD]]}' +
  '};');
const api = globalThis.__api;

// BFS 尋路，規則與實際移動一致（8 向 + 牆角規則）
api.nextStep = function(G, from, goal){
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
};

module.exports = { api };
