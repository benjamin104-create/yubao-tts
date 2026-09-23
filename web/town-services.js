// Gameplay regressions: lodging, persistent curses, and turn-based pressure.
const assert=require('node:assert/strict'),{api:a}=require('./simcore');
let passed=0;const v=()=>a.VILLAGE();
function test(name,fn){fn();passed++;console.log('PASS '+name);}
function start(act=1){v().act=act;v().condition=null;v().stock=[];v().pots=[];v().pocket.item=null;a.newGame(81291);const g=a.G();g.mons=[];g.f.arena=null;g.f.heianGate=null;g.f.heianSamurai=null;return g;}
test('return fatigue and permanent equipment curses survive reload and a new journey',()=>{
 const g=start();v().stock=[{cat:'weap',id:'brnz',up:2}];g.p.inv.push(a.mk('weap','brnz',{up:2,cursed:true}));g.p.hp=7;g.p.mp=2;g.p.sat=18000;
 a.rememberTownCondition();const c={...v().condition};a.saveVillage();a.loadVillage();assert.deepEqual(v().condition,c);a.newGame(1982);const p=a.G().p;
 assert.equal(p.hp,Math.max(1,Math.floor(p.mhp*c.hp)));assert.equal(p.mp,Math.floor(p.mmp*c.mp));assert.equal(p.sat,18000);assert(p.inv.find(i=>i.id==='brnz').cursed);
});
test('lodging charges once, restores next departure, and does not remove curses',()=>{
 start();v().stock=[{cat:'weap',id:'brnz',up:2,cursed:true}];v().condition={hp:.2,mp:0,sat:.1};v().gold=1000;const cost=a.innCost();assert(a.restAtInn());assert.equal(v().gold,1000-cost);assert(!a.restAtInn());assert(v().stock[0].cursed);a.newGame(44);assert.equal(a.G().p.hp,a.G().p.mhp);assert.equal(a.G().p.mp,a.G().p.mmp);
});
test('basic rescue cannot consume money or reduce better health',()=>{
 start();v().gold=0;v().condition={hp:.8,mp:0,sat:0};assert(a.restAtInn(true));assert.deepEqual(v().condition,{hp:.8,mp:.25,sat:.4});assert.equal(v().gold,0);assert(!a.restAtInn(true));assert(!a.restAtInn());
});
test('exorcism is rare, atomic, handles stored contents and retains upgrades',()=>{
 start();v().gold=1000;v().stock=[{cat:'weap',id:'brnz',up:5,cursed:true}];v().pots=[{cat:'pot',id:'store',cursed:false,contents:[{cat:'shld',id:'wood',up:3,cursed:true}]}];
 assert(!a.exorcismAvailable());assert(!a.purifyAtShrine());v().act=14;assert(a.exorcismAvailable());v().gold=100;assert(!a.purifyAtShrine());assert.equal(a.townCursedItems().length,2);v().gold=1000;assert(a.purifyAtShrine());assert.equal(v().gold,720);assert.equal(a.townCursedItems().length,0);assert.equal(v().stock[0].up,5);assert(!a.purifyAtShrine());
});
test('clock time and status rendering do not consume pressure; warnings and wave fire once',()=>{
 const g=start();g.f.enterAt=Date.now()-3600000;for(let i=0;i<100;i++)a.pressureInfo();assert.equal(a.pressureInfo().turns,0);
 g.f.elapsedTurns=419;a.dwellCheck();assert.equal(a.pressureInfo().stage,1);assert.equal(a.pressureInfo().left,120);
 g.f.elapsedTurns=539;a.dwellCheck();const n=g.mons.length;assert(n>=6);for(const m of g.mons){assert.notEqual(g.seen[a.key(m.x,m.y)],2);assert(Math.max(Math.abs(m.x-g.p.x),Math.abs(m.y-g.p.y))>=7);}
 a.dwellCheck();assert.equal(g.mons.length,n);assert.equal(a.pressureInfo().left,179);
});
test('collapse advances only one floor with no chapter reward, preserves escort/inventory/health',()=>{
 const g=start();g.floor=1;a.buildFloor();g.f.elapsedTurns=719;g.npc={x:g.p.x+1,y:g.p.y,hp:20,mhp:20,follow:1};const inv=g.p.inv,hp=g.p.hp,chapter=v().act,gold=v().gold;
 a.dwellCheck();assert.equal(g.floor,2);assert.equal(v().act,chapter);assert.equal(v().gold,gold);assert.equal(g.p.hp,hp);assert.strictEqual(g.p.inv,inv);assert(g.npc?.follow);assert.equal(a.pressureInfo().turns,0);
});
test('tutorial/boss/arena/story floors are exempt; tower gets a wave instead of falling',()=>{
 let g=start(0);g.f.elapsedTurns=719;a.dwellCheck();assert.equal(g.floor,1);assert.equal(a.pressureInfo(),null);
 g=start();g.floor=a.actAt(g.act).floors;a.buildFloor();g.f.elapsedTurns=719;a.dwellCheck();assert.equal(g.floor,a.actAt(g.act).floors);
 g=start();g.f.arena={};assert(!a.pressureEnabled());g.f.arena=null;g.f.heianGate={};assert(!a.pressureEnabled());
 g=start(a.ACTS.findIndex(x=>x.id==='tower'));g.f.elapsedTurns=719;a.dwellCheck();assert.equal(g.floor,1);assert(g.mons.length>0);
});
test('saved floor pressure resumes without resetting the action count',()=>{
 const g=start();g.f.elapsedTurns=603;a.saveRun();const q=a.loadedRun();assert.equal(q.pressure,603);a.resumeRun(q);assert.equal(a.G().f.elapsedTurns,603);
});
console.log('Town services: '+passed+' checks passed.');
