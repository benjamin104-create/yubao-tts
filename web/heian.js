// End-to-end quest state regression; combat powers get separate executable checks.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {api:a}=require('./simcore');
let checks=0;
function test(name,fn){fn();checks++;console.log('PASS '+name);}
function fresh(seed=260829){
  Object.assign(a.VILLAGE(),{act:a.HEIAN_ACT,muramasa:0,heianHunt:0});
  a.newGame(seed);const g=a.G();g.floor=2;a.buildFloor();return g;
}
function answer(yes){for(let i=0;i<12&&a.talkOpen();i++)a.answerTalk(yes);assert(!a.talkOpen());}
function enter(g){a.askHeianSamurai(g.f.heianSamurai);answer(true);
  Object.assign(g.p,g.f.heianGate);a.stepOn();assert(g.heian.active);}
function down(id){const m=a.G().mons.find(m=>m.d.id===id);assert(m,id);m.hp=0;a.kill(m);}
function at(x,y){const g=a.G();g.p.x=x;g.p.y=y;a.stepOn();}
function roundtrip(){a.saveRun();const q=a.loadedRun();assert(q);a.resumeRun(q);return a.G();}

test('武士可達、拒絕不開門，答應只生成一個入口（四種種子）',()=>{
  for(const seed of [1,42,260829,987654]){
    const g=fresh(seed),n=g.f.heianSamurai;assert(n);
    assert(a.nextStep(g,g.p,n));a.askHeianSamurai(n);answer(false);
    assert(!g.heian.accepted&&!g.f.heianGate);
    enter(g);assert.equal(g.heian.stage,1);assert.equal(g.mons.length,1);
    assert(!a.walkable(9,14)&&!a.walkable(17,14)&&!a.walkable(25,14));
  }
});
test('三連房逐門解鎖、不瞬移；紀錄點只補滿一次，讀檔不重生',()=>{
  let g=fresh();enter(g);const pos=[g.p.x,g.p.y];
  down('b_genmaan');assert.equal(g.heian.stage,2);assert.deepEqual([g.p.x,g.p.y],pos);
  assert(a.walkable(9,14));assert(!a.walkable(19,14));assert.equal(g.mons.length,0);
  g.p.hp=5;g.p.mp=1;at(5,14);assert.equal(g.p.hp,g.p.mhp);assert.equal(g.p.mp,g.p.mmp);
  g=roundtrip();assert(g.f.shrine.used);assert.equal(g.mons.length,0);
  g.p.hp=5;at(5,14);assert.equal(g.p.hp,5);
  // Actual path through the open doorway, not a stage teleport.
  while(g.p.x<10){g.p.x++;a.stepOn();}
  assert.equal(g.mons[0].d.id,'b_musashimaru');assert.equal(g.f.riftWave,2);
  const p2=[g.p.x,g.p.y];down('b_musashimaru');assert.deepEqual([g.p.x,g.p.y],p2);
  assert.equal(g.heian.stage,3);assert(a.walkable(19,14));assert.equal(g.mons.length,0);
  at(14,14);g=roundtrip();assert(g.f.shrine.used);at(20,14);
  assert.deepEqual(g.mons.map(m=>m.d.sideRole).sort(),['doll_heal','doll_mage','doll_tank']);
  down('b_doll_heal');down('b_doll_mage');assert.equal(g.heian.stage,3);assert(!g.f.riftExit);
  down('b_doll_tank');assert.equal(g.heian.stage,4);assert(g.f.muramasaDrop);assert(!g.f.riftExit);
});
test('满背包不吞村正；領取解鎖遠斬；回到未重生成的原樓層',()=>{
  let g=fresh();const first=Object.keys(g.gold)[0];if(first)delete g.gold[first];
  g.gold[a.key(2,2)]=617;g.mons=g.mons.slice(0,2);g.mons[0].hp=7;
  const mons=g.mons.map(m=>[m.id,m.d.id,m.hp]);const terrain=Array.from(g.f.t);
  enter(g);down('b_genmaan');at(10,14);down('b_musashimaru');at(20,14);
  for(const id of ['b_doll_heal','b_doll_mage','b_doll_tank'])down(id);
  while(g.p.inv.length<20)g.p.inv.push(a.mk('food','bread'));
  at(25,14);assert(!a.VILLAGE().muramasa);assert(g.f.muramasaDrop);assert.equal(g.p.inv.length,20);
  g=roundtrip();assert(g.f.muramasaDrop);assert.equal(g.heian.stage,4);
  g.p.inv.pop();at(25,14);assert(a.VILLAGE().muramasa);assert.equal(g.p.weap.d.id,'muramasa');
  assert(!g.f.muramasaDrop);assert(g.f.riftExit);assert.equal(g.p.inv.length,20);
  g=roundtrip();assert.equal(g.p.weap.d.id,'muramasa');assert(g.f.riftExit);
  at(27,14);assert(!g.heian.active&&g.heian.completed);assert.equal(g.floor,2);
  assert.deepEqual(Array.from(g.f.t),terrain);assert.equal(g.gold[a.key(2,2)],617);
  assert.deepEqual(g.mons.map(m=>[m.id,m.d.id,m.hp]),mons);assert(!g.f.heianGate);
  g=roundtrip();assert.deepEqual(g.mons.map(m=>[m.id,m.d.id,m.hp]),mons);
  assert.equal(g.gold[a.key(2,2)],617);assert(!g.f.heianGate);
  const count=g.p.inv.filter(i=>i.id==='muramasa').length;a.giveMuramasa();
  assert.equal(g.p.inv.filter(i=>i.id==='muramasa').length,count);
});
test('爽約後每層、跨章及存檔仍有武士靈，未答應則沒有',()=>{
  let g=fresh();assert(!g.mons.some(m=>m.d.id==='samurai_spirit'));
  a.askHeianSamurai(g.f.heianSamurai);answer(true);
  Object.assign(g.p,g.f.stairs);g.f.bossLock=0;a.descend();
  assert(g.heian.hunt&&a.VILLAGE().heianHunt);
  assert.equal(g.mons.filter(m=>m.d.id==='samurai_spirit').length,1);
  a.VILLAGE().act=a.HEIAN_ACT+1;a.newGame(882);g=a.G();
  assert.equal(g.mons.filter(m=>m.d.id==='samurai_spirit').length,1);
  g=roundtrip();assert(g.heian.hunt);assert.equal(g.mons.filter(m=>m.d.id==='samurai_spirit').length,1);
  g.floor=2;a.buildFloor();assert.equal(g.mons.filter(m=>m.d.id==='samurai_spirit').length,1);
});
test('幻魔庵有同尺寸兩分身、定身飛鏢；武藏丸震喝兩回合',()=>{
  let g=fresh();enter(g);g.p.hp=g.p.mhp=3000;
  let m=g.mons[0];a.useSideBossSkill(m,{kind:'illusion'});
  assert.equal(g.mons.filter(q=>q.isClone).length,2);
  assert(g.mons.filter(q=>q.isClone).every(q=>q.hp===1&&q.d.visualBoss));
  assert.notEqual((a.sideBossIntent(m)||{}).kind,'illusion');
  m.x=7;m.y=14;g.p.x=3;g.p.y=14;const hp=g.p.hp;
  a.useSideBossSkill(m,{kind:'rootShuriken'});assert(g.p.hp<hp);assert.equal(g.p.st['纏'],2);
  down('b_genmaan');at(10,14);m=g.mons[0];a.useSideBossSkill(m,{kind:'samuraiRoar'});
  assert.equal(g.p.st['麻'],2);assert(m.skillUsed.roar);
});
test('三人偶分工有實際回血、術式傷害和衝撞，動畫事件存在',()=>{
  const g=fresh();enter(g);down('b_genmaan');at(10,14);down('b_musashimaru');at(20,14);
  g.p.hp=g.p.mhp=5000;const [h,m,t]=g.mons;h.hp-=40;t.hp-=100;
  const old=t.hp;a.useSideBossSkill(h,{kind:'dollHeal'});assert(t.hp>old);
  const hp=g.p.hp;a.useSideBossSkill(m,{kind:'dollBurst'});assert(g.p.hp<hp);
  t.x=24;t.y=14;g.p.x=21;g.p.y=14;const hp2=g.p.hp;
  a.useSideBossSkill(t,{kind:'dollCharge'});assert(g.p.hp<hp2);
  assert(g.parts.length&&g.rings.length&&g.anim.some(x=>x.kind==='charge'));
});
test('武藏丸刀傷至少四分之一、武士靈至少三分之一；村正每刀支付5%最大HP',()=>{
  const g=fresh();enter(g);g.mons=[];g.p.hp=g.p.mhp=1200;g.p.inv=[];
  for(const [id,part] of [['b_musashimaru',4],['samurai_spirit',3]]){
    const m=a.spawnMon(id==='samurai_spirit'?a.HEIAN_SPIRIT:a.bossById(id),4,14,{noElite:true});
    m.sureHit=1;g.p.x=3;g.p.y=14;g.p.hp=1200;
    a.act(m,{k:'melee'});assert(1200-g.p.hp>=1200/part);g.mons=[];
  }
  const blade=a.mk('weap','muramasa',{known:1});g.p.inv.push(blade);g.p.weap=blade;
  g.p.hp=1200;const target=a.spawnMon(a.bossById('b_genmaan'),7,14,{noElite:true});
  target.hp=target.mhp=10000;target.st['睡']=10;g.p.st={};
  a.fireMuramasa(1,0);assert(target.hp<10000);assert.equal(g.p.hp,1140);
  g.p.weap=null;const hp=g.p.hp;a.fireMuramasa(1,0);assert.equal(g.p.hp,hp);
});
test('五頭目、武士靈及村正都有專屬實體PNG；不再依賴普通怪貼圖',()=>{
  for(const id of ['b_genmaan','b_musashimaru','b_doll_heal','b_doll_mage','b_doll_tank','samurai_spirit'])
    assert(fs.existsSync(__dirname+'/art/boss/'+id+'.png'));
  assert(fs.existsSync(__dirname+'/art/item/weap09.png'));
});
console.log(`Heian side quest: ${checks} checks passed.`);
