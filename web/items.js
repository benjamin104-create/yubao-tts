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

/* ── 怪物跟著等級走 ──────────────────────────────────────────
   使用者的原話：「有些怪物我等於都是秒殺？很沒挑戰性」。
   補正只補「超前的那一段」，所以這裡要驗兩邊：
   等級正常的時候完全不能動（既有的平衡靠這一條保住），
   練過頭的時候要真的變強，而且玩家看得出來。 */
t('等級沒有超前時，怪物的數值一個字都不動', ()=>{
  V.act = 0;
  api.newGame(777);
  const G = api.G();
  G.act = 4; G.floor = 2; api.buildFloor();
  const rat = api.MONS.find(d => d.id === 'rat');
  const m = api.spawnMon(rat, G.p.x, G.p.y);
  assert.strictEqual(m.d.hp, rat.hp, '血量被動了：' + m.d.hp + ' ≠ ' + rat.hp);
  assert.strictEqual(m.d.atk, rat.atk, '攻擊被動了');
  assert.strictEqual(m.d, rat, '沒有補正就不該複製資料表');
});

t('主角練過頭時，同一隻怪會變強，而且名字上看得出來', ()=>{
  V.act = 0;
  api.newGame(778);
  const G = api.G();
  G.act = 4; G.floor = 2; api.buildFloor();
  const rat = api.MONS.find(d => d.id === 'rat');
  const base = api.spawnMon(rat, G.p.x, G.p.y);
  G.p.lv += 12;                                   // 練到明顯超前
  const up = api.spawnMon(rat, G.p.x, G.p.y);
  assert(up.d.hp > base.d.hp, '練了十二級，血量還是 ' + up.d.hp);
  assert(up.d.atk > base.d.atk, '攻擊沒有跟上');
  assert(up.mhp === up.d.hp && up.hp === up.d.hp, '補正沒有寫進實際血量');
  // 補正有天花板 —— 不然練得越久，遊戲越變成看誰的數字大
  G.p.lv += 60;
  const cap = api.spawnMon(rat, G.p.x, G.p.y);
  assert(cap.d.hp <= Math.round(rat.hp * 2.20), '補正沒有上限：' + cap.d.hp);
  // 玩家要看得出來：名字上有記號，而且原本的表沒有被污染
  assert(api.i18n.locName('mon', up.d) !== api.i18n.locName('mon', rat),
         '變強了卻叫同一個名字');
  assert(!rat.lvup, '補正寫回了資料表 —— 下一場遊戲會繼承這個值');
});

/* ── 頭目看著眼前這個玩家配數值 ──────────────────────────────
   使用者的原話：「連小王或是魔王，我根本不會傷到血都可以簡單打贏？
   根本沒有緊張感」。原因是頭目的數值來自一條**估算**玩家的式子，
   而那條式子是從不買裝備、不加點、不施法的機器人回歸出來的。
   這兩條驗的就是：估算對得上的人不受影響，練過頭的人才會被拉。 */
t('一般玩家遇到的頭目跟原本一樣強', ()=>{
  V.act = 0;
  api.newGame(9090);
  const G = api.G();
  G.act = 12; G.floor = 1; api.buildFloor();
  const base = api.bossStats(G.md), live = api.bossLive(G.md);
  assert.strictEqual(live.hp, base.hp, '沒有超前卻被拉了血量');
  assert.strictEqual(live.atk, base.atk, '沒有超前卻被拉了攻擊');
});

t('練過頭的玩家遇到的頭目會跟著變強，但不會無限膨脹', ()=>{
  V.act = 0;
  api.newGame(9091);
  const G = api.G(), p = G.p;
  G.act = 12; G.floor = 1; api.buildFloor();
  const base = api.bossStats(G.md);

  // 一個真的練過的玩家：頂級武器打滿、等級超前、五系全滿
  p.weap = api.mk('weap', 'babel', {known:1, up:5});
  p.shld = api.mk('shld', 'aegis', {known:1, up:4});   // 防禦也要給 ——
  // 頭目的攻擊是照「幾回合打死你」反推的，而那個回合數同時吃體力與防禦。
  // 只加體力不加防禦的玩家在數學上其實沒有變耐打多少。
  p.lv += 15; p.mhp += 150; p.hp = p.mhp;
  p.sch = {heal:5, bolt:5, fire:5, aqua:5, wind:5};
  p.mmp = 300;
  const live = api.bossLive(G.md);
  assert(live.hp  > base.hp  * 1.3, '血量沒有跟上：' + live.hp + ' vs ' + base.hp);
  assert(live.atk > base.atk * 1.3, '攻擊沒有跟上：' + live.atk + ' vs ' + base.atk);
  assert(live.hp  <= base.hp  * 4.0 + 1, '血量沒有天花板：' + live.hp);
  assert(live.atk <= base.atk * 4.0 + 1, '攻擊沒有天花板：' + live.atk);

  // 而且真的用在生出來的那一隻身上 —— 算得對但沒接上是這個專案的老毛病
  const bd = api.BOSS.find(b => !b.mul && !b.turret) || api.BOSS[0];
  const mo = api.spawnMon(bd, p.x, p.y);
  assert(mo.mhp > base.hp * 1.3, '生出來的頭目還是舊數值：' + mo.mhp);
});

/* ── 鏡之女王：瞬移 ──────────────────────────────────────────
   她不走路，她換一面鏡子出現。這一條驗的是三件事：
   真的會閃、閃在同一間房裡走得到的格子、而且不會閃到玩家臉上 ——
   閃到臉上等於一記無法反應的近戰，那不是機關是偷襲。 */
t('鏡之女王會瞬移，落點在同一間房，而且不會閃到臉上', ()=>{
  V.act = 10;
  api.newGame(4242);
  const G = api.G(), p = G.p;
  G.act = 10; G.floor = api.ACTS[10].floors; api.buildFloor();
  const q = G.mons.find(m => m.d.boss);
  assert(q && q.d.blink, '這一層應該有會瞬移的頭目');
  const room = G.f.roomAt[api.key(q.x, q.y)];
  // 站在她房間裡不動，看六十回合
  p.x = q.x + 3; p.y = q.y; api.vision();
  p.hp = p.mhp = 99999;                      // 打不死，才看得完整個週期
  let last = q.x + ',' + q.y, blinks = 0;
  for(let t2 = 0; t2 < 60; t2++){
    api.endTurn();
    const now = q.x + ',' + q.y;
    if(now === last) continue;
    blinks++;
    last = now;
    assert(api.walkable(q.x, q.y), '閃到牆裡了');
    assert.strictEqual(G.f.roomAt[api.key(q.x, q.y)], room, '閃出房間了');
    assert(Math.max(Math.abs(q.x - p.x), Math.abs(q.y - p.y)) >= 3,
           '閃到臉上了 —— 那是偷襲不是機關');
  }
  assert(blinks >= 2, '六十回合只閃了 ' + blinks + ' 次 —— 停留 10~15 回合應該有三到五次');
});

/* ── 站在頭目旁邊不能是安全的 ────────────────────────────────
   使用者回報：「主角根本沒受傷，可能是踩在女王的身體上的原因」。
   查出來是兩個洞疊在一起：
     · 原地不動（still）的預告型頭目，在沒有預告掛著的回合直接 wait ——
       玩家站到她旁邊、又不在她預告的線上，她就一整場什麼都不做。
     · 她是純遠程的，而鏡之盾把所有遠程攻擊原封不動彈回去 ——
       她不但打不到人，還會被自己的攻擊打死。
   兩個都不報錯，而且單看程式碼都很合理。這一條把它們一起釘住。 */
t('站在鏡之女王旁邊會挨打，而且鏡之盾擋不住她', ()=>{
  V.act = 10;
  api.newGame(4242);
  const G = api.G(), p = G.p;
  G.act = 10; G.floor = api.ACTS[10].floors; api.buildFloor();
  const q = G.mons.find(m => m.d.boss);
  assert(q, '這一層應該有頭目');
  p.shld = api.mk('shld', 'mirr', {known:1, up:5});    // 反射盾
  p.inv.push(p.shld);
  p.weap = api.mk('weap', 'mith', {known:1, up:8});
  p.inv.push(p.weap);
  p.lv += 10;                                         // 練過頭的人，也就是回報的那一位
  /* 體力不能開太大。自然回復是「每回合累積 mhp，滿 350 換 1 點」——
     體力上限開到 9999 就是每回合回 28 點，任何傷害都會被回復蓋掉，
     於是這條斷言永遠是綠的。（這是寫這一條的時候真的踩到的。） */
  p.hp = p.mhp = 240;
  const start = p.hp;
  // 貼在她旁邊站著不動 —— 她會瞬移走，跟著她繼續貼
  for(let t2 = 0; t2 < 40; t2++){
    const b = G.mons.find(m => m.d.boss && m.hp > 0);
    if(!b) break;
    const sp = api.DIRS.map(d => ({x:b.x+d[0], y:b.y+d[1]}))
                       .find(o => api.walkable(o.x, o.y) && !api.monAt(o.x, o.y)
                                  && api.cornerOK(o.x, o.y, b.x, b.y));
    if(sp){ p.x = sp.x; p.y = sp.y; api.vision(); }
    api.endTurn();
  }
  assert(p.hp < start - 20,
    '貼著她站了四十回合只掉了 ' + (start - p.hp) + ' 點 —— 那不是機關，是漏洞');
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

// ── 解謎型頭目：砲座 ────────────────────────────────────────
// 使用者要的：「小王普通攻擊無法受傷，要踩到房間裡不同顏色的地磚上按 A，
// 對小王發射，然後這個砲台就失效，需要跑到另一個砲台裝置。」
t('解謎型頭目刀砍不動，只有砲座打得動', ()=>{
  const setup = (act) => {
    V.act = act; V.stock = []; V.pots = [];
    api.newGame(4242);
    const G = api.G();
    G.floor = api.ACTS[act].floors; api.buildFloor();
    return {G, boss: G.mons.find(m => m.d.boss)};
  };
  // 第 3 章（投石小魔王）與第 12 章（光線人）都是解謎型
  for(const act of [2, 11]){
    const {G, boss} = setup(act);
    assert(boss && boss.d.turret, '第 ' + (act+1) + ' 章的頭目應該是解謎型');
    assert(G.f.turrets && G.f.turrets.length === boss.d.turret.n,
      '砲座數量不對：' + (G.f.turrets || []).length);
    // 砲座不能疊在頭目或玩家身上，也不能長在牆裡
    for(const tt of G.f.turrets){
      assert(api.walkable(tt.x, tt.y), '砲座長在牆裡');
      assert(!(tt.x === boss.x && tt.y === boss.y), '砲座疊在頭目身上');
    }
    const hp0 = boss.hp;
    // 近戰、橫掃、貫穿、魔法 —— 全部都不該打得動
    G.p.weap = api.mk('weap', 'sky', {known:1});      // 天空之劍會橫掃
    G.p.x = boss.x - 1; G.p.y = boss.y;
    api.attack(boss);
    api.hurtMon(boss, 999, '#fff');                   // 魔法／幻獸走的是這條
    assert.strictEqual(boss.hp, hp0,
      '第 ' + (act+1) + ' 章的頭目被普通手段打掉了 ' + (hp0 - boss.hp) + ' 點');

    // 砲座打得動，而且打完要冷卻
    const t0 = G.f.turrets[0];
    G.p.x = t0.x; G.p.y = t0.y;
    assert(api.fireTurret(), '站在砲座上應該開得了火');
    assert(boss.hp < hp0, '砲座應該打得動');
    assert(t0.cd > 0, '開完火應該進冷卻');
    assert(!api.fireTurret(), '冷卻中的砲座不該再開火');

    // 換一座 —— 這就是「跑到另一個砲台裝置」
    const t1 = G.f.turrets[1];
    const hp1 = boss.hp;
    G.p.x = t1.x; G.p.y = t1.y;
    assert(api.fireTurret(), '另一座應該是熱的');
    assert(boss.hp < hp1, '另一座也該打得動');

    /* 冷卻會隨回合恢復 —— 不恢復的話砲座用完就無解了。
       迴圈上界要先抓下來：直接寫 i < t0.cd + 1 的話，
       t0.cd 每一圈都在變小，迴圈會提早結束、測試會誤判成「沒回復」。 */
    const wait = t0.cd + 1;
    for(let i = 0; i < wait; i++) api.endTurn();
    assert.strictEqual(G.f.turrets[0].cd, 0, '冷卻應該會回復');
  }
});

t('砲座彼此要隔開 —— 擠在一起就退化成連按同一顆鍵', ()=>{
  let checked = 0;
  for(const act of [2, 11]){
    for(let s = 0; s < 10; s++){
      V.act = act; V.stock = []; V.pots = [];
      api.newGame(6000 + s * 97);
      const G = api.G();
      G.floor = api.ACTS[act].floors; api.buildFloor();
      const ts = G.f.turrets || [];
      assert(ts.length >= 2, '砲座太少');
      // 至少有一對是「要走上幾步」的距離
      const far = ts.some(a => ts.some(b =>
        Math.max(Math.abs(a.x-b.x), Math.abs(a.y-b.y)) >= 3));
      assert(far, '所有砲座都擠在三格之內');
      checked++;
    }
  }
  assert(checked >= 20, '檢查數量不足');
});

// ── 試煉場 ──────────────────────────────────────────────────
// ACTS 上的 arena:{every,kill} 寫了很久卻從來沒有人讀 ——
// 第四章因此變成一層沒有頭目的空房間，使用者的回報是
// 「怎麼會有那種一層的？好像剛進去就出來了？」
t('試煉場：樓梯先鎖住，打倒指定數量才開', ()=>{
  const idx = api.ACTS.findIndex(a => a.arena);
  assert(idx >= 0, '應該有一章是試煉場');
  V.act = idx; V.stock = []; V.pots = [];
  api.newGame(88);
  const G = api.G();
  assert(G.f.arena, '試煉場的狀態應該建起來了');
  assert.strictEqual(G.f.bossLock, 1, '一進場樓梯就該是鎖的');
  const need = G.f.arena.left;
  assert(need > 0, '應該有要打倒的數量');

  // 會一波一波湧進來
  const n0 = G.mons.length;
  for(let i = 0; i < G.f.arena.every + 2; i++) api.arenaTick();
  assert(G.mons.length > n0, '時間到了應該要有下一波');

  // 打完就開門
  let guard = 0;
  while(G.f.bossLock && G.mons.length && ++guard < 200){
    const m = G.mons[0];
    api.kill(m); G.mons.shift();
  }
  assert.strictEqual(G.f.bossLock, 0, '打完之後樓梯應該解鎖');
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
