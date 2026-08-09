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
  // 一件裝備的「潛力」＝ 打滿之後的數值。真人挑的是潛力不是現值 ——
  // 秘銀 +0（攻 14）確實比鋼劍 +5（攻 18）弱，但秘銀打得到 +8（攻 30），
  // 鋼劍打到 +5 就到頂了。只看現值的話會永遠停在鋼劍上，
  // 錢愈攢愈多卻沒地方花（第一版量到的就是這個：第十五章手上十四萬）。
  const pot = (cat, id, up) => {
    const d = api.defOf(cat, id);
    return (d[stat(cat)] || 0) + Math.max(up|0, d.up || 0) * 2;
  };
  for(const cat of ['weap', 'shld']){
    const best = V.stock.filter(g => g.cat === cat)
      .reduce((n, g) => Math.max(n, pot(cat, g.id, g.up)), 0);
    const want = api.VILLAGE_STOCK.filter(g => g.cat === cat)
      .map(g => ({g, d: api.defOf(g.cat, g.id)}))
      .filter(o => o.d.price <= V.gold && pot(cat, o.g.id, 0) > best)
      .reduce((a, b) => !a || b.d.price > a.d.price ? b : a, null);
    if(!want) continue;
    V.gold -= want.d.price;
    V.stock.push({cat, id: want.g.id, up: 0});
  }
  /* 錢全部拿去鍛造，而且挑「潛力最高的那一件」往上打 ——
     鐵匠鋪最好的一把到第十三章就追不上怪物表了，深章節真正的成長
     來自把手上這把打得更利。裝備買下就是你的，不會磨損，
     所以沒有必要留一筆重買的錢。 */
  for(let i = 0; i < 60; i++){
    const cand = V.stock
      .map(g => ({g, d: api.defOf(g.cat, g.id)}))
      .filter(o => o.g.up < (o.d.up || 0))
      .map(o => Object.assign(o, {cost: api.forgeCost(o.d, o.g.up),
                                  pot: pot(o.g.cat, o.g.id, o.g.up)}))
      .filter(o => o.cost <= V.gold)
      .reduce((a, b) => !a || b.pot > a.pot ? b : a, null);
    if(!cand) break;
    V.gold -= cand.cost; cand.g.up++;
  }
}

const V = api.VILLAGE();
V.act = 0;
const ACTS = api.ACTS;
const log = [];
let seed = 101, stuck = null;
// 中段章節：此時鐵匠鋪還有東西可買、也還鍛造得動，錢應該是緊的
const MID = Math.min(12, ACTS.length - 1);
let midGold = 0;

for(let a = 0; a < ACTS.length; a++){
  let tries = 0, done = false, deepest = 0; const cause = {};
  while(tries < RETRY && !done){
    tries++;
    V.act = a;
    shopTrip(V);
    if(a === MID && tries === 1) midGold = V.gold;
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

/* ── 經濟：錢有沒有地方花 ────────────────────────────────────
   這一條是被量出來才加上去的。通關賞金第一版寫 depth*120，
   結果打到第十五章手上躺著十四萬金幣沒地方花 —— 十五章全過、
   每一支測試都綠燈，但村莊已經不是一個決定了：不管買什麼都買得起。

   「錢花不完」不會讓任何東西壞掉，所以沒有測試會發現它。
   量的是走到最後一章之前（此時鐵匠鋪還有東西可買）身上剩多少。 */
const CAP = 20000;
const spare = midGold;
console.log('第 %d 章出發時的閒錢：%d G（上限 %d）', MID + 1, spare, CAP);
if(spare > CAP){
  console.log('✗ 錢多到花不完 —— 賞金或鍛造價需要重新配');
  bad++;
}
process.exit(bad ? 1 : 0);
