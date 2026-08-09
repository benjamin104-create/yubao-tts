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

const V = api.VILLAGE();
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
  V.act = 0;
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
  V.act = 1;
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
  V.act = 0; V.feather = 0;
  api.newGame(5150);
  playToFloor(2);
  assert(api.loadedRun(), '第 2 層應該有存檔');
  const G = api.G();
  G.p.hp = 0; G.p.inv = [];
  api.death();
  assert.strictEqual(api.loadedRun(), null, '死了之後不該還有紀錄點');
});

t('通關一章之後紀錄點也會清掉（下一趟從村莊開始）', ()=>{
  V.act = 0;
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
  V.act = 0;
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

console.log('\n通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
