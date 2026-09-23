const assert=require('node:assert/strict'),{api:a}=require('./simcore');let count=0;
const v=()=>a.VILLAGE();function test(n,f){f();console.log('PASS '+n);count++;}
function setup(act=1){v().act=act;v().condition=null;v().stock=[];v().relicSeals={};v().relicForged=false;v().hunterClaims=[];a.newGame(135);const g=a.G();g.mons=[];g.f.arena=null;g.f.heianGate=null;g.f.heianSamurai=null;g.f.rest=false;g.f.bossLock=false;g.p.hp=g.p.mhp=200;g.p.x=10;g.p.y=10;for(let y=5;y<20;y++)for(let x=5;x<25;x++)g.f.t[a.key(x,y)]=1;g.seen.fill(2);return g;}
test('ordinary weapon/spells/traps cannot bypass lion armour, four named weapons can',()=>{
 const g=setup(),m=a.spawnHunter('lion',11,10);g.p.weap=a.mk('weap','mith');
 for(const source of ['weapon','magic','wand','throw','trap','summon'])assert.equal(a.hunterDamage(m,99999,source),1,source);
 for(const id of ['sky','babel','muramasa','ragnarok']){g.p.weap=a.mk('weap',id);assert.equal(a.lionBreaker(),true);assert(a.hunterDamage(m,99,'weapon')>1);assert(a.hunterDamage(m,99999,'weapon')<=Math.ceil(m.mhp*.07));}
 m.openUntil=g.turn+2;assert.equal(a.hunterDamage(m,99999,'weapon'),Math.ceil(m.mhp*.12));
 const hp=m.hp;a.hurtMon(m,10000,'#fff',null,0,'magic');assert.equal(hp-m.hp,1);
});
test('lion telegraph can be escaped in ONE move, recovery grants two counter actions',()=>{
 const g=setup(),m=a.spawnHunter('lion',11,10);m.rest=0;a.hunterIntent(m);assert(m.warn);assert.equal(m.warn.cx,11);
 assert.equal(a.hunterIntent(m).k,'wait','extra speed cannot consume the warning in the same turn');
 g.p.x=9;g.turn++;const hp=g.p.hp,it=a.hunterIntent(m);assert.equal(it.k,'hunterStrike');a.hunterStrike(m,it);assert.equal(g.p.hp,hp);g.turn++;assert.equal(a.hunterIntent(m).k,'wait');
 m.openUntil=0;g.turn=4;g.p.x=10;a.hunterIntent(m);g.turn++;a.hunterStrike(m,a.hunterIntent(m));assert(g.p.hp<hp);assert(g.p.hp>=hp*.58);
});
test('wall warning is turn based, blockage postpones emergence and pause does nothing',()=>{
 const g=setup();g.f.t[a.key(16,9)]=a.WALL;assert(a.scheduleHunter('wall','test'));const q={...g.f.pursuit.pending};
 for(let i=0;i<20;i++)a.pressureInfo();assert.equal(g.f.pursuit.pending.left,4);
 g.p.x=q.x;g.p.y=q.y;for(let i=0;i<4;i++)a.hunterTick();assert(g.f.pursuit.pending);assert.equal(g.mons.length,0);
 g.p.x=10;g.p.y=10;a.hunterTick();assert.equal(g.mons.length,1);assert.equal(g.mons[0].rest,2);assert.equal(a.scheduleHunter('wall'),false);
});
test('tutorial, boss, rest and scripted arenas never schedule hunters',()=>{
 const g=setup();g.act=0;assert(!a.scheduleHunter('lion'));g.act=1;g.floor=a.ACTS[1].floors;assert(!a.scheduleHunter('lion'));g.floor=1;g.f.rest=true;assert(!a.scheduleHunter('wall'));g.f.rest=false;g.f.arena={};assert(!a.scheduleHunter('wall'));
});
test('a hunter reward is unique across reloads, and never drops a quest-exclusive weapon',()=>{
 const g=setup(14),m=a.spawnHunter('lion',11,10),loot=a.hunterReward(m);assert(loot.length===2);assert(loot.every(i=>!i.d.ult));assert(loot.some(i=>i.id==='ygg'));a.saveVillage();a.loadVillage();g.hunterClaims=[];assert.equal(a.hunterReward(m).length,0);
});
test('pursuit health, warning, countdown and cooldown survive checkpoint restore',()=>{
 const g=setup(),m=a.spawnHunter('lion',11,10);m.hp=93;m.rest=0;m.warn={kind:'slam',cx:11,cy:10};a.hunterState().age=401;
 const q=a.packPursuit();g.mons=[];g.f.pursuit=null;a.restorePursuit(q);const n=g.mons[0];assert.equal(n.hp,93);assert(n.warn);assert.equal(g.f.pursuit.age,401);
});
test('four seals unlock in separate chapters, full bags and reloads retain progress',()=>{
 for(const r of a.RELIC_GUARDS){const g=setup(a.ACTS.findIndex(x=>x.id===r.act));g.floor=2;a.buildFloor();v().relicSeals=Object.fromEntries(a.RELIC_GUARDS.filter(x=>a.ACTS.findIndex(y=>y.id===x.act)<g.act).map(x=>[x.id,1]));g.mons=[];a.placeRelicGuardian();const m=g.mons.find(m=>m.d.relic);assert.equal(m.d.relic,r.id);assert.equal(a.hunterIntent(m).k,'wait');g.p.inv=Array.from({length:20},()=>a.mk('herb','heal'));assert(a.claimRelic(m));assert(!a.claimRelic(m));a.saveVillage();a.loadVillage();assert(v().relicSeals[r.id]);}
});
test('four seals are consumed once; forged weapon persists and stays out of shops/random drops',()=>{
 setup(14);v().relicSeals={ember:1,tide:1,crystal:1};const before=JSON.stringify(v());assert(!a.forgeRagnarok());assert.equal(JSON.stringify(v()),before);
 v().relicSeals.sky=1;assert(a.forgeRagnarok());assert(!a.forgeRagnarok());assert.deepEqual(v().relicSeals,{});assert.equal(v().stock.filter(i=>i.id==='ragnarok').length,1);a.saveVillage();a.loadVillage();a.newGame(19);assert(a.G().p.inv.some(i=>i.id==='ragnarok'));assert(!a.gearAvailable(a.WEAP.find(i=>i.id==='ragnarok'),17));
});
console.log('Hunters and seals: '+count+' checks passed.');
