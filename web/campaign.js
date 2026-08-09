// 戰役走通測試：一章一章打下去，看每一章是不是「打得完」。
//
// sim.js 量的是「一趟能走多深」，這一支量的是完全不同的東西 ——
// 十五章裡有沒有哪一章因為數值配錯而根本過不去。
// 一場死了就重來（跟真的玩家一樣，進度留在村莊），最多重試 N 次。
const { api } = require('./simcore.js');

// 30 層的通天塔一趟就要好幾千回合 —— 上限太低會把「打得完」誤判成「過不去」
const MAX_TURNS = 16000, RETRY = 40;

function playFloorLoop(G, cap){
  let t = 0;
  while(!G.over && t < cap){
    const p = G.p;
    const food = p.inv.find(i => i.cat === 'food');
    if(p.sat < 25000 && food){ api.useItem(food, false); api.endTurn(); t++; continue; }
    if(p.hp * 2 < p.mhp){
      const h = p.inv.find(i => i.cat === 'herb' && i.id === 'heal' && G.known['herb/heal']);
      if(h){ api.useItem(h, false); api.endTurn(); t++; continue; }
    }
    if(p.hp === p.mhp){
      const unk = p.inv.find(i => i.cat === 'herb' && !G.known['herb/' + i.id]);
      if(unk){ api.useItem(unk, false); api.endTurn(); t++; continue; }
    }
    const best = (cat, cur) => p.inv.filter(i => i.cat === cat && !i.cursed)
      .reduce((a, b) => {
        const v = x => (cat === 'weap' ? x.d.atk : x.d.def) + x.up * 2;
        return !a || v(b) > v(a) ? b : a;
      }, cur);
    const bw = best('weap', p.weap), bs = best('shld', p.shld);
    if(bw && bw !== p.weap){ p.weap = bw; bw.known = 1; api.endTurn(); t++; continue; }
    if(bs && bs !== p.shld){ p.shld = bs; bs.known = 1; api.endTurn(); t++; continue; }

    let hit = false;
    for(const d of api.DIRS){
      const m = api.monAt(p.x + d[0], p.y + d[1]);
      if(m && api.cornerOK(p.x, p.y, p.x + d[0], p.y + d[1])){ api.tryMove(d[0], d[1]); hit = true; break; }
    }
    if(hit){ t++; continue; }

    const k = api.key(p.x, p.y), here = G.items[k];
    if(here && !here.shop && p.inv.length < 20){
      p.inv.push(here); delete G.items[k];
      if(here.cat === 'weap' && !p.weap){ p.weap = here; here.known = 1; }
      if(here.cat === 'shld' && !p.shld){ p.shld = here; here.known = 1; }
      api.endTurn(); t++; continue;
    }
    if(api.tileAt(p.x, p.y) === api.DOWN && !G.f.bossLock){ api.descend(); t++; continue; }

    let goal = G.f.stairs;
    if(G.f.bossLock){
      let b = null, bd = 1e9;
      for(const m of G.mons){
        const dd = Math.max(Math.abs(m.x - p.x), Math.abs(m.y - p.y));
        if(dd < bd){ bd = dd; b = {x:m.x, y:m.y}; }
      }
      if(b) goal = b;
    } else if(p.inv.length < 20){
      let b = null, bd = 1e9;
      for(const ik in G.items){
        if(G.items[ik].shop) continue;
        const ix = ik % api.MW, iy = (ik / api.MW) | 0;
        const dd = Math.max(Math.abs(ix - p.x), Math.abs(iy - p.y));
        if(dd < bd){ bd = dd; b = {x:ix, y:iy}; }
      }
      if(b) goal = b;
    }
    const step = api.nextStep(G, {x:p.x, y:p.y}, goal);
    if(!step){ api.endTurn(); t++; continue; }
    api.tryMove(step[0], step[1]);
    t++;
  }
  return t;
}

/* 出發前先去一趟鐵匠鋪。
   這不是在幫機器人作弊 —— 從「進下一章不再白送裝備」開始，村莊就是
   取得裝備的**正規途徑**：打完一章帶回來的錢，換下一章的一把劍。
   機器人如果不進村就下去，量到的是「一個不玩村莊的人」，
   那不是這款遊戲的玩法，測出來的難度也不是玩家會遇到的難度。
   買最貴的買得起的那一件，跟真人會做的事一樣。 */
function shopTrip(V){
  const stat = c => c === 'weap' ? 'atk' : 'def';
  // 手上那件的實力（含強化）。已經有一把好的就不再買第二把 ——
  // 每次重來都再買一把，錢會全部漏在重複的裝備上，永遠攢不到強化的錢。
  const held = cat => V.stock.filter(g => g.cat === cat)
    .reduce((n, g) => Math.max(n, (api.defOf(g.cat, g.id)[stat(cat)] || 0) + g.up * 2), 0);
  for(const cat of ['weap', 'shld']){
    /* 挑「數值」最高的，不是最貴的。鏡之盾比鋼之盾貴一倍，防禦卻是 6 對 7 ——
       它貴在反射。照價格挑的結果是每一章都買到比該有的差一階的盾，
       而減傷是 (15/16)^防禦 的指數式，差一點防禦在深層差很多。 */
    const k = stat(cat);
    const want = api.VILLAGE_STOCK.filter(g => g.cat === cat)
      .map(g => ({g, d: api.defOf(g.cat, g.id)}))
      .filter(o => o.d.price <= V.gold)
      .reduce((a, b) => !a || (b.d[k]||0) > (a.d[k]||0) ? b : a, null);
    if(!want || (want.d[k] || 0) <= held(cat)) continue;
    V.gold -= want.d.price;
    V.stock.push({cat, id: want.g.id, up: 0});
  }
  /* 剩下的錢全部拿去鍛造。到了第十三章，鐵匠鋪最貴的那一把也追不上怪物表 ——
     深章節真正的成長來自「把手上這把打得更利」，而裝備買下就是你的，
     不會磨損，所以錢沒有必要留著重買。 */
  for(let i = 0; i < 40; i++){
    const best = V.stock
      .map(g => ({g, d: api.defOf(g.cat, g.id)}))
      .filter(o => o.g.up < (o.d.up || 0))
      .map(o => Object.assign(o, {cost: api.forgeCost(o.d, o.g.up)}))
      .filter(o => o.cost <= V.gold)
      .reduce((a, b) => !a || b.cost < a.cost ? b : a, null);
    if(!best) break;
    V.gold -= best.cost; best.g.up++;
  }
}

const V = api.VILLAGE();
V.act = 0;
const ACTS = api.ACTS;
const log = [];
let seed = 101, stuck = null;

for(let a = 0; a < ACTS.length; a++){
  let tries = 0, done = false, deepest = 0; const cause = {};
  while(tries < RETRY && !done){
    tries++;
    V.act = a;
    shopTrip(V);
    api.newGame(seed++);
    const G = api.G();
    const t = playFloorLoop(G, MAX_TURNS);
    if(G.floor > deepest){ deepest = G.floor; }
    // 通關的判定：村莊裡的章節指標往前走了，或者這是最後一章而且贏了
    if((V.act | 0) > a || G.won) done = true;
    else cause[G.p.hp <= 0 ? '死亡' : (t >= MAX_TURNS ? '回合上限' : '其他')] =
         (cause[G.p.hp <= 0 ? '死亡' : (t >= MAX_TURNS ? '回合上限' : '其他')] || 0) + 1;
  }
  log.push({ act: a + 1, nm: ACTS[a].nm, floors: ACTS[a].floors,
             tries, deepest, done, cause: Object.assign({}, cause) });
  // 過不去也要繼續測後面的章節 —— 停在第一個失敗，後面兩章就永遠沒被測到
  if(!done){ if(stuck === null) stuck = a; V.act = a + 1; }
}

console.log('=== 戰役走通測試（每章最多重試 %d 次）===\n', RETRY);
let bad = 0;
for(const r of log){
  const mark = r.done ? '✓' : '✗';
  const pad = (v, n) => String(v).padStart(n);
  console.log('%s 第%s章 %s %s層　嘗試 %s 次　最深第 %s 層%s',
    mark, pad(r.act,2), (r.nm + '　　　　').slice(0,6), pad(r.floors,2),
    pad(r.tries,2), pad(r.deepest,2),
    r.done ? '' : '　← 過不去（' + Object.entries(r.cause).map(c=>c[0]+' '+c[1]).join('／') + '）');
  if(!r.done) bad++;
}
console.log('\n通過 %d / %d 章', log.filter(r => r.done).length, ACTS.length);
if(stuck !== null) console.log('卡在第 %d 章「%s」', stuck + 1, ACTS[stuck].nm);
process.exit(bad ? 1 : 0);
