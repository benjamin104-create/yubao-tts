// 存檔測試：關掉分頁再回來，玩家的一趟要一模一樣地接回去。
//
// 這是玩家最不能容忍出錯的東西。掉一次進度，人就不會再打開了 ——
// 而「讀回來的狀態少了一件裝備」這種錯不會報任何例外，
// 它只會讓玩家覺得「這遊戲怪怪的」，然後關掉。
//
// 存檔點在樓層邊界，不在樓層中間 —— 中間存會變成「打不贏就重讀」的
// 存檔賭博，把 roguelike 最核心的「一步都不能反悔」拆掉。
const { api } = require('./simcore.js');
const assert = require('assert');

let pass = 0, fail = 0;
function t(name, fn){
  try { fn(); console.log('✓ ' + name); pass++; }
  catch(e){ console.log('✗ ' + name + '\n    ' + e.message); fail++; }
}

/* 注意：loadVillage() 是「換掉整個物件」而不是改欄位，
   所以不能在檔案開頭抓一次 api.VILLAGE() 存起來用 ——
   跑過讀檔測試之後那個參照就指向舊物件，之後所有 V().act = n 都不生效，
   而症狀是別的測試莫名其妙失敗。每次都重新取。 */
const V = () => api.VILLAGE();
// 拍一張「玩家身上有什麼」的快照，用來比對讀檔前後
function snap(){
  const G = api.G(), p = G.p;
  return {
    act:G.act, floor:G.floor, depth:G.depth, seed:G.seed,
    lv:p.lv, exp:p.exp, hp:p.hp, mhp:p.mhp, mp:p.mp, gold:p.gold, sat:p.sat,
    job:p.job, hat:p.hat,
    inv:p.inv.map(i => i.cat + '/' + i.id + '+' + i.up + (i.cursed ? 'C' : '')),
    weap:p.weap ? p.weap.cat + '/' + p.weap.id + '+' + p.weap.up : null,
    shld:p.shld ? p.shld.cat + '/' + p.shld.id + '+' + p.shld.up : null,
    st:Object.keys(p.st).sort().join(','),
  };
}

function playToFloor(n){
  const G = api.G();
  for(let f = 1; f < n; f++){
    G.p.x = G.f.stairs.x; G.p.y = G.f.stairs.y;
    G.f.bossLock = 0;
    api.descend();
  }
}

t('走到第 3 層之後，讀檔拿回一模一樣的狀態', ()=>{
  V().act = 0;
  api.newGame(4242);
  const G = api.G(), p = G.p;
  p.lv = 6; p.mhp = 60; p.hp = 41; p.gold = 777; p.exp = 30; p.job = 'war'; p.hat = 'helm';
  p.inv.push(api.mk('weap', 'steel', {known:1, up:2}));
  p.inv.push(api.mk('shld', 'wood',  {known:1, up:1, cursed:true}));
  p.inv.push(api.mk('herb', 'ygg',   {known:1}));
  p.weap = p.inv[p.inv.length - 3];
  p.shld = p.inv[p.inv.length - 2];
  playToFloor(3);
  const before = snap();
  assert.strictEqual(before.floor, 3, '應該在第 3 層');

  const q = api.loadedRun();
  assert(q, '樓層邊界應該已經存過檔');
  api.resumeRun(q);
  assert.deepStrictEqual(snap(), before, '讀檔之後狀態應該完全一致');
});

t('讀檔重建的地圖跟原來那一張一樣', ()=>{
  V().act = 1;
  api.newGame(8080);
  playToFloor(4);
  const G0 = api.G();
  const tiles = Array.from(G0.f.t).join('');
  const stairs = G0.f.stairs.x + ',' + G0.f.stairs.y;
  api.resumeRun(api.loadedRun());
  const G1 = api.G();
  assert.strictEqual(Array.from(G1.f.t).join(''), tiles, '地形應該一模一樣');
  assert.strictEqual(G1.f.stairs.x + ',' + G1.f.stairs.y, stairs, '樓梯應該在同一格');
});

t('死亡會把紀錄點清掉 —— 不能讀檔逃避死亡', ()=>{
  V().act = 0; V().feather = 0;
  api.newGame(5150);
  playToFloor(2);
  assert(api.loadedRun(), '第 2 層應該有存檔');
  const G = api.G();
  G.p.hp = 0; G.p.inv = [];
  api.death();
  assert.strictEqual(api.loadedRun(), null, '死了之後不該還有紀錄點');
});

t('通關一章之後紀錄點也會清掉（下一趟從村莊開始）', ()=>{
  V().act = 0;
  api.newGame(6161);
  playToFloor(2);
  assert(api.loadedRun(), '應該有存檔');
  const G = api.G();
  G.floor = api.ACTS[0].floors;
  G.p.x = G.f.stairs.x; G.p.y = G.f.stairs.y; G.f.bossLock = 0;
  api.descend();                       // 最後一層踩樓梯＝過關
  assert.strictEqual(api.loadedRun(), null, '過關之後不該還有紀錄點');
});

t('壞掉的存檔不會讓遊戲爆掉，只會被當成沒有存檔', ()=>{
  const bad = ['', '{', 'null', '{"v":999}', '{"v":1,"seed":1}',
               '{"v":1,"seed":1,"p":{}}', '{"v":1,"seed":"x","p":{"inv":[]}}'];
  for(const raw of bad){
    global.localStorage.setItem('claude-abyss-run', raw);
    assert.doesNotThrow(()=> api.loadedRun(), '壞存檔 ' + raw + ' 讓 loadedRun 爆了');
  }
  global.localStorage.removeItem('claude-abyss-run');
});

t('存檔裡的道具不會帶著舊數值復活', ()=>{
  V().act = 0;
  api.newGame(7272);
  const p = api.G().p;
  p.inv.push(api.mk('weap', 'drgn', {known:1, up:3}));
  playToFloor(2);
  api.resumeRun(api.loadedRun());
  const w = api.G().p.inv.find(i => i.id === 'drgn');
  assert(w, '屠龍刀應該還在');
  // d 指向現在的資料表，不是存檔當下那一份
  assert.strictEqual(w.d, api.WEAP.find(x => x.id === 'drgn'), '道具定義應該指向現行的資料表');
  assert.strictEqual(w.up, 3, '強化值應該保留');
});

t('壺裡的東西也要撐過讀檔 —— 而且不會被村莊那份多發一次', ()=>{
  V().act = 0; V().pots = [];
  api.newGame(3131);
  const G = api.G(), p = G.p;
  const pot = api.mk('pot', 'store'); pot.cap = 4; p.inv.push(pot);
  api.potPut(pot, api.mk('weap', 'steel', {known:1, up:3}));
  api.potPut(pot, api.mk('herb', 'ygg',   {known:1}));
  const ip = api.mk('pot', 'ident'); ip.cap = 2; p.inv.push(ip);
  playToFloor(3);

  // 巢狀的內容物也要進快照 —— snap() 只看得到背包第一層
  const deep = () => api.G().p.inv.map(i =>
    i.cat + '/' + i.id + '[' + (i.cap|0) + ']{' +
    (i.contents||[]).map(c => c.cat + '/' + c.id + '+' + c.up).join('|') + '}').join(' ');
  const before = deep();
  assert(before.includes('weap/steel+3'), '壺裡應該有那把劍');

  const q = api.loadedRun();

  /* 這裡要**故意**把村莊寄放的那一份填起來再讀檔。
     不填的話這條斷言等於沒寫：正常流程下 clearAct() 一定跟著 clearRun()，
     所以「有存檔」與「村莊寄放著壺」不會同時成立，
     把 resumeRun() 裡的保護整段刪掉，測試照樣全綠。
     （這一條是驗證過的：刪掉保護之後第一版的斷言依然通過。）

     但那份保護不是多餘的 —— 存檔壞掉、版本升級、使用者自己動了
     localStorage，都會讓兩者同時存在，而後果是背包裡憑空多一個壺，
     不報任何錯。守著的東西就要在守著的狀態下測。 */
  V().pots = [{cat:'pot', id:'store', cap:4, contents:[{cat:'food', id:'bread'}]}];
  const potsBefore = JSON.stringify(V().pots);

  api.resumeRun(q);
  assert.strictEqual(deep(), before, '壺與壺裡的東西讀檔後應該完全一致');
  assert.strictEqual(JSON.stringify(V().pots), potsBefore,
    '讀檔不該吃掉村莊寄放的那一份');
  assert.strictEqual(api.G().p.inv.filter(i => i.cat === 'pot').length, 2,
    '村莊那份不該在讀檔時被發進背包 —— 那是憑空多一個壺');
  V().pots = [];
});

// ── 造型只屬於主角 ──────────────────────────────────────────
t('換造型只影響主角，怪物與村民完全不受影響', ()=>{
  const shot = () => api.MONS.concat(api.BOSS)
    .map(d => (api.atlas()[d.id] || {}).__sig || d.id).join('|');
  const before = shot();
  for(const sk of api.SKINS){
    V().skin = sk;
    api.refreshHero();
    assert.strictEqual(shot(), before, '換成 ' + sk + ' 之後怪物的圖變了');
  }
  V().skin = 'blob'; api.refreshHero();
});

t('六種造型都畫得出來，而且互不相同', ()=>{
  const sigs = new Set();
  for(const sk of api.SKINS){
    const spans = api.BLOB_SKINS[sk];
    assert(Array.isArray(spans) && spans.length, sk + ' 沒有形狀資料');
    for(const [y, x0, w] of spans){
      assert(y >= 0 && y < 16, sk + ' 有跨距超出上下界：y=' + y);
      assert(x0 >= 0 && x0 + w <= 16, sk + ' 有跨距超出左右界：' + x0 + '+' + w);
    }
    const sig = spans.map(a => a.join(',')).sort().join(';');
    assert(!sigs.has(sig), sk + ' 的形狀跟另一種完全一樣');
    sigs.add(sig);
  }
});

t('造型存得下來，壞掉的值會退回預設', ()=>{
  V().skin = 'cat';
  api.saveVillage();
  V().skin = 'zzz';                       // 假裝存檔被改壞
  api.loadVillage();
  assert.strictEqual(api.VILLAGE().skin, 'cat', '存進去的造型應該讀得回來');
  V().skin = 'zzz'; api.saveVillage(); api.loadVillage();
  assert.strictEqual(api.VILLAGE().skin, 'blob', '壞掉的造型應該退回預設');
});

// ── 紀錄之環 ────────────────────────────────────────────────
t('紀錄之環只出現在頭目層的前一層', ()=>{
  for(let a = 0; a < api.ACTS.length; a++){
    const act = api.ACTS[a];
    V().act = a;
    api.newGame(1717 + a);
    const G = api.G();
    /* 章節要用 G.act 指定，不能只設 VILLAGE.act —— newGame() 會把
       村莊的進度夾在主線最後一章（Math.min(…, LAST_MAIN)），
       所以支線的副本迷宮用 VILLAGE.act 是進不去的。
       不改的話，這個迴圈會拿副本的層數去比對別的章生出來的樓層，
       然後報一個跟真正的問題完全無關的錯。 */
    G.act = a;
    for(let f = 1; f <= act.floors; f++){
      G.floor = f; api.buildFloor();
      const want = !!(act.boss && f === act.floors - 1);
      assert.strictEqual(!!G.f.shrine, want,
        act.nm + ' 第 ' + f + ' 層：光環應該' + (want ? '有' : '沒有'));
      if(G.f.shrine){
        assert(api.walkable(G.f.shrine.x, G.f.shrine.y), '光環不能長在牆裡');
        assert(!(G.f.shrine.x === G.f.stairs.x && G.f.shrine.y === G.f.stairs.y),
               '光環不該跟樓梯疊在同一格');
      }
    }
  }
});

t('踩上紀錄之環會存檔並補滿，而且只有一次', ()=>{
  V().act = 0;
  const act = api.ACTS[0];
  api.newGame(2929);
  const G = api.G(), p = G.p;
  G.floor = act.floors - 1; api.buildFloor();
  assert(G.f.shrine, '這一層應該有光環');
  api.clearRun();
  p.hp = 1; p.mp = 0;
  p.x = G.f.shrine.x; p.y = G.f.shrine.y;
  api.stepOn();
  assert.strictEqual(p.hp, p.mhp, '應該補滿體力');
  assert.strictEqual(p.mp, p.mmp, '應該補滿魔力');
  assert(api.loadedRun(), '應該存了檔');
  assert(G.f.shrine.used, '應該熄掉了');
  p.hp = 1; p.mp = 0;
  api.stepOn();
  assert.strictEqual(p.hp, 1, '第二次踩上去不該再補 —— 那會變成無限泉水');
});

/* ── 餘力煉成 ────────────────────────────────────────────────
   使用者的原話：「魔法點數也是，點到滿，結果每升一級都還會有點數，
   感覺一堆點數都不能用，很沒作用」。
   換到的東西必須跨死亡 —— 不跨的話它就只是「這一趟的加成」，
   而玩家花的是一個永遠不會再回來的資源。 */
t('五系沒滿的時候煉不了 —— 點數要先花在魔法上', ()=>{
  V().act = 0; V().sp = 0; V().sch = {heal:0,bolt:0,fire:0,aqua:0,wind:0};
  V().hpBonus = 0; V().strBonus = 0; V().defBonus = 0;
  api.newGame(5150);
  const p = api.G().p;
  p.sp = 20;
  assert(!api.schFull(p), '五系不該是滿的');
});

t('五系滿了之後，多的點數換得到永久的身體，而且撐得過死亡', ()=>{
  V().act = 0; V().sp = 0;
  V().sch = {heal:5,bolt:5,fire:5,aqua:5,wind:5};
  V().hpBonus = 0; V().strBonus = 0; V().defBonus = 0;
  api.newGame(5151);
  const G = api.G(), p = G.p;
  assert(api.schFull(p), '五系應該是滿的');
  p.sp = 8;
  const mhp0 = p.mhp, atk0 = api.pAtk(), def0 = api.pDef();
  const R = k => api.REFINE.find(r => r.key === k);

  assert(api.refine(p, R('hpBonus')), '體力應該換得到');
  assert.strictEqual(p.mhp, mhp0 + 10, '體力上限沒有立刻生效');
  assert(api.refine(p, R('strBonus')), '力量應該換得到');
  assert(api.pAtk() > atk0, '力量沒有立刻生效');
  assert(api.refine(p, R('defBonus')), '防禦應該換得到');
  assert(api.pDef() > def0, '防禦沒有立刻生效');
  assert.strictEqual(p.sp, 0, '點數應該扣光了：還剩 ' + p.sp);
  assert(!api.refine(p, R('hpBonus')), '沒點數了還換得到');

  // 死一次再來 —— 換到的東西要還在
  api.loadVillage();
  const V2 = api.VILLAGE();
  assert.strictEqual(V2.hpBonus, 10, '體力沒有存進村莊');
  assert.strictEqual(V2.strBonus, 1, '力量沒有存進村莊');
  assert.strictEqual(V2.defBonus, 1, '防禦沒有存進村莊');
  api.newGame(5152);
  assert.strictEqual(api.G().p.strb, 1, '下一趟沒有拿到換來的力量');
  assert(api.G().p.mhp >= mhp0 + 10, '下一趟沒有拿到換來的體力');
  V().sch = {heal:0,bolt:0,fire:0,aqua:0,wind:0};
  V().hpBonus = 0; V().strBonus = 0; V().defBonus = 0; api.saveVillage();
});

/* ═══ 驗收網址不准碰玩家的存檔 ═══════════════════════════════
   saveVillage() 一直守著 QA_MODE，saveRun()／clearRun() 卻漏了 ——
   於是「完全不寫進正式存檔」只做到一半。

   踩出來的樣子：玩家玩到第 6 章、中途存檔在第 2 層，開一個
   ?qa=floor&act=crystal 的驗收網址進去走一段樓梯，中途存檔就變成
   act=12 floor=3；在裡面死一次，整份存檔直接不見。
   而驗收網址正是拿來到處亂走亂死的 —— 那是它的用途。

   QA_MODE 是腳本載入當下算出來的常數，事後改不了，
   所以這一段要另外開一個行程，用 QA_SEARCH 把 location.search 換掉。 */
t('驗收網址（?qa=）不會動到玩家的存檔', () => {
  const { execFileSync } = require('child_process');
  const src = `
    const { api } = require('${__dirname.replace(/\\/g, '/')}/simcore.js');
    const assert = require('assert');
    // 先放一份「玩家的存檔」進去
    localStorage.setItem('claude-abyss-run', JSON.stringify({sentinel:1}));
    api.newGame(4242);
    api.saveRun();
    const after = localStorage.getItem('claude-abyss-run');
    assert.strictEqual(after, JSON.stringify({sentinel:1}),
      'QA 模式下 saveRun() 蓋掉了玩家的存檔');
    api.clearRun();
    assert.strictEqual(localStorage.getItem('claude-abyss-run'),
      JSON.stringify({sentinel:1}), 'QA 模式下 clearRun() 刪掉了玩家的存檔');
    console.log('QA-OK');
  `;
  const out = execFileSync(process.execPath, ['-e', src],
    { env: Object.assign({}, process.env, { QA_SEARCH: '?qa=floor&act=crystal' }),
      encoding: 'utf8' });
  assert(out.includes('QA-OK'), '子行程沒有跑完');
});

/* 反過來也要成立：一般入口（沒有 ?qa=）**必須**真的存得下去。
   只驗上面那一條的話，把 saveRun() 整支改成 return 也會全綠 ——
   而那等於所有玩家都不能存檔了。 */
t('一般入口照樣存得下去（上面那條不能把存檔關掉）', () => {
  api.clearRun();
  api.newGame(4243);
  api.saveRun();
  const raw = localStorage.getItem('claude-abyss-run');
  assert(raw, '一般模式下 saveRun() 沒有寫進去');
  assert.strictEqual(JSON.parse(raw).seed, 4243, '存進去的不是這一趟');
  api.clearRun();
  assert(!localStorage.getItem('claude-abyss-run'), '一般模式下 clearRun() 沒有清掉');
});

console.log('\n通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
