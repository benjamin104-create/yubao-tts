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
/* 走過去 = 跟他說話。使用者：「應該會需要和村人對話，主角可以選擇
   同意或不同意，按同意的話，就會牢牢的跟著主角」。
   舊版是撞一下就自動變成護送 —— 那不是選擇，是踩到機關，
   而「不救也可以」這件事在畫面上根本不存在。 */
const p = G2.p;
/* 站的位置要挑過：不但要能走到村民身上，自己旁邊還得留一格空地 ——
   下一條要驗「對話框開著的時候走不動」，而如果四周本來就都是牆，
   那條斷言會在功能壞掉的時候仍然是綠的（第一版就是這樣過的）。 */
const freeAround = (x, y) => api.DIRS.filter(d =>
  api.walkable(x + d[0], y + d[1]) && !api.monAt(x + d[0], y + d[1]) &&
  !(x + d[0] === n.x && y + d[1] === n.y) &&
  api.cornerOK(x, y, x + d[0], y + d[1])).length;
let stand = null;
for(const d of api.DIRS){
  const sx = n.x - d[0], sy = n.y - d[1];
  if(!api.walkable(sx, sy) || api.monAt(sx, sy)) continue;
  if(!api.cornerOK(sx, sy, n.x, n.y)) continue;
  if(freeAround(sx, sy) < 1) continue;
  stand = [sx, sy, d]; break;
}
ok(!!stand, '找得到一個「走得到村民、旁邊又有空地」的位置');
p.x = stand[0]; p.y = stand[1];
api.tryMove(stand[2][0], stand[2][1]);
ok(api.talkOpen(), '走過去會跟他說話（跳出對話框）');
ok(!G2.npc.follow, '還沒回答之前不會開始跟');
/* 對話框開著的時候方向鍵不該讓主角走路 —— 他正在回答一個問題。
   要往一個**真的走得過去**的方向試：隨便挑一個方向的話，
   那一格可能本來就是牆，於是「沒有移動」會是牆擋的，不是對話框擋的，
   而這條斷言就會在功能壞掉的時候仍然是綠的。 */
const open = api.DIRS.find(d =>
  api.walkable(p.x + d[0], p.y + d[1]) &&
  !api.monAt(p.x + d[0], p.y + d[1]) &&
  !(G2.npc && G2.npc.x === p.x + d[0] && G2.npc.y === p.y + d[1]) &&
  api.cornerOK(p.x, p.y, p.x + d[0], p.y + d[1]));
ok(!!open, '旁邊有一格是真的走得過去的（不然下一條驗不到東西）');
const kx = p.x, ky = p.y;
if(open) api.tryMove(open[0], open[1]);
ok(p.x === kx && p.y === ky, '對話框開著的時候主角不會走路');

// 先按不同意：他要留在原地，而且不會擋路
api.answerTalk(false);
ok(!api.talkOpen(), '回答完對話框就關掉');
ok(!!G2.npc && !G2.npc.follow, '按「不同意」他不會跟（不救也可以）');

// 再走過去可以再問一次 —— 反悔不該有代價
api.tryMove(stand[2][0], stand[2][1]);
ok(api.talkOpen(), '再走過去會再問一次');
api.answerTalk(true);
ok(!!G2.npc && G2.npc.follow, '按「同意」就開始護送');
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
  // 站到他旁邊 —— 方向照實算，不要假設他還在右邊（他會跟著走）
  const hd = api.DIRS.find(d => api.walkable(G2.npc.x - d[0], G2.npc.y - d[1])
    && api.cornerOK(G2.npc.x - d[0], G2.npc.y - d[1], G2.npc.x, G2.npc.y));
  p.x = G2.npc.x - hd[0]; p.y = G2.npc.y - hd[1];
  api.tryMove(hd[0], hd[1]);
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

/* ═══ 「牢牢的跟著，不會亂跑」 ═══════════════════════════════
   使用者的原話。這是一句可以量的話：帶著他在地牢裡亂走，
   他應該幾乎全程都貼在旁邊。

   為什麼要跑十顆種子而不是一顆：單一種子量不出差別。
   實測（每顆 150 步）——
       貪心走一步   775 步裡有 30 步距離超過兩格，最遠掉到 5 格
       BFS ＋追趕   753 步裡有  0 步超過兩格，最遠 2 格
   而在其中某些種子上，兩種寫法的成績一模一樣（地形夠開闊）。
   只驗一顆的話，退回貪心版仍然是綠的 —— 這條測試就白寫了。 */
console.log('\n=== 牢牢跟著（十張圖、各亂走 150 步） ===');
{
  const V2 = api.VILLAGE();
  const SEEDS = [20260822, 11, 202, 3003, 40404, 555, 6006, 77, 808, 9009];
  let maps = 0, steps = 0, farSteps = 0, worst = 0;
  for(const seed of SEEDS){
    V2.act = MINE; V2.vault = 0; V2.npcDone = 0;
    api.newGame(seed);
    const G3 = api.G();
    G3.act = MINE; G3.floor = 3; api.buildFloor();
    if(!G3.npc) continue;
    const n3 = G3.npc, p3 = G3.p;
    let st = null;
    for(const d of api.DIRS){
      const sx = n3.x - d[0], sy = n3.y - d[1];
      if(api.walkable(sx, sy) && !api.monAt(sx, sy) && api.cornerOK(sx, sy, n3.x, n3.y)){
        st = [sx, sy, d]; break;
      }
    }
    if(!st) continue;
    maps++;
    p3.x = st[0]; p3.y = st[1];
    api.tryMove(st[2][0], st[2][1]);
    if(api.talkOpen()) api.answerTalk(true);
    // 亂走。用自己的偽亂數，不吃遊戲的 RNG —— 吃遊戲的會影響怪物生成，
    // 那樣量到的就不只是「跟得緊不緊」了。
    const rnd = (s0 => () => (s0 = (s0 * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff)(7);
    for(let i = 0; i < 150 && G3.npc; i++){
      const d = api.DIRS[(rnd() * 8) | 0];
      const bx2 = p3.x, by2 = p3.y;
      api.tryMove(d[0], d[1]);
      if(p3.x === bx2 && p3.y === by2) continue;   // 撞牆不算一步
      steps++;
      const dist = Math.max(Math.abs(p3.x - G3.npc.x), Math.abs(p3.y - G3.npc.y));
      worst = Math.max(worst, dist);
      if(dist > 2) farSteps++;
    }
  }
  ok(maps >= 8, '十顆種子裡至少八張圖跑得起來（實際 ' + maps + ' 張）');
  ok(steps > 400, '真的走了幾百步（實際 ' + steps + ' 步）');
  /* 門檻照實際量到的數字訂，不留寬鬆的餘地 —— 留了餘地的門檻
     會在退化的時候仍然是綠的，而那正是這條測試要防的事。 */
  ok(farSteps === 0, '全程貼著（' + farSteps + '/' + steps + ' 步距離超過兩格）');
  ok(worst <= 2, '一次都沒有掉隊（最遠 ' + worst + ' 格）');
}

/* Token 金庫要撐得過重新整理。這一條是踩出來的：loadVillage() 會用
   白名單重建一整個 VILLAGE，而 vault 不在白名單裡 —— 護送成功的人
   只要重整一次分頁，金庫就消失了，而且不會有任何錯誤訊息。 */
console.log('\n=== 存下來的東西真的存得住 ===');
V.vault = 1; V.npcDone = 1; api.saveVillage(); api.loadVillage();
ok(api.VILLAGE().vault === 1, 'Token 金庫撐得過重新讀檔');
ok(api.VILLAGE().npcDone === 1, '「救過了」撐得過重新讀檔');

console.log('\n%d 項，%d 失敗', total, fail);
process.exit(fail ? 1 : 0);
