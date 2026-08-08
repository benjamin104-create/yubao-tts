// 新道具的功能測試：資料表加了欄位，不代表程式真的讀它。
//
// 這一支存在的理由，是死亡復活那條路徑上真的踩過的坑：
// HERB 表上早就有 `revive:1`，但 death() 裡寫的是 `i.id === 'rev'` ——
// 於是「世界樹之葉」加進表裡完全沒有效果，而且不會報任何錯。
// 沉默的失效比崩潰難抓，所以每一個有特殊效果的道具都要有一條斷言。
const { api } = require('./simcore.js');
const assert = require('assert');

const V = api.VILLAGE();
let pass = 0, fail = 0;
function t(name, fn){
  try { fn(); console.log('✓ ' + name); pass++; }
  catch(e){ console.log('✗ ' + name + '\n    ' + e.message); fail++; }
}

// ── 世界樹之葉：倒下時自動用掉，而且回滿 ────────────────────
t('世界樹之葉在死亡時自動復活，且體力全滿', ()=>{
  V.act = 0; V.feather = 0;
  api.newGame(4242);
  const G = api.G(), p = G.p;
  p.inv.push(api.mk('herb', 'ygg', {known:1}));
  const before = p.inv.length;
  p.hp = 0;
  api.death();
  assert(!G.over, '應該沒有真的死掉');
  assert.strictEqual(p.hp, p.mhp, '體力應該回滿，實際 ' + p.hp + '/' + p.mhp);
  assert.strictEqual(p.inv.length, before - 1, '葉子應該被消耗掉');
});

t('身上同時有復活草與世界樹之葉時，先用比較好的那一片', ()=>{
  V.act = 0; V.feather = 0;
  api.newGame(4243);
  const G = api.G(), p = G.p;
  p.inv.push(api.mk('herb', 'rev', {known:1}));
  p.inv.push(api.mk('herb', 'ygg', {known:1}));
  p.hp = 0;
  api.death();
  assert(p.inv.some(i => i.id === 'rev'), '復活草應該還在');
  assert(!p.inv.some(i => i.id === 'ygg'), '世界樹之葉應該被用掉');
});

// ── 屠龍刀：對大型獸與頭目才吃得到倍率 ───────────────────────
t('屠龍刀對頭目的傷害明顯高於秘銀之劍', ()=>{
  const dmg = (wid)=>{
    V.act = 0;
    api.newGame(777);
    const G = api.G(), p = G.p;
    p.lv = 20; p.weap = api.mk('weap', wid, {known:1});
    const bd = api.bossById('b_warden');
    const spot = { x: p.x + 1, y: p.y };
    G.mons.length = 0;
    api.spawnMon(bd, spot.x, spot.y);
    const m = G.mons[0];
    m.hp = m.mhp = 99999;               // 打不死，才量得到單次傷害
    let tot = 0;
    for(let i=0;i<400;i++){ const h0 = m.hp; api.attack(m); tot += h0 - m.hp; }
    return tot / 400;
  };
  const mith = dmg('mith'), drgn = dmg('drgn');
  assert(drgn > mith * 1.05,
    '屠龍刀 ' + drgn.toFixed(1) + ' 應該高於秘銀 ' + mith.toFixed(1));
});

t('屠龍刀對小型怪沒有倍率（所以換上去不是無腦升級）', ()=>{
  const dmg = (wid)=>{
    V.act = 0;
    api.newGame(778);
    const G = api.G(), p = G.p;
    p.lv = 20; p.weap = api.mk('weap', wid, {known:1});
    G.mons.length = 0;
    api.spawnMon(api.MONS.find(m=>m.id==='rat'), p.x + 1, p.y);
    const m = G.mons[0];
    m.hp = m.mhp = 99999;
    let tot = 0;
    for(let i=0;i<400;i++){ const h0 = m.hp; api.attack(m); tot += h0 - m.hp; }
    return tot / 400;
  };
  assert(dmg('mith') > dmg('drgn'), '對老鼠，秘銀應該比屠龍刀強');
});

// ── 天空之劍：橫掃所有相鄰的敵人 ─────────────────────────────
t('天空之劍會同時打到其他相鄰的敵人', ()=>{
  V.act = 0;
  api.newGame(999);
  const G = api.G(), p = G.p;
  p.lv = 20; p.weap = api.mk('weap', 'sky', {known:1});
  G.mons.length = 0;
  // 在玩家四周擺三隻，只打其中一隻
  const spots = api.DIRS.filter(d => api.walkable(p.x+d[0], p.y+d[1])).slice(0, 3);
  assert(spots.length >= 2, '需要至少兩格空地才測得起來');
  for(const d of spots) api.spawnMon(api.MONS.find(m=>m.id==='golem'), p.x+d[0], p.y+d[1]);
  for(const m of G.mons){ m.hp = m.mhp = 99999; }
  const other = G.mons[1];
  const before = other.hp;
  api.attack(G.mons[0]);
  assert(other.hp < before, '旁邊那一隻也應該掉血（掃到了）');
});

// ── 熔岩杖：把牆熔成通道，而且永遠不會挖穿地圖邊界 ───────────
t('熔岩杖把牆熔成可走的格子', ()=>{
  V.act = 0;
  api.newGame(1234);
  const G = api.G(), p = G.p;
  // 找一個「面前是牆」的方向
  let dir = null;
  for(const d of api.DIRS){
    if(d[0] && d[1]) continue;                        // 只試四個正方向
    const nx = p.x + d[0], ny = p.y + d[1];
    if(nx > 1 && ny > 1 && nx < api.MW-2 && ny < api.MH-2 && !api.walkable(nx, ny)){ dir = d; break; }
  }
  if(!dir){ console.log('    （這顆種子四周沒有牆，跳過）'); return; }
  const it = api.mk('wand', 'lava', {known:1});
  p.inv.push(it);
  api.useItem(it, false);                             // 進入瞄準狀態
  api.fireWand(dir[0], dir[1]);
  assert(api.walkable(p.x + dir[0], p.y + dir[1]), '面前那一格應該被熔開了');
});

t('熔岩杖挖不穿地圖最外一圈', ()=>{
  V.act = 0;
  api.newGame(1235);
  const G = api.G(), p = G.p;
  const it = api.mk('wand', 'lava', {known:1});
  p.inv.push(it);
  // 從各個方向各掃一次，然後檢查邊界完好
  for(const d of api.DIRS){
    it.uses = 9;
    api.useItem(it, false);
    api.fireWand(d[0], d[1]);
  }
  for(let i=0;i<api.MW;i++){
    assert.strictEqual(G.f.t[api.key(i,0)], api.WALL, '上邊界破了 x=' + i);
    assert.strictEqual(G.f.t[api.key(i,api.MH-1)], api.WALL, '下邊界破了 x=' + i);
    assert.strictEqual(G.f.t[api.key(0,i)], api.WALL, '左邊界破了 y=' + i);
    assert.strictEqual(G.f.t[api.key(api.MW-1,i)], api.WALL, '右邊界破了 y=' + i);
  }
});

// ── 影忍的分身之術 ───────────────────────────────────────────
t('影忍挨打之後會分出只有 1 點體力的分身', ()=>{
  V.act = 0;
  let cloned = false;
  for(let s=0; s<40 && !cloned; s++){
    api.newGame(5000 + s);
    const G = api.G(), p = G.p;
    p.lv = 5;                                         // 打不死牠才分得出來
    G.mons.length = 0;
    const d = api.MONS.find(m=>m.id==='shinobi');
    const sp = api.DIRS.find(dd => api.walkable(p.x+dd[0], p.y+dd[1]));
    if(!sp) continue;
    api.spawnMon(d, p.x+sp[0], p.y+sp[1]);
    const m = G.mons[0];
    m.hp = m.mhp = 99999;
    for(let i=0;i<12 && !cloned;i++){
      api.attack(m);
      cloned = G.mons.some(x => x.isClone);
    }
    if(cloned) assert.strictEqual(G.mons.find(x=>x.isClone).hp, 1, '分身應該只有 1 點體力');
  }
  assert(cloned, '打了幾十次都沒有分身 —— clone 沒有生效');
});

// ── 影法師：傷害跟著玩家的攻擊力走 ───────────────────────────
t('影法師的傷害會跟著玩家的攻擊力變高', ()=>{
  const dmg = (lv, weap)=>{
    V.act = 0;
    api.newGame(6060);
    const G = api.G(), p = G.p;
    p.lv = lv; p.weap = weap ? api.mk('weap', weap, {known:1}) : null;
    p.hp = p.mhp = 999999; p.st = {};
    G.mons.length = 0;
    const sp = api.DIRS.find(dd => api.walkable(p.x+dd[0], p.y+dd[1]));
    api.spawnMon(api.MONS.find(m=>m.id==='shadow'), p.x+sp[0], p.y+sp[1]);
    const m = G.mons[0];
    let tot = 0;
    for(let i=0;i<300;i++){ const h0 = p.hp; api.act(m, {k:'melee'}); tot += h0 - p.hp; }
    return tot / 300;
  };
  const weak = dmg(1, null), strong = dmg(24, 'sky');
  assert(strong > weak * 1.4,
    '裝備好了影子應該更痛：' + weak.toFixed(1) + ' → ' + strong.toFixed(1));
});

console.log('\n通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
