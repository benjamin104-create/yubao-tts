// 玩家受傷回歸測試：攻擊有播動畫，不代表 HP 真的有留下來。
//
// 這支專門擋兩種曾經讓玩家看起來無敵的組合：
//   1. 忍者 Master 把陷阱整個吃掉，踩上去完全不扣血。
//   2. 高防禦把怪物傷害壓成 1，白魔導士 Master 又在同一回合補回 1。
// 兩者都不會丟例外，只有實際比較回合前後 HP 才抓得到。
const { api } = require('./simcore.js');
const assert = require('assert');

let pass = 0, fail = 0;
function t(name, fn){
  try { fn(); console.log('✓ ' + name); pass++; }
  catch(e){ console.log('✗ ' + name + '\n    ' + e.message); fail++; }
}

const V = () => api.VILLAGE();
function resetProgress(){
  V().jobs = {};
  V().defBonus = 0;
  V().hpBonus = 0;
}

t('一般傷害陷阱會立即扣除 HP', ()=>{
  resetProgress();
  api.newGame(24081);
  const G = api.G(), p = G.p, before = p.hp;
  G.mons.length = 0;
  G.traps[api.key(p.x,p.y)] = 1;
  api.stepOn();
  assert(p.hp < before, `陷阱前後仍是 ${before}/${p.hp}`);
  assert(!G.traps[api.key(p.x,p.y)], '觸發後陷阱應該消失');
});

t('忍者 Master 只讓陷阱減傷，不會完全免疫', ()=>{
  resetProgress();
  V().jobs.nin = {lv:3, prog:0};
  api.newGame(24082);
  const G = api.G(), p = G.p;
  G.mons.length = 0;
  p.mhp = p.hp = 80;
  G.traps[api.key(p.x,p.y)] = 1;
  api.stepOn();
  assert.strictEqual(p.hp, 75, '80 上限的普通陷阱，忍者減半後應扣 5 點');
});

t('高防禦與白魔導士 Master 也不能在受擊回合把傷害補掉', ()=>{
  resetProgress();
  V().jobs.wht = {lv:3, prog:0};
  V().defBonus = 40;
  api.newGame(24083);
  const G = api.G(), p = G.p;
  G.mons.length = 0;
  p.mhp = p.hp = 400;
  const d = api.DIRS.find(([dx,dy]) => api.walkable(p.x+dx,p.y+dy));
  assert(d, '玩家旁邊需要一格可走地板');
  api.spawnMon(api.MONS.find(m=>m.id==='rat'), p.x+d[0], p.y+d[1]);
  const oldI = G.rng.i;
  G.rng.i = ()=>1;                    // 命中率檢定固定成功
  api.endTurn();
  G.rng.i = oldI;
  assert(p.hp < p.mhp, `怪物命中後仍是滿血 ${p.hp}/${p.mhp}`);
  assert.strictEqual(p.hp, 399, '高防禦後的 1 點傷害應保留到畫面更新');
});

t('沒有受傷的回合仍會正常自然回復', ()=>{
  resetProgress();
  V().jobs.wht = {lv:3, prog:0};
  api.newGame(24084);
  const G = api.G(), p = G.p;
  G.mons.length = 0;
  p.mhp = 400; p.hp = 390; p.regen = 0;
  api.endTurn();
  assert(p.hp > 390, '修正不能把白魔導士的自然回復整個關掉');
});

resetProgress();
console.log('\n受傷檢查：通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
