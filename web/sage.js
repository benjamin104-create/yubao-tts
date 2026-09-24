const assert=require('node:assert/strict'),{api:a}=require('./simcore');
let checks=0;
function test(name,fn){fn();checks++;console.log('PASS '+name);}
function fresh(){a.VILLAGE().jobs={};a.VILLAGE().act=0;a.VILLAGE().condition=null;a.newGame(8172);a.G().mons=[];return a.G();}
test('all hats have a trainable job and unlock their own two skills',()=>{
  for(const hat of a.HAT){const g=fresh();a.wearHat(a.mk('hat',hat.id));assert.notEqual(g.p.job,'none');
    for(let i=0;i<6;i++)a.jobLevelUp();assert.equal(a.jobLv(hat.job),3);
    const skills=a.ABIL.filter(x=>x.job===hat.job);assert.equal(skills.length,2);assert(skills.every(x=>g.p.learned[x.id]));
  }
});
test('circlet levels require progress, persist, and retain the original spell discount',()=>{
  const g=fresh(),p=g.p;a.wearHat(a.mk('hat','circlet'));a.jobLevelUp();assert.equal(a.jobLv('sage'),0);assert(!p.learned.meditate);
  a.jobLevelUp();assert.equal(a.jobLv('sage'),1);assert(p.learned.meditate);assert(!p.learned.sageward);
  a.saveVillage();a.loadVillage();assert.equal(a.jobLv('sage'),1);
  const spell={sc:'fire',mp:10};p.sch.fire=3;const cost=a.spellCost(p,spell);p.hat=null;assert.equal(a.spellCost(p,spell)-cost,3);
});
test('old equipped circlet save resumes as Sage without losing other progress or items',()=>{
  const g=fresh();g.p.inv=[a.mk('hat','circlet'),a.mk('food','bread')];g.p.hat='circlet';g.p.job='none';g.p.lv=24;
  a.VILLAGE().jobs.war={lv:2,prog:1};a.saveRun();a.resumeRun(a.loadedRun());
  assert.equal(a.G().p.job,'sage');assert.equal(a.G().p.lv,24);assert.equal(a.jobLv('war'),2);assert.equal(a.G().p.inv.length,2);
  a.jobLevelUp();a.jobLevelUp();assert(a.G().p.learned.meditate);
});
test('Meditation spends food, MP and exactly one turn; invalid uses spend nothing',()=>{
  const g=fresh(),p=g.p,skill=a.ABIL.find(x=>x.id==='meditate');p.lv=24;p.mmp=a.maxMp(p);p.mp=10;
  const sat=p.sat,turn=g.turn;assert(a.useAbil(skill));assert.equal(g.turn,turn+1);assert(p.sat<=sat-Math.ceil(p.msat*.1));assert(p.mp>10&&p.mp<=27);
  p.mp=p.mmp;const snapshot=[g.turn,p.mp,p.sat];assert.equal(a.useAbil(skill),false);assert.deepEqual([g.turn,p.mp,p.sat],snapshot);
  p.mp=10;p.sat=1;const hungry=[g.turn,p.mp,p.sat];assert.equal(a.useAbil(skill),false);assert.deepEqual([g.turn,p.mp,p.sat],hungry);
});
test('Sage ward applies both protections and mastery survives removing the circlet',()=>{
  const g=fresh(),p=g.p;p.lv=24;p.mmp=a.maxMp(p);p.mp=p.mmp;const before=p.mp;
  assert(a.useAbil(a.ABIL.find(x=>x.id==='sageward')));assert.equal(before-p.mp,10);assert(p.st['守']>0&&p.st['界']>0);
  const base=a.maxMp(p);a.VILLAGE().jobs.sage={lv:3,prog:0};p.hat=null;assert.equal(a.maxMp(p),Math.round(base*1.1));
});
console.log('Sage: '+checks+' checks passed.');
