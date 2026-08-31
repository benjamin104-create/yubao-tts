// The campaign bot must use the same consumables a player can use. No free
// items, stat changes, extra turns, or special boss damage are granted here.
const weakened = new WeakSet();

function combatItem(api, G){
  const p = G.p;
  if(G.over || ['睡','麻','石'].some(k => p.st[k])) return false;
  const known = i => i.known || G.known[i.cat + '/' + i.id];
  const drink = i => { api.useItem(i, false); api.endTurn(); return true; };

  if(['毒','亂','盲','封','緩','痛','燒','纏'].some(k => p.st[k])){
    const cure = p.inv.find(i => i.cat === 'herb' && known(i) && i.d.cure);
    if(cure) return drink(cure);
  }
  if(p.hp < p.mhp * .6){
    const lost = p.mhp - p.hp;
    const heals = p.inv.filter(i => i.cat === 'herb' && known(i) &&
      !i.d.revive && !i.d.bad && (i.d.hp > 0 || i.d.full));
    heals.sort((a,b) => Math.min(lost,b.d.full ? lost : b.d.hp) -
      Math.min(lost,a.d.full ? lost : a.d.hp));
    if(heals.length) return drink(heals[0]);
  }

  // A wand hits the first actor on its ray. Do not shoot through a wall or
  // another monster to reach the boss, and do not act on unseen enemies.
  const targets = [];
  for(const dir of api.DIRS){
    for(let n=1;n<=8;n++){
      const x=p.x+dir[0]*n, y=p.y+dir[1]*n;
      if(!api.walkable(x,y)) break;
      const m=api.monAt(x,y);
      if(!m) continue;
      if(G.seen[api.key(x,y)] === 2) targets.push({m,dir,n});
      break;
    }
  }
  targets.sort((a,b) => Number(!!b.m.d.boss)-Number(!!a.m.d.boss) || a.n-b.n);
  for(const {m,dir,n} of targets){
    if(!m.d.boss && !m.d.elite && p.hp >= p.mhp*.5) continue;
    if(m.d.turret) continue;
    const wand = id => p.inv.find(i => i.cat==='wand' && i.id===id && i.uses>0 && known(i));
    let it=null;
    if(m.d.spd>1) it=wand('slow');
    if(!it && !weakened.has(m)) it=wand('weak');
    if(!it && !(m.d.imm||[]).includes('睡') && !(m.st['睡']>2) && n<=4) it=wand('sleep');
    if(!it) continue;
    if(it.id==='weak') weakened.add(m);
    api.useItem(it,false);
    api.fireWand(dir[0],dir[1]); // This API already spends the turn.
    return true;
  }
  return false;
}

module.exports = { combatItem };

if(require.main === module){
  const assert = require('node:assert/strict');
  const { api } = require('./simcore.js');
  const start = () => {
    api.VILLAGE().act=0; api.newGame(90210);
    const G=api.G(); G.mons=[]; G.p.inv=[]; G.p.mhp=100; G.p.hp=100;
    G.p.weap=null; G.p.shld=null; return G;
  };
  let G=start();
  G.p.hp=20;
  const elix=api.mk('herb','elix',{known:1}); G.p.inv.push(elix);
  let turn=G.turn;
  assert.equal(combatItem(api,G),true);
  assert(G.p.hp>=100 && !G.p.inv.includes(elix));
  assert.equal(G.turn,turn+1);

  G=start(); G.p.st['毒']=5;
  const cure=api.mk('herb','cure',{known:1}); G.p.inv.push(cure);
  assert.equal(combatItem(api,G),true);
  assert(!G.p.st['毒'] && !G.p.inv.includes(cure));

  G=start();
  const dir=api.DIRS.find(d=>api.walkable(G.p.x+d[0],G.p.y+d[1]));
  assert(dir);
  const boss=api.spawnMon(api.bossById('b_hanzo'),G.p.x+dir[0],G.p.y+dir[1]);
  G.seen[api.key(boss.x,boss.y)]=2;
  const slow=api.mk('wand','slow',{known:1,uses:3}); G.p.inv.push(slow);
  const hp=boss.hp, resist=boss.d.magicResist;
  turn=G.turn;
  assert.equal(combatItem(api,G),true);
  assert.equal(slow.uses,2);
  assert.equal(G.turn,turn+1);
  assert.equal(boss.d.spd,.5);
  assert.equal(boss.hp,hp);
  assert.equal(boss.d.magicResist,resist);

  G=start(); G.p.hp=20;
  assert.equal(combatItem(api,G),false);
  assert.equal(G.p.inv.length,0);
  console.log('Campaign consumable strategy: 4 checks passed (real inventory and one turn per action).');
}
