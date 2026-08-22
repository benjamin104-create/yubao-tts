// 自動遊玩模擬：邏輯錯誤要在 headless 抓到，而不是等玩家玩到第 10 層才炸。
// 執行環境與 API 由 simcore.js 提供（campaign.js 也用同一份）。
const { api } = require('./simcore.js');
const nextStep = api.nextStep;

const RUNS = 60, MAX_TURNS = 1500;
let stats = { deaths:0, cleared:0, starve:0, turns:0, floors:0, maxFloor:0, lv:0, items:0, used:0, errs:0, ident:0 };
// 死在哪一層的分佈。平均樓層會把「開場就死」藏起來 ——
// 玩家第一次的體驗是由前兩層決定的，那才是要盯的數字。
const deathAt = {};

for(let r=0; r<RUNS; r++){
  try{
    // 每一場都從第一章開始。VILLAGE 在同一個 process 裡是共用的，
    // 不重設的話第 2 場會從第 2 章開頭起跑，量到的就不是同一件事了。
    api.VILLAGE().act = 0;
    api.newGame(r*7919 + 13);
    const G = api.G();
    let t = 0;
    while(!G.over && t < MAX_TURNS){
      const p = G.p;
      /* 有人在跟你說話就先回答。對話框開著的時候方向鍵不會走路，
         漏了這一段的話機器人會卡在原地跑完一千五百回合，
         而且不會報錯 —— 只會看到「第一章忽然過不去了」。
         一律同意：機器人的工作是量「護送走不走得完」，不是量拒絕。 */
      if(api.talkOpen()){ api.answerTalk(true); continue; }
    /* 落石就順手搬開。機器人不會刻意去找事件，但它一定會走到旁邊 ——
       不搬的話石匠永遠救不出來，於是每走幾層就再生一堆新的落石，
       量到的會變成「一個永遠完成不了的事件」的成本，而不是玩家的成本
       （玩家救一次就結束了）。實測差別很大：不搬的版本通天塔要 39 趟。 */
    const evM = G.f && G.f.ev;
    if(evM && evM.kind === 'mason' && !evM.done &&
       Math.max(Math.abs(evM.x - p.x), Math.abs(evM.y - p.y)) === 1 &&
       api.cornerOK(p.x, p.y, evM.x, evM.y)){
      api.tryMove(Math.sign(evM.x - p.x), Math.sign(evM.y - p.y)); t++; continue;
    }
      // 餓了就吃
      const food = p.inv.find(i=>i.cat==='food');
      if(p.sat < 25000 && food){ api.useItem(food,false); api.endTurn(); stats.used++; t++; continue; }
      /* 中毒就解毒。機器人不會解毒的話，量到的是「玩家看到狀態列上的『毒』
         卻裝作沒看到」—— 那不是難度，那是把測試員當笨蛋。
         平衡要對著**會用道具的玩家**調，不然調出來的難度是給機器人的。 */
      if(p.st['毒']){
        const c = p.inv.find(i=>i.cat==='herb' && i.id==='cure' && G.known['herb/cure']);
        if(c){ api.useItem(c,false); api.endTurn(); stats.used++; t++; continue; }
        /* 沒有已知的解毒草就喝一株沒鑑定過的 —— 那正是玩家中毒時會做的事，
           而且是這款遊戲設計的玩法（十四種草每局重洗，喝了才知道是什麼）。
           不模擬這一步的話，量到的是「玩家中毒之後乾等」。 */
        const unk2 = p.inv.find(i=>i.cat==='herb' && !G.known['herb/'+i.id]);
        if(unk2 && p.hp*2 < p.mhp){ api.useItem(unk2,false); api.endTurn(); stats.used++; t++; continue; }
      }
      // 低血喝已知回復草。中毒時門檻拉高 —— 毒還在扣，等到三分之一就來不及了
      if(p.hp * (p.st['毒'] ? 2 : 3) < p.mhp){
        const h = p.inv.find(i=>i.cat==='herb' && i.id==='heal' && G.known['herb/heal']);
        if(h){ api.useItem(h,false); api.endTurn(); stats.used++; t++; continue; }
      }
      // 安全時盲喝未鑑定草藥（這正是 GDD 設計的正確玩法）
      if(p.hp===p.mhp){
        const unk = p.inv.find(i=>i.cat==='herb' && !G.known['herb/'+i.id]);
        if(unk){ api.useItem(unk,false); api.endTurn(); stats.used++; t++; continue; }
      }
      // 裝上目前最好的武器與盾牌。
      // 開場已經不再預先裝備，機器人不會自己穿的話，量到的是赤手空拳的數據。
      const best = (cat, cur) => p.inv
        .filter(i => i.cat === cat && !i.cursed)
        .reduce((a2, b2) => {
          const v = x => (cat === 'weap' ? x.d.atk : x.d.def) + x.up * 2;
          return !a2 || v(b2) > v(a2) ? b2 : a2;
        }, cur);
      const bw = best('weap', p.weap), bs = best('shld', p.shld);
      if(bw && bw !== p.weap){ p.weap = bw; bw.known = 1; api.endTurn(); t++; continue; }
      if(bs && bs !== p.shld){ p.shld = bs; bs.known = 1; api.endTurn(); t++; continue; }

      // 相鄰有怪就打
      /* 解謎型頭目：刀砍不動，正解是房間裡的砲座。
       機器人必須會用 —— 不會用的話那一章直接變成走不完，
       而走通測試回報的會是「死亡 40」，看不出真正的原因。 */
    const tboss = G.f.bossLock && G.mons.find(m => m.d.boss && m.d.turret);
    if(tboss && G.f.turrets){
      const here = G.f.turrets.find(t => t.x === p.x && t.y === p.y);
      if(here && here.cd <= 0){ api.fireTurret(); api.endTurn(); t++; continue; }
      const hot = G.f.turrets.filter(t2 => t2.cd <= 0);
      const aim = (hot.length ? hot : G.f.turrets)
        .reduce((a, b) => !a || (Math.abs(b.x-p.x)+Math.abs(b.y-p.y)) < (Math.abs(a.x-p.x)+Math.abs(a.y-p.y)) ? b : a, null);
      if(aim){
        const st2 = api.nextStep(G, {x:p.x, y:p.y}, aim);
        if(st2){ api.tryMove(st2[0], st2[1]); t++; continue; }
      }
      api.endTurn(); t++; continue;          // 全部冷卻中：原地等，不要去撞它
    }

    let hit = false;
      for(const d of api.DIRS){
        const m = api.monAt(p.x+d[0], p.y+d[1]);
        if(m && api.cornerOK(p.x,p.y,p.x+d[0],p.y+d[1])){ api.tryMove(d[0],d[1]); hit=true; break; }
      }
      if(hit){ t++; continue; }
      // 腳下有東西就撿
      const k = api.key(p.x,p.y);
      const here = G.items[k];
      if(here && !here.shop && p.inv.length < 20){
        p.inv.push(here); delete G.items[k];
        // 空手時自動裝備，跟遊戲內的規則一致
        if(here.cat==='weap' && !p.weap){ p.weap=here; here.known=1; }
        if(here.cat==='shld' && !p.shld){ p.shld=here; here.known=1; }
        api.endTurn(); stats.items++; t++; continue;
      }
      // 樓梯就下樓（頭目還活著的話樓梯是鎖的，這時候要去打頭目）
      if(api.tileAt(p.x,p.y)===api.DOWN && !G.f.bossLock){ api.descend(); t++; continue; }
      let goal = G.f.stairs;
      if(G.f.bossLock){
        let best=null, bd=1e9;
        for(const m of G.mons){
          const dd = Math.max(Math.abs(m.x-p.x), Math.abs(m.y-p.y));
          if(dd < bd){ bd=dd; best={x:m.x, y:m.y}; }
        }
        if(best) goal = best;
      }
      // 否則走向最近的道具或樓梯
      else if(p.inv.length < 20){
        let best=null, bd=1e9;
        for(const ik in G.items){
          if(G.items[ik].shop) continue;          // 不去撿店裡的商品
          const ix = ik%api.MW, iy = (ik/api.MW)|0;
          const dd = Math.max(Math.abs(ix-p.x), Math.abs(iy-p.y));
          if(dd < bd){ bd=dd; best={x:ix,y:iy}; }
        }
        if(best) goal = best;
      }
      const step = nextStep(G, {x:p.x,y:p.y}, goal);
      if(!step){ api.endTurn(); t++; continue; }
      api.tryMove(step[0], step[1]);
      t++;
    }
    stats.turns += t;
    stats.floors += G.depth;
    stats.maxFloor = Math.max(stats.maxFloor, G.depth);
    stats.lv += G.p.lv;
    stats.ident += Object.keys(G.known).length;
    // 通關一章也會把 over 設成 true —— 那不是死亡，要分開算
    if(G.over && G.p.hp > 0) stats.cleared++;
    else if(G.over){ stats.deaths++; if(G.p.sat<=0) stats.starve++;
      deathAt[G.depth] = (deathAt[G.depth]||0)+1; }
  }catch(e){
    stats.errs++;
    console.log('  ✗ 第 %d 場拋出例外：%s', r, e.message);
    console.log(e.stack.split('\n').slice(1,4).join('\n'));
  }
}

const n = RUNS;
console.log('=== 瀏覽器版模擬（%d 場）===\n', n);
console.log('執行期錯誤    : %d', stats.errs);
console.log('通關一章      : %d（%s%%）', stats.cleared, (100*stats.cleared/n).toFixed(1));
console.log('死亡          : %d（%s%%）', stats.deaths, (100*stats.deaths/n).toFixed(1));
console.log('  └ 餓死      : %d（%s%%）', stats.starve, (100*stats.starve/n).toFixed(1));
console.log('平均存活回合  : %s', (stats.turns/n).toFixed(0));
console.log('平均到達樓層  : %s（最深 %d）', (stats.floors/n).toFixed(1), stats.maxFloor);
console.log('平均結束等級  : %s', (stats.lv/n).toFixed(1));
console.log('平均鑑定種類  : %s', (stats.ident/n).toFixed(1));
console.log('撿取 %d 件　使用 %d 件', stats.items, stats.used);
console.log('\n死亡樓層分佈：');
const keys2 = Object.keys(deathAt).map(Number).sort((a,b)=>a-b);
for(const d of keys2){
  const c = deathAt[d];
  console.log('  B%sF %s %d 場（%s%%）',
    String(d).padStart(2), '#'.repeat(c), c, (100*c/n).toFixed(1));
}
const early = (deathAt[1]||0) + (deathAt[2]||0);
console.log('  → 前兩層陣亡：%d 場（%s%%）', early, (100*early/n).toFixed(1));
process.exit(stats.errs > 0 ? 1 : 0);
