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
/* QA 快速入口會讀 location.search。預設為空 —— 無頭測試等同一般遊戲入口。
   QA_SEARCH 環境變數可以把它換掉，因為「驗收網址不准動玩家存檔」這件事
   只有在 QA_MODE 為真的時候才測得到，而 QA_MODE 是在腳本載入的當下
   從 location.search 算出來的常數，事後改不了。 */
global.location = { search: process.env.QA_SEARCH || '',
                    href:'http://localhost/game/' };
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
const m = html.match(/<script>\r?\n"use strict";([\s\S]*)<\/script>/);
if(!m){ console.error('index.html 裡找不到遊戲腳本'); process.exit(2); }

eval(m[1] + '\n;globalThis.__api = {' +
  'G:()=>G, VILLAGE:()=>VILLAGE, newGame, tryMove, endTurn, descend, useItem,' +
  'DIRS, key, walkable, monAt, nameOf, pAtk, pDef, cornerOK, MW, MH, WALL, DOWN,' +
  'tileAt, rollItem, mk, WEAP, SHLD, ACTS, BOSS, absDepth, actAt, bossById,' +
  'HAT, OPEN_HAT, ABIL, jobLv, jobRank, abilCost, spellCost, maxMp, floorLabel, actUp, mk, healNpc, hatHere, restStep, dwellCheck,' +
  'buildFloor, THEME_SHAPE, ACT_THEME, iceRoughAt, iceSlickAt, iceMoveTarget, MONS, death, attack, spawnMon, fireWand, act, BGM,' +
  'bossStats, bossLive, lvMul, overLv, mk, hurtWide, knockPlayer,' +
  'hookSay, saveRun, loadedRun, clearRun, resumeRun, stepOn,' +
  'SKINS, BLOB_SKINS, refreshHero, saveVillage, loadVillage, atlas:()=>atlas,' +
  'villageStyle, VSTYLES, VNAME, VPAL, VILLAGE_SCENE_SPEC, migrateAct, VILLAGE_VER, RUN_VER,' +
  'talkOpen, answerTalk, askVillager, npcStep,' +
  'evOK, makeEvent, rubbleAt, digMason, stoneStep, evStep, giveCirclet,' +
  'EV_RATE, MASON_DIG, STONE_ELS, ULT_RUNS, ULT_IDS, REGEN_TURNS, needExp,' +
  'THEMES, PAL,' +
  'crispCssWidth, crispPortraitGrid, FIELD_ZOOM,' +
  'POT, potPut, potTake, stashPots, throwItem, sellPrice, clearAct, leaveDungeon, removeItem,' +
  'VILLAGE_STOCK, stockNow, defOf, HALL_FROM, forgeCost, REFINE, refine, schFull, fireTurret, arenaTick, kill, hurtMon, bossWatch, vision,' +
  'i18n:{setLang, LANG:()=>LANG, TX, M, locName, locJob, locAbil, locSpell, locSpellD, locSummon, locAct,' +
  ' locPassive, MASTER_PASSIVE,' +
  ' MONS, BOSS, HAT, ABIL, ABIL_T, SPELLS, SUMMONS, SCHOOLS, ACTS, LOOK, DICT,' +
  ' ITEM_TABLES:[["herb",HERB],["scroll",SCROLL],["wand",WAND],["pot",POT],' +
  ' ["food",FOOD],["weap",WEAP],["shld",SHLD]]}' +
  '};');
const api = globalThis.__api;

// BFS 尋路，規則與實際移動一致（8 向 + 牆角規則 + 冰面滑行）
//
// 「按一個方向」與「移動一格」在這款遊戲裡不是同一件事：冰原上直走會滑到
// 第二格。所以 BFS 展開的必須是**實際落點**，回傳的則是按下去的方向。
//
// 舊版把兩者當成同一件事，於是在水晶礦坑整個失效：它規劃一步、遊戲滑兩步，
// 從新的位置規劃回來的那一步又滑回原地 —— 完美的來回。
// 實測（種子 122～131）：機器人在一樓兩格之間各站了一千三百多回合，
// 三千回合後餓死，一樓總共只踏到六格；而樓梯全程都是走得到的。
// 走通測試因此回報「第 13 章死亡 40 次」，看起來像數值太難，
// 真正的原因是**測試自己不會走路**。
//
// 斜走不會滑（遊戲刻意保留的微調手段），所以照實際規則展開之後路一定找得到。
api.nextStep = function(G, from, goal){
  if(from.x===goal.x && from.y===goal.y) return null;
  const came = new Map([[api.key(from.x,from.y), null]]);
  const q = [{x:from.x, y:from.y}]; let h = 0;
  while(h < q.length){
    const cur = q[h++];
    for(const d of api.DIRS){
      const ax = cur.x+d[0], ay = cur.y+d[1];
      if(!api.walkable(ax,ay) || !api.cornerOK(cur.x,cur.y,ax,ay)) continue;
      // 落點用遊戲自己的函式算。ignoreActors=true：規劃路線時不必管
      // 這一刻誰站在哪，怪物下一回合就不在那裡了。
      const lz = api.iceMoveTarget(cur.x, cur.y, d[0], d[1], true);
      const nx = lz.x, ny = lz.y, k = api.key(nx,ny);
      if(came.has(k) || !api.walkable(nx,ny)) continue;
      came.set(k, {p:cur, d:d});
      if(nx===goal.x && ny===goal.y){
        let node = {x:nx, y:ny};
        while(true){
          const par = came.get(api.key(node.x,node.y));
          if(!par) break;
          if(par.p.x===from.x && par.p.y===from.y) return par.d;
          node = par.p;
        }
        return null;
      }
      q.push({x:nx,y:ny});
    }
  }
  return null;
};

module.exports = { api };
