const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'C:/Users/X/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),path=require('node:path');
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});try{
 const p=await b.newPage({viewport:{width:390,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true});const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:8876/?qa=village&act=10');await p.waitForFunction(()=>RPG_TOWN.state&&HD_LOADED['hd:town-shrine']);
 await p.evaluate(()=>{for(const n of RPG_TOWN.state.npcs){n.goal=null;n.next=999;}Object.assign(RPG_TOWN.state.p,{x:16,y:12.6});});
 await p.locator('#town-action').tap();assert((await p.locator('#town-modal').innerText()).includes('驅魔小祠'));
 await p.screenshot({animations:'disabled',path:path.resolve(__dirname,'../work/rpg-v20/shrine-phone.png')});await p.getByRole('button',{name:'返回村莊',exact:true}).tap();
 await p.goto('http://127.0.0.1:8876/?qa=floor&act=mine');await p.waitForFunction(()=>HD_LOADED['npc#mason']);
 for(const [width,height] of [[390,844],[360,640]]){
  await p.setViewportSize({width,height});await p.evaluate(()=>{G.over=false;G.mons=[];G.f.arena=null;G.f.heianGate=null;G.f.heianSamurai=null;G.f.elapsedTurns=660;refresh();fitViewport();});await p.waitForTimeout(250);
  for(const sel of ['#btnA','#btnB','#btnS','#padup','#paddown']){if(!await p.locator(sel).count())continue;const r=await p.locator(sel).boundingBox();assert(r.x>=0&&r.y>=0&&r.x+r.width<=width+1&&r.y+r.height+15<=height+1,JSON.stringify({sel,r,width,height}));assert(r.width>=44&&r.height>=44,JSON.stringify({sel,r}));}
  await p.locator('#btnB').tap();assert(await p.locator('#panel').evaluate(e=>e.classList.contains('open')));await p.locator('#panel-tabs').getByRole('button',{name:'技能',exact:true}).tap();await p.locator('#panel-tabs').getByRole('button',{name:'背包',exact:true}).tap();assert.equal(await p.evaluate(()=>G.f.elapsedTurns),660);await p.keyboard.press('Escape');
 }
 await p.setViewportSize({width:1200,height:900});await p.evaluate(()=>{G.f.elapsedTurns=719;dwellCheck();refresh();});assert.equal(await p.evaluate(()=>G.floor),2);await p.screenshot({animations:'disabled',path:path.resolve(__dirname,'../work/rpg-v20/collapse.png')});
 await p.waitForTimeout(1200);assert(await p.locator('#floor-collapse').isHidden());assert.deepEqual(errors,[]);console.log('PASS real touch events, 3x DPR, mobile bounds, tabs, paused pressure, collapse presentation');
 }finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
