// 音樂資料檢查：十八章各自該有一首，而且資料要長得對。
//
// 曲子聽不聽得出來要靠耳朵，但「這一章根本沒配到曲子」「第三小節少了旋律」
// 這種錯不需要耳朵 —— 而且它不會報錯，只會安靜地退回礦坑主題。
// 這正是這個專案一路上最常踩的那種坑：加了東西，但沒有接上。
const { api } = require('./simcore.js');
const assert = require('assert');

const TRACKS = api.BGM.TRACKS;
const ACT_THEME = api.ACT_THEME;
let pass = 0, fail = 0;
function t(name, fn){
  try { fn(); console.log('✓ ' + name); pass++; }
  catch(e){ console.log('✗ ' + name + '\n    ' + e.message); fail++; }
}

t('每一章都對應得到一首曲子', ()=>{
  for(const a of api.ACTS){
    const theme = ACT_THEME[a.id];
    assert(theme, a.nm + ' 沒有地貌');
    assert(TRACKS[theme], a.nm + '（' + theme + '）沒有曲子');
  }
});

t('每一首曲子的四個小節都寫滿了', ()=>{
  for(const id in TRACKS){
    const tr = TRACKS[id];
    assert.strictEqual(tr.root.length, 4, id + ' 的低音不是四小節');
    assert.strictEqual(tr.chord.length, 4, id + ' 的和弦不是四小節');
    assert.strictEqual(tr.lead.length, 4, id + ' 的旋律不是四小節');
    for(const bar of tr.lead)
      assert(bar.length > 0, id + ' 有一小節沒有旋律');
    for(const bar of tr.chord)
      assert(bar.length >= 3, id + ' 有一個和弦少於三個音');
  }
});

/* 鼓與低音的編排有兩種形狀：一整首共用一組步數，或四小節各一組
   （詠嘆調用的 —— 前兩小節不進伴奏）。兩種都要驗，而且要驗到底層的數字，
   不能只驗最外層是不是陣列：巢狀的那一種如果只看外層，
   裡面塞了什麼都會過。 */
const steps = lane => !lane ? []
  : Array.isArray(lane[0]) ? [].concat.apply([], lane) : lane;

t('所有音符都落在一小節之內、音高在可聽範圍', ()=>{
  for(const id in TRACKS){
    const tr = TRACKS[id];
    for(const bar of tr.lead) for(const [s, n, d, gl, vb] of bar){
      assert(s >= 0 && s < 16, id + ' 有音符起點在小節外：' + s);
      assert(d >= 1 && s + d <= 24, id + ' 有音符長度異常：' + s + '+' + d);
      assert(n >= 36 && n <= 96, id + ' 的音高離譜：' + n);
      // 滑音的目標也是一個音高，一樣會被送進振盪器 —— 打錯字的話
      // 那一顆會滑到聽不見的地方，而且不會報錯，只會忽然消失一顆音
      if(gl !== undefined && gl !== 0)
        assert(gl >= 36 && gl <= 96, id + ' 的滑音目標離譜：' + gl);
      if(vb !== undefined)
        assert(vb >= 0 && vb <= 100, id + ' 的顫音深度離譜：' + vb + ' 音分');
    }
    for(const lane of ['bass','hat','kick','tom','arp']){
      if(!tr[lane]) continue;
      if(Array.isArray(tr[lane][0]))
        assert.strictEqual(tr[lane].length, 4,
          id + ' 的 ' + lane + ' 分小節寫但不是四小節');
      for(const k of steps(tr[lane]))
        assert(k >= 0 && k < 16, id + ' 的 ' + lane + ' 有步數落在小節外：' + k);
    }
    assert(tr.bpm >= 60 && tr.bpm <= 160, id + ' 的速度異常：' + tr.bpm);
  }
});

t('十八章至少聽得到十首不同的迷宮主題', ()=>{
  const used = new Set(api.ACTS.map(a => ACT_THEME[a.id]));
  assert(used.size >= 10, '只有 ' + used.size + ' 首 —— 整趟聽起來會像同一首');
});

t('鏡像世界的曲子真的是礦坑主題的倒影', ()=>{
  const st = TRACKS.stone.lead, mi = TRACKS.mirror.lead;
  for(let b = 0; b < 4; b++){
    assert.strictEqual(mi[b].length, st[b].length, '第 ' + b + ' 小節音數對不上');
    // 音高集合要是原曲以 A4 為軸的倒影（順序會因為節奏翻轉而改變）
    const a = st[b].map(x => 138 - x[1]).sort((x,y)=>x-y);
    const c = mi[b].map(x => x[1]).sort((x,y)=>x-y);
    assert.deepStrictEqual(c, a, '第 ' + b + ' 小節的音高不是倒影');
    // 節奏也要翻：第 k 步的音變成第 (16-k-長度) 步
    const ra = st[b].map(x => 16 - x[0] - x[2]).sort((x,y)=>x-y);
    const rc = mi[b].map(x => x[0]).sort((x,y)=>x-y);
    assert.deepStrictEqual(rc, ra, '第 ' + b + ' 小節的節奏沒有翻過來');
  }
  // 倒影之後方向要真的相反：原曲往上走的地方，鏡像要往下走
  const dir = bars => Math.sign(bars[0][1][1] - bars[0][0][1]);
  assert.strictEqual(dir(mi), -dir(st), '倒影之後旋律的方向沒有反過來');
});

t('每一首的鼓組編排都不一樣（不然只是換了音高的同一首）', ()=>{
  const sig = id => {
    const tr = TRACKS[id];
    return [tr.bpm, steps(tr.bass).join(','), steps(tr.hat).join(','),
            steps(tr.kick).join(','), steps(tr.tom).join(',')].join('|');
  };
  const seen = new Map();
  for(const id in TRACKS){
    const s = sig(id);
    if(seen.has(s)) throw new Error(id + ' 跟 ' + seen.get(s) + ' 的速度與鼓組完全一樣');
    seen.set(s, id);
  }
});

/* ═══ 參考曲的語彙 ═══════════════════════════════════════════
   使用者點名了幾組參考（《深入地心》、神祕森林、中亞／巴比倫、
   《第五元素》的女伶）。抄旋律是不行的 —— 那是別人的著作；
   抄的是語彙：哪個音階、低音怎麼動、和弦怎麼疊。

   而「語彙」正是那種改壞了不會報錯的東西：把增二度改掉、把增三和弦
   改成大三和弦，曲子照樣播得出來、四小節照樣寫滿，只是它不再像那個地方。
   所以每一項都寫成一條可以量的斷言。 */
const PC = n => ((n % 12) + 12) % 12;

t('神殿與通天塔用的是 Hijaz（中亞／巴比倫的那個增二度）', ()=>{
  // D Hijaz：D E♭ F♯ G A B♭ C = 音級 2,3,6,7,9,10,0
  const HIJAZ = new Set([2,3,6,7,9,10,0]);
  for(const id of ['temple','spire']){
    const tr = TRACKS[id];
    const bad = [];
    for(const bar of tr.lead) for(const [,n,,gl] of bar){
      if(!HIJAZ.has(PC(n))) bad.push(n);
      if(gl && !HIJAZ.has(PC(gl))) bad.push(gl);
    }
    assert(!bad.length, id + ' 的旋律有音不在 Hijaz 上：' + bad.join('/'));
    // 光是「音都在音階裡」還不夠 —— 那個增二度必須真的被走過，
    // 不然整首可以只用 D 小調那幾個音，聽起來就不是那個地方了
    let jump = false;
    for(const bar of tr.lead) for(let i = 1; i < bar.length; i++)
      if(Math.abs(bar[i][1] - bar[i-1][1]) === 3 &&
         ((PC(bar[i][1]) === 6 && PC(bar[i-1][1]) === 3) ||
          (PC(bar[i][1]) === 3 && PC(bar[i-1][1]) === 6))) jump = true;
    assert(jump, id + ' 從頭到尾沒有走過 E♭–F♯ 那個增二度 —— 那是整個音階的簽名');
  }
});

t('神殿是持續低音，通天塔的低音自己爬過那個增二度', ()=>{
  assert(TRACKS.temple.drone, '神殿沒有持續低音 —— 低音一走動就變回西方和聲');
  assert(new Set(TRACKS.temple.root).size === 1, '神殿的低音有在動');
  const r = TRACKS.spire.root;
  assert(!TRACKS.spire.drone, '通天塔不該是持續低音 —— 它要往上爬');
  for(let i = 1; i < r.length; i++)
    assert(r[i] > r[i-1], '通天塔的低音第 ' + i + ' 小節沒有往上：' + r.join(','));
  assert(r.some((_, i) => i && r[i] - r[i-1] === 3),
         '通天塔的低音沒有爬過增二度（' + r.join(',') + '）');
});

t('迷霧森林是全音音階 —— 沒有半音就沒有解決，那就是「神祕」', ()=>{
  const tr = TRACKS.forest;
  const WT = new Set([0,2,4,6,8,10]);
  for(const bar of tr.lead) for(const [,n] of bar)
    assert(WT.has(PC(n)), '森林的旋律有音不在全音階上：' + n);
  for(const bar of tr.chord){
    const iv = bar.map(n => PC(n - bar[0])).sort((a,b)=>a-b);
    assert.deepStrictEqual(iv, [0,4,8],
      '森林的和弦不是增三和弦（' + bar.join(',') + '）—— 大三和弦會把主音指出來');
  }
  for(let i = 1; i < tr.root.length; i++)
    assert.strictEqual(tr.root[i] - tr.root[i-1], 2,
      '森林的低音沒有照全音階一階一階走');
});

t('礦坑的和弦沒有三音，低音半音往下（往地底下去的聲音）', ()=>{
  const tr = TRACKS.stone;
  for(let i = 1; i < tr.root.length; i++)
    assert.strictEqual(tr.root[i] - tr.root[i-1], -1,
      '礦坑的低音沒有半音往下：' + tr.root.join(','));
  for(const bar of tr.chord){
    const iv = new Set(bar.map(n => PC(n - bar[0])));
    assert(!iv.has(3) && !iv.has(4),
      '礦坑的和弦裡有三音（' + bar.join(',') + '）—— 有了三音就有大小調，' +
      '而這一章要的是「空」，不是「悲傷」');
  }
});

t('十九位頭目都有對應戰鬥配樂，而且至少八種戰鬥語彙', ()=>{
  assert.strictEqual(api.BOSS.length, 19, '頭目表數量改了，音樂驗收也要一起更新');
  const used = new Set();
  for(const d of api.BOSS){
    assert(d.bgm, d.nm + ' 沒有 bgm，會悄悄退回通用快歌');
    assert(TRACKS[d.bgm], d.nm + ' 的 bgm 指向不存在的曲子：' + d.bgm);
    used.add(d.bgm);
  }
  assert(used.size >= 8, '十九位王只有 ' + used.size + ' 種配樂語彙');
  const mind=['b_mind1','b_mind2','b_mind'].map(id=>api.BOSS.find(d=>d.id===id).bgm);
  assert.strictEqual(new Set(mind).size,3,'意識三型態沒有隨型態進化音樂：'+mind.join('/'));
  assert.strictEqual(api.BOSS.find(d=>d.id==='b_mermaid').bgm,'diva',
    '人魚王后沒有保留詠嘆調');
});

t('人魚王后有自己的一首，而且前半讓開、後半才進伴奏', ()=>{
  const q = api.BOSS.find(d => d.id === 'b_mermaid');
  assert(q, '找不到人魚王后');
  assert.strictEqual(q.bgm, 'diva', '人魚王后沒有指定自己的曲子');
  assert(TRACKS[q.bgm], '指定了 ' + q.bgm + ' 但那首曲子不存在');
  // 每一隻寫了 bgm 的都要指得到真的曲子（打錯字的話會安靜地退回通用頭目曲）
  for(const d of api.BOSS)
    if(d.bgm) assert(TRACKS[d.bgm], d.nm + ' 的 bgm 指向不存在的曲子：' + d.bgm);
  const tr = TRACKS.diva;
  assert(Array.isArray(tr.kick[0]), '詠嘆調的鼓沒有分小節寫 —— 伴奏就不會「後來才進來」');
  assert.strictEqual(tr.kick[0].length, 0, '第一小節就有鼓了，聲音會被蓋住');
  assert(tr.kick[3].length > tr.kick[1].length, '後半的鼓沒有比前半密');
  // 前半是人聲（滑音＋顫音），後半是唱不出來的（不滑也不抖）
  const has = (bar, idx) => TRACKS.diva.lead[bar].some(n => n[idx]);
  assert(has(0,4) || has(1,4), '前半沒有顫音 —— 沒有顫音就不像有人在唱');
  assert(has(0,3) || has(1,3), '前半沒有滑音 —— 那些滑上去的大跳是這一段的識別');
  assert(!has(2,4) && !has(3,4), '後半還在抖 —— 後半要的是機器的準確度');
  const fast = TRACKS.diva.lead[2].filter(n => n[2] === 1).length;
  assert(fast >= 10, '後半只有 ' + fast + ' 顆十六分音符 —— 快不起來就沒有那個轉折');
});

/* 怪物之間的音樂：踏進大廳音樂繃緊，離開這一層才鬆開。
   這是「加了東西但沒有接上」的最典型現場 —— 曲子寫好了、
   force() 也存在，但沒有人呼叫它，而不呼叫不會報錯。 */
t('踏進怪物之間，音樂會切成緊張的那一首', ()=>{
  const BGM = api.BGM;
  // 找一層真的有怪物之間的樓層。它從第 6 層起、機率 16%，
  // 所以要掃一陣子 —— 掃不到就是生成那一段壞了，一樣該紅。
  let found = 0;
  for(let s = 1; s <= 40 && !found; s++){
    api.newGame(s);
    const G = api.G();
    // 第一章整章不會有大廳，而且每一章的最後一層是頭目層 ——
    // 所以要真的照章節走，不能把 floor 直接加到 18（那是不存在的樓層）。
    for(let a = 1; a < api.ACTS.length && !found; a++)
    for(let fl = 1; fl < api.ACTS[a].floors; fl++){
      G.act = a; G.floor = fl; api.buildFloor();
      if(!G.f.hall) continue;
      found = 1;
      BGM.force(null);
      api.bossWatch();
      assert.strictEqual(BGM.forced, null, '還沒踏進去就先緊張了');
      // 走進大廳
      const r = G.f.rooms[G.f.hall.room];
      G.p.x = r.x; G.p.y = r.y;
      // 房間雕過形狀，左上角不一定走得到 —— 找一格真的在裡面的
      for(let y = r.y; y < r.y + r.h; y++) for(let x = r.x; x < r.x + r.w; x++)
        if(api.walkable(x,y) && api.G().f.roomAt[api.key(x,y)] === G.f.hall.room){ G.p.x = x; G.p.y = y; }
      api.stepOn();
      api.bossWatch();
      assert.strictEqual(BGM.forced, 'hall', '踏進大廳了，音樂沒有變');
      // 離開這一層就該鬆開
      G.floor = fl + 1; api.buildFloor(); api.bossWatch();
      if(!G.f.hall) assert.strictEqual(BGM.forced, null, '下了一層，音樂還卡在緊張');
      break;
    }
  }
  assert(found, '掃了六十顆種子都生不出怪物之間');
  BGM.force(null);
});

/* 詠嘆調有沒有真的被叫出來。上面那一條只驗到「資料表上寫了 bgm」——
   而這個專案最常見的失效方式正是「寫了但沒有人讀」：
   bossWatch() 裡如果還是寫死 force('boss')，資料表那一行就完全沒有效果，
   遊戲照跑、頭目照打，只是那一場放的是跟前面十五場一樣的鼓點。 */
t('進入每個頭目房，音樂都真的切到那隻王指定的曲子', ()=>{
  const BGM=api.BGM,V=api.VILLAGE();
  for(let a=0;a<api.ACTS.length;a++){
    if(!api.ACTS[a].boss)continue;
    V.act=a;V.stock=[];V.pots=[];api.newGame(4242+a);
    const G=api.G();G.act=a;G.floor=api.ACTS[a].floors;api.buildFloor();
    const b=G.mons.find(m=>m.d.boss);
    assert(b,api.ACTS[a].nm+'的頭目層沒有王');
    BGM.force(null);G.f.bossLock=1;G.seen[api.key(b.x,b.y)]=2;api.bossWatch();
    assert.strictEqual(BGM.forced,b.d.bgm,
      b.d.nm+'看見了，但實際播放 '+BGM.forced+'（應為 '+b.d.bgm+'）');
  }
  BGM.force(null);
});

t('人魚王后的詠嘆調與守護者戰鼓不會互相外洩', ()=>{
  const BGM = api.BGM, V = api.VILLAGE();
  const a = api.ACTS.findIndex(x => x.id === 'tower');
  V.act = a; V.stock = []; V.pots = [];
  api.newGame(4242);
  const G = api.G();
  G.act = a; G.floor = api.ACTS[a].floors; api.buildFloor();
  const b = G.mons.find(m => m.d.boss);
  assert(b && b.d.id === 'b_mermaid', '塔頂那一層沒有人魚王后');
  BGM.force(null);
  // 看見她 —— 觸發點是「看得見」，不是踏進房間
  G.p.x = b.x + 1; G.p.y = b.y; api.vision();
  api.bossWatch();
  assert.strictEqual(BGM.forced, 'diva',
    '看見人魚王后了，音樂還是 ' + BGM.forced);

  // 對照組：礦坑守衛要回到厚重的守護者戰鼓，不能沿用詠嘆調。
  const m = api.ACTS.findIndex(x => x.id === 'mine');
  V.act = m; api.newGame(4242);
  const G2 = api.G();
  G2.act = m; G2.floor = api.ACTS[m].floors; api.buildFloor();
  const b2 = G2.mons.find(x => x.d.boss);
  assert(b2, '礦坑那一層沒有頭目');
  BGM.force(null);
  G2.p.x = b2.x + 1; G2.p.y = b2.y; api.vision();
  api.bossWatch();
  assert.strictEqual(BGM.forced, 'boss_guardian',
    '礦坑守衛放的是 ' + BGM.forced + ' —— 詠嘆調外洩到別的頭目身上了');
  BGM.force(null);
});

console.log('\n通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
