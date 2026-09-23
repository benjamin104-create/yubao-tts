const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});const out=path.resolve(__dirname,'../work/rpg-v19');fs.mkdirSync(out,{recursive:true});
try{const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8876/?qa=village&act=1');await page.waitForFunction(()=>RPG_TOWN.state&&HD_LOADED['hd:town-healer']);
const click=async name=>page.getByRole('button',{name,exact:true}).click();
const close=async()=>page.keyboard.press('Escape');
async function talk(id){await page.evaluate(id=>{const n=RPG_TOWN.state.npcs.find(x=>x.id===id);n.goal=null;n.next=999;Object.assign(RPG_TOWN.state.p,{x:n.x+(id==='archivist'?1:0),y:n.y+(id==='archivist'?0:1)});},id);await click('A 交談 / 調查');}
await click('委託');await click('承接：修復蓄水池');await close();await talk('mason');await click('接過扳手與操作提示');
await page.evaluate(()=>Object.assign(RPG_TOWN.state.p,{x:10,y:9}));await click('A 交談 / 調查');await click('引水閥');assert.equal(await page.evaluate(()=>VILLAGE.townStory[villageStyle()+':valve']),0);await click('重新調整');
const before=await page.evaluate(()=>[VILLAGE.gold,VILLAGE.forgeOre]);await click('止水閥');await click('清淤閥');await click('引水閥');assert.deepEqual(await page.evaluate(()=>[VILLAGE.gold,VILLAGE.forgeOre]),[before[0]+180,before[1]+2]);await close();
await click('委託');await click('承接：尋找商隊貨箱');
for(const x of [4,16]){await page.evaluate(x=>Object.assign(RPG_TOWN.state.p,{x,y:13}),x);await click('A 交談 / 調查');await close();}
await talk('merchant');await click('關於遺落的貨箱');await click('送給傷患 · 3 塊精礦');assert.equal(await page.evaluate(()=>VILLAGE.townStory[villageStyle()+':caravan']),3);await close();
await talk('archivist');await close();assert.equal(await page.evaluate(()=>VILLAGE.townStory[villageStyle()+':archive']),1);
await page.evaluate(()=>{VILLAGE.alchemyStock=[{cat:'herb',id:'psn'},{cat:'herb',id:'heal'}];VILLAGE.reagents={leaf:2,spore:1,ink:2,spark:2};VILLAGE.travelSupplies=[];});
await talk('healer');await click('魔法調合與素材寄存');await page.screenshot({path:path.join(out,'alchemy-390.png')});
await click('提煉 毒草 → 異質孢粉 ×1');assert.equal(await page.evaluate(()=>VILLAGE.reagents.spore),2);
await click('保留原用途：打包 回復草');assert.equal(await page.evaluate(()=>VILLAGE.alchemyStock.length),0);
const card=page.locator('.alchemy-recipes article').filter({has:page.locator('b',{hasText:'凝神露'})});await card.getByRole('button',{name:'調合 1 份'}).click();assert(await page.evaluate(()=>VILLAGE.travelSupplies.some(q=>q.id==='mana')));
for(const [width,height]of [[360,640],[844,390],[1200,900]]){await page.setViewportSize({width,height});await page.screenshot({path:path.join(out,`alchemy-${width}.png`)});const box=await page.locator('#town-modal').boundingBox();assert(box.y>=0&&box.y+box.height<=height+1);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);assert(await page.locator('#town-modal-actions').evaluate(e=>e.getBoundingClientRect().bottom<=innerHeight));}
await close();await page.evaluate(()=>{closeVillage();newGame(8912);RPG_TOWN.takeSupplies();});assert(await page.evaluate(()=>G.p.inv.some(q=>q.id==='mana')&&VILLAGE.travelSupplies.length===0));
await page.goto('http://127.0.0.1:8876/?qa=floor&act=temple&floor=3');await page.waitForFunction(()=>HD_LOADED['hd:keeper-slam']);
await page.setViewportSize({width:1200,height:900});
const frames=await page.evaluate(()=>{const g=G;g.mons=[];g.p.x=10;g.p.y=11;for(let y=6;y<15;y++)for(let x=6;x<15;x++){g.f.t[key(x,y)]=1;g.seen[key(x,y)]=2;}const m=spawnMon(bossById('b_keeper'),10,10);globalThis.qaKeeper=m;camX=10-VW/2;camY=10-VH/2;return ['idle','anticipation','slam','recovery','hit','defeat'].map(k=>({k,w:HD_LOADED['hd:keeper-'+k]?.width}));});assert(frames.every(f=>f.w===384));
for(const phase of ['idle','anticipation','slam','recovery','hit','defeat']){
await page.evaluate(phase=>{const m=globalThis.qaKeeper;m.warn=null;m.lunge=null;m.recoil=null;m.openUntil=-1;if(phase==='anticipation')m.warn={kind:'slam',cx:m.x,cy:m.y,x:G.p.x,y:G.p.y};if(phase==='recovery')m.openUntil=G.turn+999;if(phase==='slam')m.lunge={dx:0,dy:1,t:0,dur:50,kind:'slam'};if(phase==='hit')m.recoil={dx:0,dy:-1,t:0,dur:50};if(phase==='defeat'){kill(m);if(G.corpses[0])G.corpses[0].dur=50;}refresh();},phase);
await page.waitForTimeout(60);await page.screenshot({path:path.join(out,`boss-${phase}.png`)});}
assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'events-report.json'),JSON.stringify({waterReward:true,caravanChoice:true,archiveRecipe:true,distill:true,retainItem:true,craft:true,transferOnce:true,viewports:4,frames,errors},null,2));console.log('Village events, crafting transactions, four layouts and six boss poses passed.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
