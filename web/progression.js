// Regression checks for scarcity, fair telegraphs, and persistent crafting.
const assert=require('node:assert/strict'),{api:a}=require('./simcore');
const V=()=>a.VILLAGE();let passed=0;
function test(name,fn){fn();passed++;console.log('PASS '+name);}
function start(act=0){V().act=act;a.newGame(7781);const g=a.G();g.mons=[];g.p.inv=[];return g;}
test('each level/chapter milestone grants once, including after save/reload',()=>{
 const g=start();V().magicMilestones={};V().sp=7;g.p.sp=7;
 assert(a.grantMagicPoint('level:4'));assert.equal(V().sp,8);assert(!a.grantMagicPoint('level:4'));
 a.saveVillage();a.loadVillage();assert.equal(V().sp,8);assert(!a.grantMagicPoint('level:4'));assert(a.grantMagicPoint('chapter:temple'));
 assert.equal(V().sp,9);assert.deepEqual([0,1,2,3,4].map(a.schoolUpgradeCost),[1,1,2,3,4]);
});
test('new chapter ore does not repeat and existing upgraded equipment survives',()=>{
 start();V().stock=[{cat:'weap',id:'mith',up:8}];V().forgeOre=0;V().magicMilestones={};
 a.grantReward(a.ACTS[0]);assert.equal(V().forgeOre,3);a.grantReward(a.ACTS[0]);assert.equal(V().forgeOre,3);
 a.saveVillage();a.loadVillage();assert.equal(V().stock[0].up,8);assert.equal(a.forgeCap(a.WEAP.find(d=>d.id==='mith'),0),2);
});
test('loot and shops respect chapter gates and ultimate exclusivity (18000 rolls)',()=>{
 for(let act=0;act<a.ACTS.length;act++){
  const g=start(act);V().stock=[];
  for(let i=0;i<1000;i++){const it=a.rollItem(g.rng,99);assert(!it.d.ult&&!it.d.craftOnly);if(['weap','shld'].includes(it.cat)){assert(a.gearAvailable(it.d,act));assert(it.up<=a.scrollForgeCap(it.d,act));}}
  for(const item of a.stockNow())assert((item.from||0)<=act);
 }
});
test('capped enhancement scroll stays in inventory',()=>{
 const g=start();const w=a.mk('weap','brnz',{up:1}),s=a.mk('scroll','ench',{known:1});g.p.weap=w;g.p.inv=[w,s];assert.equal(a.useItem(s,false),false);assert(g.p.inv.includes(s));assert.equal(w.up,1);
});
test('return collects eligible identified items once, protecting full wands/rare herbs/pots',()=>{
 const g=start();V().alchemyStock=[];
 const heal=a.mk('herb','heal',{known:1}),bad=a.mk('herb','psn',{known:1}),rare=a.mk('herb','life',{known:1}),unknown=a.mk('scroll','map'),empty=a.mk('wand','bolt',{uses:0,known:1}),full=a.mk('wand','weak',{uses:2,known:1}),pot=a.mk('pot','store',{known:1});
 pot.contents=[a.mk('herb','cure',{known:1})];g.p.inv=[heal,bad,rare,unknown,empty,full,pot];g.known={};
 assert.equal(a.stashAlchemy(),3);assert.equal(a.stashAlchemy(),0);assert.deepEqual(g.p.inv,[rare,unknown,full,pot]);assert.equal(pot.contents.length,1);
 assert.deepEqual(V().alchemyStock.map(x=>x.id),['heal','psn','bolt']);
});
test('crafting charges exact materials, preserves points, rejects missing/unlearned/full',()=>{
 start();V().reagents={leaf:4,spore:2,ink:4,spark:4};V().gold=1000;V().townStory={};V().travelSupplies=[];const sp=V().sp;
 assert.equal(a.craftAlchemy('mana'),false);V().townStory['euro:well']=3;
 assert(a.craftAlchemy('mana'));assert.equal(V().gold,880);assert.deepEqual(V().reagents,{leaf:3,spore:2,ink:4,spark:2});assert.equal(V().sp,sp);
 assert(a.craftAlchemy('cure'));assert(a.craftAlchemy('heal'));const snapshot=JSON.stringify([V().reagents,V().gold]);assert(!a.craftAlchemy('heal'));assert.equal(JSON.stringify([V().reagents,V().gold]),snapshot);
 V().travelSupplies.push({cat:'food',id:'fruit'});V().reagents.leaf=9;assert(!a.craftAlchemy('cure'));
 a.saveVillage();a.loadVillage();assert.equal(V().travelSupplies.length,4);assert(V().travelSupplies.some(x=>x.id==='mana'));assert.equal(V().reagents.leaf,9);
});
test('distillation consumes one item, cannot overfill, persists original choices',()=>{
 V().alchemyStock=[{cat:'herb',id:'psn'},{cat:'scroll',id:'map'}];V().reagents={spore:98,ink:99};
 assert(a.distillAlchemy(0));assert.equal(V().reagents.spore,99);assert(!a.distillAlchemy(0));assert.equal(V().alchemyStock.length,1);
 a.saveVillage();a.loadVillage();assert.deepEqual(V().alchemyStock,[{cat:'scroll',id:'map'}]);
});
test('mana potion restores at most 12 MP, preserves at full, never increases growth',()=>{
 const g=start(),it=a.mk('herb','mana',{known:1});g.p.inv=[it];g.p.mmp=40;g.p.mp=10;const sp=g.p.sp;
 assert(a.useItem(it,false));assert.equal(g.p.mp,22);assert.equal(g.p.mmp,40);assert.equal(g.p.sp,sp);assert(!g.p.inv.includes(it));
 const more=a.mk('herb','mana',{known:1});g.p.inv=[more];g.p.mp=40;assert.equal(a.useItem(more,false),false);assert(g.p.inv.includes(more));
});
test('boss slam uses warned area, dodging avoids damage and opens finite recovery',()=>{
 const g=start();g.turn=10;g.p.x=10;g.p.y=11;for(let y=7;y<15;y++)for(let x=7;x<15;x++)g.f.t[a.key(x,y)]=1;
 const m=a.spawnMon(a.bossById('b_keeper'),10,10);m.skillUsed={};m.d={...m.d,sig:null,ward:null};m.tick=3;
 const intent=a.decide(m);assert.equal(intent.k,'wait');assert.equal(m.warn.kind,'slam');
 g.turn++;g.p.y=12;const hp=g.p.hp,resolved=a.decide(m);assert.equal(resolved.k,'bossSlam');a.act(m,resolved);assert.equal(g.p.hp,hp);assert.equal(m.openUntil,13);
 assert.equal(a.bossDamage(m,20),27);g.turn=12;assert.equal(a.decide(m).k,'wait');g.turn=14;assert.equal(a.bossDamage(m,20),17);
 m.warn={kind:'slam',cx:10,cy:10,x:10,y:11};g.p.y=11;const hit=a.decide(m);a.act(m,hit);assert(g.p.hp<hp,'standing in warning must hurt');
});
console.log('Progression and crafting: '+passed+' checks passed.');
