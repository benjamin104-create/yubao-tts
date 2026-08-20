// 劇情機制的走通測試：迷路的村民護送，以及「往上走」的章節。
//
// 為什麼要單獨一支：這兩件事都不會讓遊戲報錯。村民卡在轉角走不出去、
// 護送成功卻沒拿到獎勵、通天塔還是寫著 B1F —— 全部照樣跑得動，
// 只是玩家的體驗壞掉。sim.js 量的是「活不活得下來」，量不到這些。
//
// 護送那一段特別容易壞：村民會擋路。第一版沒有「交換位置」，
// 機器人帶著他的時候四十趟只有八趟走得完第一章（其餘卡在死路），
// 而遊戲一行錯誤都沒有。加上交換之後回到 26 趟。
const { api } = require('./simcore.js');

let fail = 0, total = 0;
const ok = (cond, msg) => { total++; if(cond) console.log('  ✓ ' + msg);
  else { console.log('  ✗ ' + msg); fail++; } };

console.log('=== 往上走的章節 ===');
const ACTS = api.i18n.ACTS;
const up = ACTS.filter(a => a.up);
ok(up.length >= 1, '至少有一章是往上走的（' + up.length + ' 章）');
ok(!ACTS[0].up, '第一章是往下的');
ok(ACTS[ACTS.length-1].up, '最後一章在塔上');
// 往上的章節必須連在一起而且在最後 —— 中間插一段往上再往下，
// 那張側面圖就畫不出來了（它假設「下去、轉頭、上來」）
const firstUp = ACTS.findIndex(a => a.up);
ok(firstUp < 0 || ACTS.slice(firstUp).every(a => a.up),
   '往上的章節連在一起而且排在最後');
/* 指名驗通天塔那一章。只驗「有幾章往上」是不夠的 ——
   把 tower 的 up 拿掉、留著後面兩章，那幾條照樣全綠，
   而使用者問的正是「叫通天之塔為什麼一直往下」。 */
const tower = ACTS.find(a => a.id === 'tower');
ok(!!tower && tower.up, '「通天塔」那一章是往上走的');
ok(!!tower && tower.floors === Math.max(...ACTS.map(a => a.floors)),
   '通天塔是最長的一章（側面圖靠層數決定高度，它要看起來最高）');
ok(api.floorLabel(0, 3) === 'B3F', '往下的章寫 B3F（實際 ' + api.floorLabel(0,3) + '）');
ok(api.floorLabel(firstUp, 3) === '3F',
   '往上的章不寫 B（實際 ' + api.floorLabel(firstUp,3) + '）');

console.log('\n=== 迷路的村民 ===');
// 生成：只在第一章第三層
api.VILLAGE().act = 0; api.VILLAGE().vault = 0; api.VILLAGE().npcDone = 0;
api.newGame(13);
const G = api.G();
const seen = {};
for(let f = 1; f <= 5; f++){ G.floor = f; api.buildFloor(); seen[f] = !!G.npc; }
ok(!seen[1] && !seen[2], '前兩層不會出現（那兩層是教走路與打架）');
ok(seen[3], '第三層會出現');
ok(!seen[4], '第四層不會另外生一個');

// 護送：撞一下開始跟、再撞一下交換位置（不然他會把人堵死）
G.floor = 3; api.buildFloor();
const n = G.npc;
ok(!!n && n.hp === n.mhp, '出現時是滿血的');
ok(!n.follow, '一開始不會跟 —— 玩家要先走過去');
// 把玩家放到他旁邊
const p = G.p;
p.x = n.x - 1; p.y = n.y;
api.tryMove(1, 0);
ok(!!G.npc && G.npc.follow, '走過去就開始護送');
const bx = p.x, by = p.y, nx = G.npc.x, ny = G.npc.y;
api.tryMove(Math.sign(nx - bx), Math.sign(ny - by));
ok(p.x === nx && p.y === ny && G.npc.x === bx && G.npc.y === by,
   '再走進他就交換位置（走廊只有一格寬，不交換會把人堵死）');

// 受傷與治療
G.npc.hp = 10;
const before = p.inv.length;
p.inv.push(api.mk ? api.mk('herb','heal') : null);
if(p.inv[p.inv.length-1]){
  const hp0 = G.npc.hp;
  p.x = G.npc.x - 1; p.y = G.npc.y;
  api.tryMove(1, 0);
  ok(G.npc.hp > hp0, '相鄰時走進去會用回復草替他治療（' + hp0 + ' → ' + G.npc.hp + '）');
  ok(p.inv.length === before, '治療會花掉那一株草');
} else { ok(false, '拿不到回復草，無法測治療'); }

// 帶著他過樓層
G.npc.hp = G.npc.mhp;
G.floor = 4; api.buildFloor();
ok(!!G.npc && G.npc.follow, '跟著的村民會過樓層');
// 沒跟的就留在原地那一層
G.floor = 3; api.buildFloor();
if(G.npc) G.npc.follow = 0;
G.floor = 4; api.buildFloor();
ok(!G.npc, '沒跟著的村民不會被帶走（不救也可以）');

console.log('\n%d 項，%d 失敗', total, fail);
process.exit(fail ? 1 : 0);
