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

t('白色箭機關會造成明顯傷害，而不是只有動畫', ()=>{
  resetProgress();
  api.newGame(24085);
  const G = api.G(), p = G.p;
  G.mons.length = 0;
  p.mhp = p.hp = 140;
  G.traps[api.key(p.x,p.y)] = 3;
  api.stepOn();
  assert.strictEqual(p.hp, 120, '140 上限的飛箭陷阱應扣 20 點');
  assert(G.trapFx.some(f=>f.kind==='arrow'), '飛箭陷阱應建立由左側射入的動畫');
});

t('食人草會咬傷並拘束玩家 3～5 個後續回合', ()=>{
  resetProgress();
  api.newGame(24086);
  const G = api.G(), p = G.p;
  G.mons.length = 0;
  p.mhp = p.hp = 140;
  G.traps[api.key(p.x,p.y)] = 4;
  api.stepOn();
  assert(p.hp < 140, '食人草合起時必須先造成傷害');
  assert(p.st['咬'] >= 4 && p.st['咬'] <= 6,
    `觸發當下的拘束計數應為 4～6，實際是 ${p.st['咬']}`);
});

t('強酸會長效腐蝕盾牌 1 點，且存入一般道具欄位', ()=>{
  resetProgress();
  api.newGame(24087);
  const G = api.G(), p = G.p;
  G.mons.length = 0;
  const sh = api.mk('shld','steel',{known:1,up:1});
  p.inv.push(sh); p.shld = sh;
  const before = api.pDef();
  G.traps[api.key(p.x,p.y)] = 5;
  api.stepOn();
  assert.strictEqual(sh.acid, 1, '盾牌必須留下 acid=1 的長效腐蝕值');
  assert.strictEqual(api.pDef(), before-1, '腐蝕後實際防禦必須降低 1 點');
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

t('鋼之盾不能把頭目攻擊壓回 2～3 點', ()=>{
  resetProgress();
  api.newGame(24088);
  const G=api.G(),p=G.p;
  const sh=api.mk('shld','steel',{known:1,up:1}); p.inv.push(sh); p.shld=sh;
  const d=api.BOSS.find(x=>x.id==='b_keeper');
  const m={d:Object.assign({},d,{atk:5})};
  // 固定亂數在傷害區間的最低端，驗的是保底，不是運氣好的高傷。
  const old=G.rng; G.rng=Object.assign(()=>0,{i:old.i,pick:old.pick,chance:old.chance,weight:old.weight,shuffle:old.shuffle});
  const hit=api.rollEnemyDmg(m,5,1,false);
  G.rng=old;
  assert(hit>=4,`鋼盾後頭目仍只造成 ${hit} 點`);
});

resetProgress();
console.log('\n受傷檢查：通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
