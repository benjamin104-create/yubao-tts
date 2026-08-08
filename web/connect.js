// 連通性測試：每一章、每一層、多顆種子，檢查地圖是不是還走得通。
//
// 為什麼需要這一支：房間開始「雕形狀」之後（森林是圓的、山道是階梯狀、
// 通天塔是同心圓），矩形房間那個「每一格都是地板」的前提就沒了。
// 只要雕出一塊孤島，玩家就會對著一個到不了的樓梯或道具發呆 ——
// 而這種失敗在走通測試裡只會顯示成「回合上限」，看不出真正的原因。
//
// 檢查兩件事：
//   1. 樓梯從出生點走得到
//   2. 地圖上沒有走不到的地板（孤島）
const { api } = require('./simcore.js');

const V = api.VILLAGE();
const MW = api.MW, MH = api.MH;
const SEEDS = 12;

function reach(G){
  const t = G.f.t;
  const seen = new Uint8Array(MW * MH);
  const st = [[G.p.x, G.p.y]];
  seen[api.key(G.p.x, G.p.y)] = 1;
  while(st.length){
    const [x, y] = st.pop();
    for(const [ox, oy] of [[1,0],[-1,0],[0,1],[0,-1]]){
      const nx = x + ox, ny = y + oy;
      if(nx < 0 || ny < 0 || nx >= MW || ny >= MH) continue;
      const k = api.key(nx, ny);
      if(seen[k] || t[k] === api.WALL) continue;
      seen[k] = 1; st.push([nx, ny]);
    }
  }
  let floors = 0, orphan = 0;
  for(let i = 0; i < MW * MH; i++){
    if(t[i] === api.WALL) continue;
    floors++;
    if(!seen[i]) orphan++;
  }
  return { stairs: !!seen[api.key(G.f.stairs.x, G.f.stairs.y)], floors, orphan };
}

let bad = 0, checked = 0, orphanTot = 0, floorTot = 0;
const rows = [];
for(let a = 0; a < api.ACTS.length; a++){
  const act = api.ACTS[a];
  let noStairs = 0, orph = 0, fl = 0, cells = 0;
  for(let s = 0; s < SEEDS; s++){
    V.act = a;
    api.newGame(9001 + s * 977);
    const G = api.G();
    for(let f = 1; f <= act.floors; f++){
      G.floor = f;
      buildFloorSafe(G);
      const r = reach(G);
      checked++; fl++;
      if(!r.stairs) noStairs++;
      orph += r.orphan; cells += r.floors;
    }
  }
  orphanTot += orph; floorTot += cells;
  rows.push({ nm: act.nm, fl, noStairs, orph, cells });
  if(noStairs || orph) bad++;
}

function buildFloorSafe(G){
  // buildFloor 沒被 simcore 匯出，但 newGame 之後改 floor 再呼叫是遊戲自己的做法
  api.buildFloor();
}

console.log('=== 連通性測試（每章 %d 顆種子）===\n', SEEDS);
for(const r of rows){
  console.log('%s 　%s　%s 層　樓梯不可達 %s　孤島格 %s / %s',
    (r.noStairs || r.orph) ? '✗' : '✓',
    (r.nm + '　　　　　　').slice(0, 6),
    String(r.fl).padStart(3), String(r.noStairs).padStart(3),
    String(r.orph).padStart(4), r.cells);
}
console.log('\n檢查 %d 層，孤島格 %d / %d（%s%%）',
  checked, orphanTot, floorTot, (orphanTot / floorTot * 100).toFixed(3));
process.exit(bad ? 1 : 0);
