const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const out=path.resolve(__dirname,'../work/rpg-v21');fs.mkdirSync(out,{recursive:true});const report=[];
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{for(const [width,height]of [[390,844],[360,640],[844,390],[1200,900]]){
  const p=await b.newPage({viewport:{width,height},isMobile:width<621,hasTouch:width<621}),errors=[];p.on('pageerror',e=>errors.push(e.message));
  await p.goto('http://127.0.0.1:8876/?qa=floor&act=mine');await p.waitForFunction(()=>globalThis.RPG_ENDING&&HD_LOADED['hd:hunter-wall-idle']&&HD_LOADED['hero#blob']);
  const bounds=async selector=>{const z=await p.locator(selector).boundingBox();assert(z&&z.x>=-1&&z.y>=-1&&z.x+z.width<=width+1&&z.y+z.height<=height+1,JSON.stringify({selector,width,height,z}));};
  await p.evaluate(()=>{document.getElementById('cover').classList.remove('gone');coverUp=true;});await p.waitForTimeout(400);assert(await p.locator('#covertext').isVisible());await bounds('#start');await p.screenshot({path:path.join(out,`cover-${width}.png`)});
  await p.locator('#start').click();await p.locator('#prologue.show').waitFor();await p.locator('#propause').click();await bounds('#prologuebox');await bounds('#pronext');
  await p.locator('#pronext').click();await p.locator('#pronext').click();await p.waitForTimeout(900);await p.screenshot({path:path.join(out,`opening-${width}.png`)});
  await p.locator('#proprev').click();assert((await p.locator('#prologuevisual').getAttribute('class')).includes('scene-1'));await p.locator('#proskip').click();
  await p.evaluate(()=>{document.getElementById('card').classList.remove('show');document.getElementById('hint').classList.remove('show');G.act=1;G.floor=1;buildFloor();G.mons=[];G.p.hp=G.p.mhp=500;G.p.x=15;G.p.y=15;for(let y=9;y<23;y++)for(let x=8;x<26;x++)G.f.t[key(x,y)]=1;G.seen.fill(2);const m=spawnHunter('lion',16,15);m.rest=0;hunterIntent(m);refresh();});
  await p.waitForTimeout(600);await p.screenshot({path:path.join(out,`lion-${width}.png`)});
  await p.evaluate(()=>{G.mons=[];G.f.pursuit={pending:{kind:'wall',x:18,y:14,wx:18,wy:13,left:2}};G.f.t[key(18,13)]=WALL;refresh();});
  await p.waitForTimeout(500);await p.screenshot({path:path.join(out,`wall-emergence-${width}.png`)});
  await p.evaluate(()=>{G.over=true;G.won=true;VILLAGE.relicForged=true;VILLAGE.npcDone=1;ending();});await p.locator('#ending-cinema').waitFor({state:'visible'});await p.locator('#ending-pause').click();
  const cleared=await p.evaluate(()=>VILLAGE.cleared),turn=await p.evaluate(()=>G.turn);
  await bounds('#ending-cinema');await bounds('#ending-controls');await bounds('#ending-caption');await p.waitForTimeout(700);await p.screenshot({path:path.join(out,`ending-0-${width}.png`)});
  for(let i=1;i<9;i++){await p.locator('#ending-next').click();await bounds('#ending-caption');assert(await p.locator('#ending-caption').evaluate(e=>e.scrollHeight<=e.clientHeight+1),'caption fits without scrolling');await p.waitForFunction(()=>[...document.querySelectorAll('#ending-cast img')].every(im=>im.complete&&im.naturalWidth>0));if([2,6,7,8].includes(i)){await p.waitForTimeout(1000);await p.screenshot({path:path.join(out,`ending-${i}-${width}.png`)});}}
  assert.equal(await p.evaluate(()=>G.turn),turn);await p.locator('#ending-replay').click();assert.equal(await p.evaluate(()=>VILLAGE.cleared),cleared);assert.equal(await p.evaluate(()=>RPG_ENDING.index),0);
  await p.keyboard.press('Escape');assert.equal(await p.locator('#ending-pause').textContent(),'自動播放');
  for(let i=1;i<9;i++)await p.locator('#ending-next').click();await p.locator('#ending-return').click();await p.locator('#village.show').waitFor();
  await p.evaluate(()=>{for(const n of RPG_TOWN.state.npcs){n.goal=null;n.next=999;}Object.assign(RPG_TOWN.state.p,{x:5,y:7.6});VILLAGE.relicSeals={ember:1,tide:1,crystal:1,sky:1};VILLAGE.relicForged=false;});
  await p.locator('#town-action').click();await p.getByRole('button',{name:'四像封印 · 諸神的黃昏'}).click();await bounds('#town-modal');
  await p.screenshot({path:path.join(out,`relic-forge-${width}.png`)});await p.getByRole('button',{name:'融合四印 · 鑄成究極之劍'}).click();assert(await p.evaluate(()=>VILLAGE.relicForged));
  assert.deepEqual(errors,[]);report.push({width,height,errors,endingScenes:9,oneCraft:true});console.log('PASS presentation '+width+'x'+height);await p.close();
 }
 const p=await b.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});await p.goto('http://127.0.0.1:8876/?qa=floor&act=tower');await p.waitForFunction(()=>globalThis.RPG_ENDING);await p.evaluate(()=>{G.over=true;ending();});assert.equal(await p.locator('#ending-pause').textContent(),'自動播放');await p.waitForTimeout(1500);assert.equal(await p.evaluate(()=>RPG_ENDING.index),0);report.push({reducedMotion:'manual, stable'});await p.close();
 fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2));
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
