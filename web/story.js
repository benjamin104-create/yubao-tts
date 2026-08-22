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

const ALL_ACTS = api.i18n.ACTS;
/* 路線的形狀只看**主線**。副本迷宮（side:1）接在陣列尾巴，
   它不在「神殿 → 往下 → 大廣間 → 往上」那條線上 ——
   把它算進來的話，「最後一章在塔上」會變成假的，
   而那條斷言要釘的事情其實一點都沒有壞。 */
const ACTS = ALL_ACTS.filter(a => !a.side);
const AI = id => ALL_ACTS.findIndex(a => a.id === id);

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

/* ═══ 神殿的平面 ═══════════════════════════════════════════════
   使用者：「我需要一個立體神殿的類似像『入口迷宮』的設定場景」，
   而「立體」選的是「俯視＋看得出高低」。

   這一段驗的是那座建築真的長成建築：一條中軸、對稱的側室、
   越往裡越高的台基。全部都是不會報錯的東西 —— 生成器退回
   3x3 隨機房間，遊戲照樣跑得完，只是神殿又變回一座貼皮的地牢。 */
console.log('\n=== 神殿的平面（中軸、側室、台基） ===');
{
  const V1 = api.VILLAGE();
  const AX = api.MW >> 1;
  let axisOK = 0, lvOK = 0, upward = 0, chambers = 0, maps = 0, sym = 0;
  const N = 200;   // 單邊的平面在原本的寫法下約 0.6% —— 四十張抽不到，兩百張才抽得到
  for(let seed = 1; seed <= N; seed++){
    V1.act = 0; api.newGame(seed);
    const g = api.G(); g.act = 0; g.floor = 1; api.buildFloor();
    const f = g.f, el = f.el;
    maps++;
    // (1) 中軸：從出生點那一列到樓梯那一列，中軸上每一格都走得到
    let solid = true;
    for(let y = f.stairs.y; y <= f.spawn.y; y++)
      if(!api.walkable(AX, y)) solid = false;
    if(solid) axisOK++;
    // (2) 三種高度都在
    const lvs = new Set();
    for(let k = 0; k < api.MW*api.MH; k++) if(f.t[k] !== 0) lvs.add(el[k]);
    if(lvs.has(0) && lvs.has(1) && lvs.has(2)) lvOK++;
    // (3) 越往裡越高：樓梯站在最高階，出生點站在最低階
    if(el[api.key(f.stairs.x, f.stairs.y)] === 2 &&
       el[api.key(f.spawn.x, f.spawn.y)] === 0) upward++;
    /* (4)(5) 側室：左右兩側都要有。內殿與前庭比側室高（h 都大於 4），
       所以用高度篩掉它們兩個，剩下的就是側室。 */
    let L = 0, R = 0;
    for(const k of Object.keys(f.rooms)){
      const r = f.rooms[k];
      if(r.h > 4) continue;
      if(r.x + r.w - 1 < AX) L++;
      else if(r.x > AX) R++;
    }
    chambers += L + R;
    if(L && R) sym++;
  }
  ok(maps === N, N + ' 張神殿圖都生得出來');
  ok(axisOK === N, '中軸從門口一路通到內殿（' + axisOK + '/' + N + ' 張）');
  ok(lvOK === N, '三種台基高度都在（' + lvOK + '/' + N + ' 張）');
  ok(upward === N, '樓梯在最高階、出生點在最低階（' + upward + '/' + N + ' 張）');
  /* 左右都要有側室，一張都不能漏。各自擲骰的第一版在八顆種子裡就中了
     一顆全右邊的（三帶的左側都被跳過）—— 那不是變化，
     那是把這一章唯一的形狀特徵弄丟了。所以掃四十顆，而且要求全中。 */
  ok(sym === N, '每一張都是左右對稱的（' + sym + '/' + N + ' 張有兩側側室）');
  ok(chambers >= N * 3, '側室的數量夠（共 ' + chambers + ' 間 / ' + N + ' 張）');
}

/* ═══ 神殿的佈景：石灰岩、柱面、陽光 ═══════════════════════════
   使用者：「應該有柱面、有光影、外面有陽光灑進來」「神殿的佈景，
   應該是更純白色、或是沙地廢墟感，有雕像、有柱面的感覺」
   「可能會有窗或孔，讓陽光直射進來」。

   這一整段講的是**看起來像什麼**，而看起來像什麼是最容易安靜壞掉的
   —— 地貌表上打錯一個字，遊戲照跑，只是神殿又變回泥磚色的地牢。 */
console.log('\n=== 神殿的佈景（石灰岩、柱面、陽光） ===');
{
  const th = api.THEMES ? api.THEMES.temple : null;
  ok(!!th, '找得到神殿的地貌設定');
  if(th){
    // 石灰岩：色階要比泥磚亮。拿最亮的那一階跟礦坑比
    const lum = ch => { const h = api.PAL[ch].slice(1);
      return (parseInt(h.slice(0,2),16)*.3 + parseInt(h.slice(2,4),16)*.6
            + parseInt(h.slice(4,6),16)*.1); };
    const bright = r => lum(r[3]);
    /* 亮度要比礦坑高 —— 但只比**最亮那一階**是不夠的：泥磚色階的
       最亮階（#ecd3ae）其實比石灰岩還亮，暗的是它下面三階。
       所以比的是四階的平均。 */
    const avgLum = r => r.reduce((a, c) => a + lum(c), 0) / r.length;
    ok(avgLum(th.ramp) > avgLum(api.THEMES.stone.ramp) + 15,
       '神殿整體比礦坑亮（' + Math.round(avgLum(th.ramp)) + ' 對 ' +
       Math.round(avgLum(api.THEMES.stone.ramp)) + '）');
    /* 而且要是**石頭**不是泥土：石灰岩幾乎沒有彩度，泥磚是飽和的橙棕。
       只驗亮度的話，把色階換成更亮的黃土仍然會過，而那看起來是沙丘，
       不是使用者要的「純白色／沙地廢墟」。 */
    const sat = ch => { const h = api.PAL[ch].slice(1);
      const v = [0,2,4].map(i => parseInt(h.slice(i,i+2),16));
      return Math.max(...v) - Math.min(...v); };
    const avgSat = r => r.reduce((a, c) => a + sat(c), 0) / r.length;
    ok(avgSat(th.ramp) < 30,
       '石灰岩是灰的不是棕的（彩度 ' + Math.round(avgSat(th.ramp)) +
       '，礦坑是 ' + Math.round(avgSat(api.THEMES.stone.ramp)) + '）');
    // 色階要真的分得開，不然整章糊成一片
    const gaps = [1,2,3].map(i => lum(th.ramp[i]) - lum(th.ramp[i-1]));
    ok(gaps.every(g => g > 20), '四階拉得開（' + gaps.map(Math.round).join('/') + '）');
    ok(th.wall === 'fluted', '牆是柱面（fluted），不是釉磚');
    ok(th.floor === 'limestone', '地板是石灰岩，不是泥磚');
    ok(!!th.sun, '有陽光的旗標');
    ok(!!th.mark, '有雕像（守護獸像）');
  }

  const V3 = api.VILLAGE();
  let withSun = 0, brighter = 0, onFloor = 0, floors = 0, rays2 = 0, headBright = 0;
  for(const seed of [11, 22, 33, 44, 55, 66]){
    for(const fl of [1, 2, 3]){
      V3.act = 0; api.newGame(seed);
      const g = api.G(); g.act = 0; g.floor = fl; api.buildFloor();
      const L = g.f.litAt;
      floors++;
      if(!L || !L.size) continue;
      withSun++;
      /* 光只打在走得到的地板上。打在牆上的話那不是天窗，
         是貼在牆上的一塊黃色 —— 而且它會讓玩家以為那裡有路。 */
      let bad = 0;
      for(const k of L.keys()) if(g.f.t[k] === 0) bad++;
      if(!bad) onFloor++;
      /* 前庭（露天）要比內殿（只有一道天窗）亮。
         那條由亮到暗的曲線就是「往神殿深處走」這件事本身 ——
         反過來的話，玩家會覺得自己是從裡面往外走。 */
      const avg = (y0, y1) => {
        let sum = 0, n = 0;
        for(let y = y0; y <= y1; y++) for(let x = 1; x < api.MW-1; x++){
          const k = api.key(x, y);
          if(g.f.t[k] === 0) continue;
          sum += (L.get(k) || 0); n++;
        }
        return n ? sum / n : 0;
      };
      if(avg(23, 27) > avg(2, 8)) brighter++;
      /* 每一道光柱自己也要由亮到暗：靠窗那一頭最亮，越往下越散。
         反過來的話光是從地板長出來的，那不是天窗。
         上面那一條比的是「前庭 vs 內殿」，比不到單一道光柱的方向 ——
         前庭有三道、內殿只有一道，就算每一道都反過來，前庭還是比較亮。 */
      for(const ray of g.f.rays){
        const at = (yy, xx) => L.get(api.key(xx, yy)) || 0;
        const head = at(ray.y,              ray.x + 1);
        const tail = at(ray.y + ray.len - 1, ray.x + Math.round((ray.len-1)*0.5) + 1);
        if(head > 0 && tail > 0){ rays2++; if(head > tail) headBright++; }
      }
    }
  }
  ok(floors === 18 && withSun === 18, '每一層都有陽光（' + withSun + '/' + floors + '）');
  ok(onFloor === withSun, '光只打在走得到的地板上（' + onFloor + '/' + withSun + '）');
  ok(brighter === withSun,
     '前庭比內殿亮（' + brighter + '/' + withSun + ' 層）—— 越往裡走越暗');
  ok(rays2 > 40 && headBright === rays2,
     '每一道光柱都是靠窗那頭最亮（' + headBright + '/' + rays2 + ' 道）');
}

/* 別的章節沒有陽光。神殿是地面上的建築，那是它跟後面十六章最大的分野；
   到處都有陽光的話，那個分野就消失了 —— 而且每一格會多跑一次查表。 */
{
  const V3 = api.VILLAGE();
  let dark = 0, n = 0;
  for(const id of ['mine', 'forest', 'gaol', 'hall', 'tower']){
    const a = AI(id);
    V3.act = a; api.newGame(99);
    const g = api.G(); g.act = a; g.floor = 1; api.buildFloor();
    n++;
    if(!g.f.litAt || !g.f.litAt.size) dark++;
  }
  ok(dark === n, '神殿以外的章節沒有陽光（' + dark + '/' + n + '）');
}

/* 別的章節必須是平的。高低差的算圖只在「這一層有高低」時才跑 ——
   如果別的章節的 el 不小心也有值，那一段每一格會多跑四次查表，
   而且會在沒有台基的地方畫出立面與陰影。兩件事都不會報錯。 */
{
  const V1 = api.VILLAGE();
  let flat = 0, checked = 0;
  for(const id of ['mine', 'forest', 'gaol', 'hall', 'tower']){
    const a = AI(id);
    V1.act = a; api.newGame(99);
    const g = api.G(); g.act = a; g.floor = 1; api.buildFloor();
    checked++;
    if(g.f.el && !g.f.el.some(v => v > 0)) flat++;
  }
  ok(checked === 5 && flat === 5, '神殿以外的章節都是平的（' + flat + '/' + checked + '）');
}

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

/* ═══ 迷宮裡的臨時狀況 ═══════════════════════════════════════
   使用者：「在不同迷宮章節中，隨機出現臨時的『拯救』或『解謎』狀況」，
   而且究極武具要「拯救到對的村人」、頭環要「透過拯救或解謎」拿到。

   這一整段驗的是那句話真的成立：兩個事件各自是一件究極裝備的唯一來源，
   而且都可以拒絕、都不會把玩家關在樓層裡。 */
console.log('\n=== 什麼樣的樓層會出事件 ===');
{
  const A = id => ALL_ACTS[AI(id)];
  ok(!api.evOK(A('temple'), 1, false), '序章不出事件（那三層在教走路）');
  ok(!api.evOK(A('vault'), 1, false),  '副本迷宮不出事件（它本身就是獎勵）');
  ok(!api.evOK(A('ordeal'), 1, false), '競技場那一章不出事件');
  ok(!api.evOK(A('mine'), A('mine').floors, false), '頭目層不出事件');
  ok(!api.evOK(A('gaol'), 5, true),    '休息層不出事件（補給站中間插謎題等於沒有補給站）');
  ok(api.evOK(A('mine'), 2, false),    '一般的迷宮層會出事件');
}

/* 找一層真的長出指定事件的樓層。事件是隨機的，所以掃過去找 ——
   找不到就是機率或條件壞了，那本身就是要報出來的事。 */
function findEv(kind, prep){
  const V3 = api.VILLAGE();
  for(let seed = 1; seed <= 60; seed++){
    api.newGame(seed * 104729);
    prep(api.VILLAGE());
    const G4 = api.G();
    for(let a = 0; a < ALL_ACTS.length; a++){
      if(ALL_ACTS[a].side) continue;
      for(let f = 1; f <= ALL_ACTS[a].floors; f++){
        G4.act = a; G4.floor = f; G4.npc = null;
        api.buildFloor();
        if(G4.f.ev && G4.f.ev.kind === kind) return G4;
      }
    }
  }
  return null;
}
const noNpc = V4 => { V4.sideKey = 0; V4.circletDone = 0; V4.vault = 0; V4.npcDone = 1; };

console.log('\n=== 受困的石匠（拯救 → 副本迷宮） ===');
{
  /* 落石是真的會擋路的東西。第一版沒有連通複查，
     兩百多次裡有六次把樓梯關在牆的另一邊（2.5%）——
     那個機率小到單一種子看不見，但它的後果是「這一趟結束了」。
     所以這裡掃很多層，不是掃幾層。 */
  let seen = 0, blocked = 0;
  for(let seed = 1; seed <= 12; seed++){
    api.newGame(seed * 7919);
    noNpc(api.VILLAGE());
    const G5 = api.G();
    for(let a = 0; a < ALL_ACTS.length; a++){
      if(ALL_ACTS[a].side) continue;
      for(let f = 1; f <= ALL_ACTS[a].floors; f++){
        G5.act = a; G5.floor = f; G5.npc = null;
        api.buildFloor();
        const ev = G5.f.ev;
        if(!ev || ev.kind !== 'mason') continue;
        seen++;
        // 把落石當牆，從出生點走一遍，樓梯還到不到
        const vis = new Set([api.key(G5.p.x, G5.p.y)]);
        const q = [[G5.p.x, G5.p.y]];
        for(let h = 0; h < q.length; h++){
          const [cx, cy] = q[h];
          for(const d of api.DIRS){
            const nx = cx + d[0], ny = cy + d[1], k = api.key(nx, ny);
            if(vis.has(k) || !api.walkable(nx, ny)) continue;
            if(nx === ev.x && ny === ev.y) continue;
            if(!api.cornerOK(cx, cy, nx, ny)) continue;
            vis.add(k); q.push([nx, ny]);
          }
        }
        if(!vis.has(api.key(G5.f.stairs.x, G5.f.stairs.y))) blocked++;
      }
    }
  }
  ok(seen >= 40, '掃到夠多的落石（' + seen + ' 次，太少就驗不出 2.5% 的事）');
  ok(blocked === 0, '落石一次都沒有把樓梯關在外面（' + blocked + '/' + seen + '）');
}
{
  const G6 = findEv('mason', noNpc);
  ok(!!G6, '找得到有石匠的樓層');
  if(G6){
    const ev = G6.f.ev, V6 = api.VILLAGE();
    // 站到落石旁邊，然後撞過去
    let d0 = null;
    for(const d of api.DIRS){
      const sx = ev.x - d[0], sy = ev.y - d[1];
      if(api.walkable(sx, sy) && !api.monAt(sx, sy) && api.cornerOK(sx, sy, ev.x, ev.y)){
        G6.p.x = sx; G6.p.y = sy; d0 = d; break;
      }
    }
    ok(!!d0, '走得到落石旁邊');
    V6.sideKey = 0;
    api.tryMove(d0[0], d0[1]);
    ok(api.talkOpen(), '撞上去會先問，不會直接開挖');
    ok(ev.n === 0, '還沒答應之前一塊石頭都沒搬');
    api.answerTalk(false);
    ok(!ev.agreed, '按「不同意」不會開始搬（不救也可以）');
    api.tryMove(d0[0], d0[1]);
    ok(api.talkOpen(), '再撞一次會再問一次（反悔不該有代價）');
    api.answerTalk(true);
    ok(ev.agreed === 1, '按「同意」就開始搬');
    ok(V6.sideKey === 0, '答應的當下還沒開副本 —— 要真的搬完才算');
    /* 「搬幾次」不能只拿 MASON_DIG 自己去比 —— 那是拿常數驗常數，
       把它改成 1 測試照樣全綠（破壞測試就是這樣抓到的）。
       要釘的其實是「拯救有代價」：至少三回合，而且第一下挖不出來。 */
    ok(api.MASON_DIG >= 3, '搬石頭至少要三回合（實際 ' + api.MASON_DIG + '）—— 一下就好等於沒有代價');
    api.tryMove(d0[0], d0[1]);
    ok(ev.n === 1 && !ev.done, '第一下搬不出來（' + ev.n + '/' + api.MASON_DIG + '）');
    ok(V6.sideKey === 0, '搬到一半副本還沒開');
    for(let i = 1; i < api.MASON_DIG - 1; i++) api.tryMove(d0[0], d0[1]);
    ok(ev.n === api.MASON_DIG - 1, '每撞一次搬一塊（' + ev.n + '/' + api.MASON_DIG + '）');
    ok(V6.sideKey === 0, '差一塊的時候副本還沒開');
    api.tryMove(d0[0], d0[1]);
    ok(ev.done === 1, '搬滿 ' + api.MASON_DIG + ' 次就把人挖出來了');
    ok(V6.sideKey === 1, '★ 石匠獲救 → 祕匠的副本開了');
    api.saveVillage(); api.loadVillage();
    ok(api.VILLAGE().sideKey === 1, '副本的鑰匙撐得過重新讀檔');
  }
}

console.log('\n=== 記憶的石碑（解謎 → 賢者頭環） ===');
{
  const G7 = findEv('stones', V7 => { V7.sideKey = 1; V7.circletDone = 0; V7.vault = 0; V7.npcDone = 1; });
  ok(!!G7, '找得到有石碑的樓層');
  if(G7){
    const ev = G7.f.ev, V8 = api.VILLAGE();
    const at = el => ev.stones.find(s => s.el === el);
    const stepTo = pt => { G7.p.x = pt.x; G7.p.y = pt.y; api.stepOn(); };
    // 四塊碑要散得開 —— 兩塊並排的話「照順序踩」讀不出是四個地方
    let mind = 99;
    for(let i = 0; i < ev.stones.length; i++)
      for(let j = i + 1; j < ev.stones.length; j++)
        mind = Math.min(mind, Math.max(Math.abs(ev.stones[i].x - ev.stones[j].x),
                                       Math.abs(ev.stones[i].y - ev.stones[j].y)));
    ok(mind >= 3, '四塊碑彼此至少三格（最近的兩塊差 ' + mind + ' 格）');
    ok(ev.order.length === 4 && new Set(ev.order).size === 4, '順序是四個不重複的記號');

    /* 沒讀石板就踩，什麼都不該發生 —— 連「錯」都不算。
       看不懂的東西不該罰人，而這一條同時也是「不能靠試誤解開」：
       沒讀石板的人根本推不動這個謎題。 */
    stepTo(at(ev.order[0]));
    ok(ev.step === 0 && !at(ev.order[0]).lit, '沒讀石板就踩碑，碑不會亮');
    stepTo(ev.slab);
    ok(ev.read === 1, '踩上石板就讀到了順序');

    stepTo(at(ev.order[0]));
    ok(at(ev.order[0]).lit === 1 && ev.step === 1, '照順序踩第一塊，碑亮了');
    stepTo(at(ev.order[0]));
    ok(ev.step === 1, '再踩一次已經亮的碑不算數（走回頭路不該被罰）');
    stepTo(at(ev.order[2]));
    ok(ev.step === 0 && ev.stones.every(s => !s.lit), '踩錯順序，四塊碑一起熄滅');

    ok(!V8.circletDone, '還沒解開之前沒有頭環');
    const bag0 = G7.p.inv.length;
    for(const el of ev.order) stepTo(at(el));
    ok(ev.done === 1, '重來一次、四塊踩完就解開了');
    ok(V8.circletDone === 1, '★ 解謎完成 → 賢者頭環到手');
    ok((V8.ult.circlet | 0) > 0, '頭環記的是「趟數」，不是一件會隨死亡消失的物件');
    ok(G7.p.inv.length === bag0 + 1, '這一趟身上就多了一只頭環');
    const cir = G7.p.inv.find(i => i.d && i.d.id === 'circlet');
    ok(!!cir && cir.ultLeft > 0, '頭環身上帶著剩餘趟數（' + (cir ? cir.ultLeft : '-') + '）');
    api.saveVillage(); api.loadVillage();
    ok(api.VILLAGE().circletDone === 1, '解過的謎撐得過重新讀檔');
    ok((api.VILLAGE().ult.circlet | 0) > 0, '頭環的趟數撐得過重新讀檔');
  }
}

/* 「其他取得路徑改成不可」。這三件東西如果還能在地上撿到、
   在鐵匠鋪買到，那前面整段拯救與解謎就只是一條繞遠路的支線。 */
console.log('\n=== 究極裝備只有這兩條路 ===');
{
  const ULT = new Set(api.ULT_IDS);
  ok(!api.OPEN_HAT.some(h => ULT.has(h.id)), '究極頭環不在一般的帽子池裡');
  ok(!api.VILLAGE_STOCK.some(g => ULT.has(g.id)), '究極裝備不在村莊商店的貨架上');
  let dropped = 0;
  for(let seed = 1; seed <= 8; seed++){
    api.newGame(seed * 31337);
    const G9 = api.G();
    for(let a = 0; a < ALL_ACTS.length; a++){
      if(ALL_ACTS[a].side) continue;
      for(let f = 1; f <= ALL_ACTS[a].floors; f++){
        G9.act = a; G9.floor = f; G9.npc = null;
        api.buildFloor();
        for(const k of Object.keys(G9.items))
          if(G9.items[k] && G9.items[k].d && ULT.has(G9.items[k].d.id)) dropped++;
      }
    }
  }
  ok(dropped === 0, '走了幾千層，地上一件究極裝備都沒有掉（' + dropped + ' 件）');
}

/* Token 金庫要撐得過重新整理。這一條是踩出來的：loadVillage() 會用
   白名單重建一整個 VILLAGE，而 vault 不在白名單裡 —— 護送成功的人
   只要重整一次分頁，金庫就消失了，而且不會有任何錯誤訊息。 */
console.log('\n=== 存下來的東西真的存得住 ===');
/* 用 api.VILLAGE() 現拿，不要用開頭抓的那個 V —— loadVillage() 會
   用白名單**重建**一整個 VILLAGE 物件，抓在手上的舊參考從那一刻起
   就指著一個沒有人在看的東西了。 */
{
  const Vn = api.VILLAGE();
  Vn.vault = 1; Vn.npcDone = 1;
}
api.saveVillage(); api.loadVillage();
ok(api.VILLAGE().vault === 1, 'Token 金庫撐得過重新讀檔');
ok(api.VILLAGE().npcDone === 1, '「救過了」撐得過重新讀檔');

console.log('\n%d 項，%d 失敗', total, fail);
process.exit(fail ? 1 : 0);
