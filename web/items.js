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


// ── 長槍：刺穿後面那一隻 ────────────────────────────────────
// 這個欄位在表上寫了很久，程式裡一次都沒讀過 —— 也就是說長槍花 1600 G
// 買到的只有「攻擊力比鋼之劍低」。沉默失效的欄位就是這樣長出來的。
t('長槍會連同後面那一隻一起刺穿，普通劍不會', ()=>{
  const twoInLine = (weap) => {
    V.act = 0; api.newGame(4242);
    const G = api.G(), p = G.p;
    p.hp = p.mhp = 99999; G.mons.length = 0;
    p.weap = api.mk('weap', weap, {known:1}); p.inv.push(p.weap);
    const d = api.DIRS.find(dd => api.walkable(p.x+dd[0], p.y+dd[1])
                               && api.walkable(p.x+dd[0]*2, p.y+dd[1]*2));
    assert(d, '這顆種子找不到連續兩格的方向');
    const rat = api.MONS.find(m => m.id === 'rat');
    const a = api.spawnMon(rat, p.x+d[0],   p.y+d[1]);
    const b = api.spawnMon(rat, p.x+d[0]*2, p.y+d[1]*2);
    a.hp = a.mhp = 99999; b.hp = b.mhp = 99999;
    api.attack(a);
    return {front: 99999 - a.hp, back: 99999 - b.hp};
  };
  const spear = twoInLine('spear'), steel = twoInLine('steel');
  assert(spear.front > 0, '長槍該打中前面那一隻');
  assert(spear.back > 0, '長槍該刺穿到後面那一隻，實際 ' + spear.back);
  assert.strictEqual(steel.back, 0, '一般的劍不該打到後面那一隻');
});

// ── 鏡之盾：彈回遠程攻擊 ────────────────────────────────────
t('鏡之盾把遠程攻擊彈回去，木盾不會', ()=>{
  const shot = (shld) => {
    V.act = 0; api.newGame(5150);
    const G = api.G(), p = G.p;
    p.hp = p.mhp = 99999; p.st = {}; G.mons.length = 0;
    p.shld = api.mk('shld', shld, {known:1}); p.inv.push(p.shld);
    const gz = api.MONS.find(m => m.rng);                    // 隨便一隻會射的怪
    const d = api.DIRS.find(dd => api.walkable(p.x+dd[0]*2, p.y+dd[1]*2));
    const m = api.spawnMon(gz, p.x+d[0]*2, p.y+d[1]*2);
    m.hp = m.mhp = 99999;
    api.act(m, {k:'shoot'});
    return {me: 99999 - p.hp, them: 99999 - m.hp};
  };
  const mirr = shot('mirr'), wood = shot('wood');
  assert(mirr.them > 0, '鏡之盾該把傷害彈回去，實際 ' + mirr.them);
  assert.strictEqual(mirr.me, 0, '彈回去的那一下不該同時打到自己');
  assert.strictEqual(wood.them, 0, '木盾不該彈任何東西');
  assert(wood.me > 0, '木盾擋不住，該受傷');
});

// ── 壺 ──────────────────────────────────────────────────────
// 這四個是使用者親口回報的那個坑：「壺的作用是什麼？只是撿起沒作用很怪吧？」
// 表上有 beh 欄位，程式裡一次都沒有讀 —— 撿起來就只是一個佔格子的圖示。
const potOf = (id, cap) => { const it = api.mk('pot', id); it.cap = cap; return it; };

t('保存壺裝得進東西，而且裝進去就不佔背包格', ()=>{
  V.act = 0; V.pots = [];
  api.newGame(9001);
  const p = api.G().p;
  const pot = potOf('store', 4); p.inv.push(pot);
  const h = api.mk('herb', 'heal', {known:1}); p.inv.push(h);
  const n0 = p.inv.length;
  assert(api.potPut(pot, h), '應該放得進去');
  assert.strictEqual(p.inv.length, n0 - 1, '放進壺裡就該離開背包');
  assert.strictEqual(pot.contents.length, 1, '壺裡應該有一件');
  assert(api.potTake(pot, 0), '應該拿得出來');
  assert.strictEqual(p.inv.length, n0, '拿出來就該回到背包');
});

t('壺裝不進另一個壺 —— 不然裡面的東西會憑空消失', ()=>{
  V.act = 0; api.newGame(9002);
  const p = api.G().p;
  const a = potOf('store', 4), b = potOf('store', 4);
  p.inv.push(a, b);
  assert(!api.potPut(a, b), '壺不該裝得進壺');
  assert.strictEqual(a.contents.length, 0, '什麼都不該進去');
  assert(p.inv.includes(b), '另一個壺應該還在背包裡');
});

t('保存壺裡的東西跟著走到下一座迷宮，沒放進去的不會', ()=>{
  V.act = 0; V.pots = [];
  api.newGame(9003);
  const p = api.G().p;
  const pot = potOf('store', 4); p.inv.push(pot);
  const inside = api.mk('weap', 'steel', {known:1, up:2});
  const outside = api.mk('weap', 'brnz', {known:1});
  p.inv.push(inside, outside);
  api.potPut(pot, inside);
  api.stashPots();
  V.act = 1;
  api.newGame(9004);
  const inv = api.G().p.inv;
  const pot2 = inv.find(i => i.cat === 'pot');
  assert(pot2, '保存壺應該跟著下來了');
  assert.strictEqual(pot2.contents.length, 1, '壺裡的東西應該還在');
  assert.strictEqual(pot2.contents[0].id, 'steel', '應該是收進去的那一把');
  assert.strictEqual(pot2.contents[0].up, 2, '強化值應該保留');
  assert(!inv.some(i => i.id === 'brnz'), '沒放進壺裡的東西不該跟著來');
});

t('識別壺／破魔壺／吸物壺各自做該做的事，用完就裂', ()=>{
  V.act = 0; api.newGame(9005);
  const G = api.G(), p = G.p;
  // 識別
  const ip = potOf('ident', 2); p.inv.push(ip);
  const unk = api.mk('herb', 'psn'); p.inv.push(unk);
  assert(!G.known['herb/psn'], '一開始應該是未鑑定的');
  api.potPut(ip, unk);
  assert(G.known['herb/psn'], '放進識別壺就該認得出來');
  assert.strictEqual(ip.cap, 1, '應該用掉一次');
  // 破魔
  const dp = potOf('dispel', 1); p.inv.push(dp);
  const cursed = api.mk('weap', 'club', {known:1, cursed:true}); p.inv.push(cursed);
  api.potPut(dp, cursed);
  assert(!cursed.cursed, '詛咒應該被洗掉');
  assert(!p.inv.includes(dp), '用完最後一次，壺應該裂掉消失');
  // 吸物
  const vp = potOf('devour', 3); p.inv.push(vp);
  const food = api.mk('food', 'bread'); p.inv.push(food);
  api.potPut(vp, food);
  assert(!p.inv.includes(food), '吸物壺應該把東西吞掉');
});

t('壺丟出去會碎掉消失，裡面的東西撒在地上', ()=>{
  V.act = 0; api.newGame(9006);
  const G = api.G(), p = G.p;
  const pot = potOf('store', 4); p.inv.push(pot);
  const h = api.mk('herb', 'heal', {known:1}); p.inv.push(h);
  api.potPut(pot, h);
  G.items = {};
  const d = api.DIRS.find(dd => api.walkable(p.x+dd[0], p.y+dd[1]));
  api.removeItem ? api.removeItem(pot) : (p.inv = p.inv.filter(i => i !== pot));
  api.throwItem(pot, d[0], d[1]);
  const onGround = Object.values(G.items);
  assert(!onGround.some(i => i.cat === 'pot'), '壺不該落地 —— 它碎了');
  assert(!p.inv.includes(pot), '壺不該還在背包裡');
  assert(onGround.some(i => i.id === 'heal'), '裡面的東西應該撒在地上');
});

// ── 怪物之間 ────────────────────────────────────────────────
t('怪物之間是一間大廳、有怪、而且不會生在出生的房間', ()=>{
  V.act = 0; V.pots = [];
  let found = 0;
  for(let a = 0; a < api.ACTS.length && found < 6; a++){
    for(let s = 0; s < 40 && found < 6; s++){
      V.act = a; api.newGame(31000 + s * 13);
      const G = api.G();
      for(let f = 1; f <= api.ACTS[a].floors && found < 6; f++){
        G.floor = f; api.buildFloor();
        if(!G.f.hall) continue;
        found++;
        const r = G.f.rooms[G.f.hall.room];
        assert(r, '大廳應該對應得到一個房間');
        assert(r.w * r.h >= 49, '大廳應該真的很大，實際 ' + r.w + 'x' + r.h);
        const spawnRoom = G.f.roomAt[api.key(G.p.x, G.p.y)];
        assert.notStrictEqual(G.f.hall.room, spawnRoom,
          '一落地就站在怪物之間裡等於判死刑');
        const inside = G.mons.filter(m =>
          G.f.roomAt[api.key(m.x, m.y)] === G.f.hall.room);
        assert(inside.length >= 4, '大廳裡應該真的有一群怪，實際 ' + inside.length);
        assert(inside.length <= 12, '密度不該噁心到故意讓玩家失敗，實際 ' + inside.length);
      }
    }
  }
  assert(found >= 3, '四十顆種子裡至少該遇到幾次怪物之間，實際 ' + found);
});

t('第一章不會出現怪物之間 —— 那一章還在教怎麼玩', ()=>{
  V.act = 0;
  for(let s = 0; s < 60; s++){
    api.newGame(41000 + s * 7);
    const G = api.G();
    for(let f = 1; f <= api.ACTS[0].floors; f++){
      G.floor = f; api.buildFloor();
      assert(!G.f.hall, '第 ' + f + ' 層不該有怪物之間');
    }
  }
});

// ── 職業帽 ──────────────────────────────────────────────────
// 使用者回報：「每一個章節都沒有撿到帽子，所以好像也無法測試職業技能」。
// 查出來是真的 —— 舊的放置邏輯是照「絕對深度每 20 層」切段，
// 那是為一座連續的 20 層地牢寫的，可是戰役把深度切成十五章、
// 每章各自 newGame()。量出來第 3、4、9、15 章二十趟一頂都沒有。
// 九個職業、技能欄、Master 被動，整套系統對玩家等於不存在，而且不報錯。
t('每一章都撿得到職業帽（最後的競技場除外）', ()=>{
  V.pots = [];
  for(let a = 0; a < api.ACTS.length; a++){
    const act = api.ACTS[a];
    if(act.id === 'chaos') continue;            // 最終競技場刻意清空場地
    for(let s = 0; s < 8; s++){
      V.act = a; V.stock = [];
      api.newGame(90000 + s * 811);
      const G = api.G();
      let hats = 0;
      for(let f = 1; f <= act.floors; f++){
        G.floor = f; api.buildFloor();
        hats += Object.values(G.items).filter(i => i.cat === 'hat').length;
      }
      assert(hats >= 1, '第 ' + (a+1) + ' 章「' + act.nm + '」種子 ' + s + ' 一頂帽子都沒有');
      assert(hats <= 2, '第 ' + (a+1) + ' 章一趟出現 ' + hats + ' 頂 —— 帽子該是招牌，不是配件');
    }
  }
});

t('淺章節只掉得到公開職業，隱藏職業要更深才進池子', ()=>{
  const hidden = api.HAT.filter(h => !api.OPEN_HAT.includes(h)).map(h => h.id);
  assert(hidden.length, '應該有隱藏職業');
  V.act = 0; V.stock = []; V.pots = [];
  for(let s = 0; s < 20; s++){
    api.newGame(12000 + s * 37);
    const G = api.G();
    for(let f = 1; f <= api.ACTS[0].floors; f++){
      G.floor = f; api.buildFloor();
      for(const it of Object.values(G.items))
        if(it.cat === 'hat')
          assert(!hidden.includes(it.id), '第一章不該掉隱藏職業的帽子：' + it.id);
    }
  }
});

// ── 有害道具的收購價 ────────────────────────────────────────
t('店員認得出來的爛東西只給四分之一，認不出來的照樣全價', ()=>{
  V.act = 0; api.newGame(9007);
  const G = api.G();
  const psn = api.mk('herb', 'psn'), heal = api.mk('herb', 'heal');
  delete G.known['herb/psn']; delete G.known['herb/heal'];
  const blind = api.sellPrice(psn);
  G.known['herb/psn'] = 1; G.known['herb/heal'] = 1;
  assert(api.sellPrice(psn) < blind, '鑑定過的毒草應該賣得比較便宜');
  assert.strictEqual(api.sellPrice(heal), Math.round(heal.d.price * 0.5),
    '正常的草還是半價');
});

console.log('\n通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
