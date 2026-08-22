// 劇情機制的走通測試：整條路線的形狀、迷路的村民護送，以及存檔遷移。
//
// 為什麼要單獨一支：這些事都不會讓遊戲報錯。村民卡在轉角走不出去、
// 護送成功卻沒拿到獎勵、通天塔還是寫著 B1F、舊存檔被丟回錯的章 ——
// 全部照樣跑得動，只是玩家的體驗壞掉。sim.js 量的是「活不活得下來」，
// 量不到這些。
//
// 護送那一段特別容易壞：村民會擋路。第一版沒有「交換位置」，
// 機器人帶著他的時候四十趟只有八趟走得完第一章（其餘卡在死路），
// 而遊戲一行錯誤都沒有。加上交換之後回到 26 趟。
const { api } = require('./simcore.js');

let fail = 0, total = 0;
const ok = (cond, msg) => { total++; if(cond) console.log('  ✓ ' + msg);
  else { console.log('  ✗ ' + msg); fail++; } };

const ACTS = api.i18n.ACTS;
const AI = id => ACTS.findIndex(a => a.id === id);

/* ═══ 整條路線的形狀 ═══════════════════════════════════════════
   使用者手繪的剖面圖：「從神殿找到隱藏前往地底廣場的入口 → 往下抵達
   地底廣場 → 橫向打敗小王，找到向上前往通天塔入口，往上到塔頂進入時空之門」。

   這一段驗的是那張圖：地面的神殿在最前面，中間一路往下，
   然後**一個**橫著走的大廣間，之後全部往上。順序錯了不會報錯 ——
   村莊那張側面圖會照樣畫出一個沒有人看得懂的形狀。 */
console.log('=== 路線的形狀（神殿 → 往下 → 大廣間 → 往上） ===');
const surf = ACTS.filter(a => a.surf);
const wide = ACTS.filter(a => a.wide);
const up   = ACTS.filter(a => a.up);
ok(surf.length === 1, '地面上的章節剛好一章（' + surf.length + '）');
ok(ACTS[0].surf, '第一章就是那一章（' + ACTS[0].nm + '）');
ok(!ACTS[0].up, '神殿是往下走進去的');
ok(ACTS[0].id === 'temple', '第一章是巴比倫神殿');
ok(wide.length === 1, '橫著走的章節剛好一章（' + wide.length + '）');
ok(wide.length === 1 && wide[0].id === 'hall', '那一章是地下大廣間');
ok(up.length >= 1, '至少有一章是往上走的（' + up.length + ' 章）');
ok(ACTS[ACTS.length-1].up, '最後一章在塔上');

const firstUp = ACTS.findIndex(a => a.up);
const wideAt  = ACTS.findIndex(a => a.wide);
// 往上的章節必須連在一起而且在最後 —— 中間插一段往上再往下，
// 那張側面圖就畫不出來了（它假設「下去、橫過去、上來」）
ok(firstUp < 0 || ACTS.slice(firstUp).every(a => a.up),
   '往上的章節連在一起而且排在最後');
/* 大廣間必須**緊接在**第一章往上的前面。這是整張剖面圖的鉸鏈：
   它把左邊的豎井接到右邊的塔基。中間隔了一章的話，玩家會在
   「找到向上的門」之後又被送回地底繼續往下，那條故事線就斷了。 */
ok(wideAt === firstUp - 1,
   '大廣間就接在第一章往上的前面（大廣間第 ' + (wideAt+1) +
   ' 章、開始往上第 ' + (firstUp+1) + ' 章）');
/* 指名驗通天塔那一章。只驗「有幾章往上」是不夠的 ——
   把 tower 的 up 拿掉、留著後面兩章，那幾條照樣全綠，
   而使用者問的正是「叫通天之塔為什麼一直往下」。 */
const tower = ACTS.find(a => a.id === 'tower');
ok(!!tower && tower.up, '「通天塔」那一章是往上走的');
ok(!!tower && tower.floors === Math.max(...ACTS.map(a => a.floors)),
   '通天塔是最長的一章（側面圖靠層數決定高度，它要看起來最高）');
ok(api.floorLabel(AI('mine'), 3) === 'B3F',
   '往下的章寫 B3F（實際 ' + api.floorLabel(AI('mine'), 3) + '）');
ok(api.floorLabel(firstUp, 3) === '3F',
   '往上的章不寫 B（實際 ' + api.floorLabel(firstUp,3) + '）');

/* 每一章都要有自己的地貌與曲子。這裡只驗地貌對得上表 ——
   新增一章卻忘了給 ACT_THEME，它會安靜地退回礦坑的石頭色，
   而「這一章長得跟第一章一樣」不會有任何一支測試看得見。
   ★ 真的踩過：大廣間的地貌本來叫 hall，而 TRACKS.hall 已經被
   「怪物之間」那首佔走了 —— 整章的音樂會變成一首沒有解決的等待曲。 */
console.log('\n=== 每一章都有自己的地貌 ===');
const noTheme = ACTS.filter(a => !api.ACT_THEME[a.id]);
ok(!noTheme.length, '沒有章節漏掉地貌（' + noTheme.map(a=>a.id).join('、') + '）');
ok(api.ACT_THEME.temple !== api.ACT_THEME.mine, '神殿跟礦坑不是同一個地貌');
ok(api.ACT_THEME.hall !== api.ACT_THEME.crystal, '大廣間跟水晶礦坑不是同一個地貌');
ok(api.ACT_THEME.hall !== 'hall',
   '大廣間的地貌沒有叫 hall（那個名字已經被「怪物之間」那首曲子佔走了）');

/* ═══ 中繼之村 ═══════════════════════════════════════════════
   使用者：「然後找到往上的地方（中繼之村）然後往上進入通天塔」。
   它是**轉折點的村莊**：打通大廣間、下一章開始往上，才會住到這裡。 */
console.log('\n=== 中繼之村 ===');
const V = api.VILLAGE();
const styleAt = a => { V.act = a; return api.villageStyle(); };
ok(styleAt(0) !== 'spire', '第一章之前住的不是中繼之村');
ok(styleAt(wideAt) !== 'spire',
   '還沒打完大廣間就還不是中繼之村（第 ' + (wideAt+1) + ' 章）');
ok(styleAt(firstUp) === 'spire',
   '打完大廣間、下一章開始往上，就住到中繼之村');
ok(styleAt(ACTS.length-1) === 'spire', '塔上的每一章都回中繼之村');
ok(api.VSTYLES.includes('spire') && !!api.VNAME.spire && !!api.VPAL.spire,
   '中繼之村有自己的名字與色盤（少了色盤會直接畫不出來）');
// 四個村莊的顏色必須真的不一樣，不然換的只有名字
const lits = api.VSTYLES.map(s => api.VPAL[s].lit);
ok(new Set(lits).size === api.VSTYLES.length, '四個村莊的燈火各是各的顏色');

/* ═══ 存檔遷移 ═══════════════════════════════════════════════
   VILLAGE.act 存的是章節索引，而序章插在 0、大廣間插在 13 ——
   舊存檔的每一個索引都往後移了。不遷移的話，一個已經打到通天塔的人
   會被丟回水晶礦坑，而且沒有任何錯誤訊息。 */
console.log('\n=== 舊存檔的章節編號 ===');
const oldTower = 12, oldMine = 0, oldCrystal = 11, oldChaos = 14;
ok(api.migrateAct(oldMine, 0) === AI('mine'), '舊的第 1 章（礦坑）對到新的礦坑');
ok(api.migrateAct(oldCrystal, 0) === AI('crystal'), '舊的水晶礦坑對到新的水晶礦坑');
ok(api.migrateAct(oldTower, 0) === AI('tower'), '舊的通天塔對到新的通天塔');
ok(api.migrateAct(oldChaos, 0) === AI('chaos'), '舊的混沌之間對到新的混沌之間');
ok(api.migrateAct(AI('tower'), api.VILLAGE_VER) === AI('tower'),
   '已經是新版的存檔不會再被搬一次（搬兩次就整個往後跑掉了）');
ok(api.RUN_VER >= 2,
   '中途存檔的版本有跟著跳（不跳的話，舊的一趟會在錯的章節被讀回來）');

/* ═══ 迷路的村民 ═══════════════════════════════════════════ */
console.log('\n=== 迷路的村民 ===');
// 生成：只在礦坑洞穴第三層（使用者原話是「第一關的第三層」，
// 序章加進來之後那一章是第 2 章 —— 用 id 找，不寫索引）
const MINE = AI('mine');
V.act = MINE; V.vault = 0; V.npcDone = 0;
api.newGame(13);
const G = api.G();
G.act = MINE;
const seen = {};
for(let f = 1; f <= 5; f++){ G.floor = f; api.buildFloor(); seen[f] = !!G.npc; }
ok(!seen[1] && !seen[2], '前兩層不會出現（那兩層是教走路與打架）');
ok(seen[3], '第三層會出現');
ok(!seen[4], '第四層不會另外生一個');
// 序章裡不該有村民 —— 他是礦坑那一章的劇情，不是「任何一章的第三層」
V.act = 0; api.newGame(13);
const G0 = api.G();
G0.act = 0; G0.floor = 3; api.buildFloor();
ok(!G0.npc, '序章（神殿）第三層不會冒出一個村民');

V.act = MINE; api.newGame(13);
const G2 = api.G();
G2.act = MINE; G2.floor = 3; api.buildFloor();
// 護送：撞一下開始跟、再撞一下交換位置（不然他會把人堵死）
const n = G2.npc;
ok(!!n && n.hp === n.mhp, '出現時是滿血的');
ok(!!n && !n.follow, '一開始不會跟 —— 玩家要先走過去');
const p = G2.p;
p.x = n.x - 1; p.y = n.y;
api.tryMove(1, 0);
ok(!!G2.npc && G2.npc.follow, '走過去就開始護送');
const bx = p.x, by = p.y, nx = G2.npc.x, ny = G2.npc.y;
api.tryMove(Math.sign(nx - bx), Math.sign(ny - by));
ok(p.x === nx && p.y === ny && G2.npc.x === bx && G2.npc.y === by,
   '再走進他就交換位置（走廊只有一格寬，不交換會把人堵死）');

// 受傷與治療
G2.npc.hp = 10;
const before = p.inv.length;
p.inv.push(api.mk ? api.mk('herb','heal') : null);
if(p.inv[p.inv.length-1]){
  const hp0 = G2.npc.hp;
  p.x = G2.npc.x - 1; p.y = G2.npc.y;
  api.tryMove(1, 0);
  ok(G2.npc.hp > hp0, '相鄰時走進去會用回復草替他治療（' + hp0 + ' → ' + G2.npc.hp + '）');
  ok(p.inv.length === before, '治療會花掉那一株草');
} else { ok(false, '拿不到回復草，無法測治療'); }

// 帶著他過樓層
G2.npc.hp = G2.npc.mhp;
G2.floor = 4; api.buildFloor();
ok(!!G2.npc && G2.npc.follow, '跟著的村民會過樓層');
// 沒跟的就留在原地那一層
G2.floor = 3; api.buildFloor();
if(G2.npc) G2.npc.follow = 0;
G2.floor = 4; api.buildFloor();
ok(!G2.npc, '沒跟著的村民不會被帶走（不救也可以）');

/* Token 金庫要撐得過重新整理。這一條是踩出來的：loadVillage() 會用
   白名單重建一整個 VILLAGE，而 vault 不在白名單裡 —— 護送成功的人
   只要重整一次分頁，金庫就消失了，而且不會有任何錯誤訊息。 */
console.log('\n=== 存下來的東西真的存得住 ===');
V.vault = 1; V.npcDone = 1; api.saveVillage(); api.loadVillage();
ok(api.VILLAGE().vault === 1, 'Token 金庫撐得過重新讀檔');
ok(api.VILLAGE().npcDone === 1, '「救過了」撐得過重新讀檔');

console.log('\n%d 項，%d 失敗', total, fail);
process.exit(fail ? 1 : 0);
