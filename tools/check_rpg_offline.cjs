const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('url'),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});try{
const p=await b.newPage({viewport:{width:390,height:844}}),errors=[],network=[];p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
const out=path.resolve(__dirname,process.env.RPG_OUTPUT||'../work/rpg-v19');fs.mkdirSync(out,{recursive:true});
const base=pathToFileURL(path.resolve(__dirname,process.env.RPG_BUILD||'../dist/babel-rpg-v19.html')).href;
await p.goto(base);await p.waitForFunction(()=>HD_LOADED['hero-worn:helm#front']);
if(await p.evaluate(()=>!!globalThis.RPG_COVER)){
 assert.equal(await p.locator('#cover-party canvas').count(),3);assert.equal(await p.locator('#cols button').count(),4);
 await p.locator('#cols button[data-color="magenta"]').click();assert.equal(await p.evaluate(()=>VILLAGE.col),'magenta');
 assert(await p.evaluate(()=>document.getElementById('coverposter').style.backgroundImage.includes('data:image/')));
 await p.screenshot({path:path.join(out,'offline-cover-mobile.png')});
}
await p.goto(base+'?qa=village&act=1');await p.waitForFunction(()=>HD_LOADED['hd:keeper-slam']&&HD_LOADED['hd:town-healer']&&RPG_TOWN.state&&globalThis.RPG_BOSS_FX);
assert.equal(await p.locator('#town-world').count(),1);
await p.evaluate(()=>{for(const actor of RPG_TOWN.state.npcs){actor.goal=null;actor.next=999;}const n=RPG_TOWN.state.npcs.find(n=>n.id==='healer');RPG_TOWN.state.p.x=n.x;RPG_TOWN.state.p.y=n.y+.25;});await p.locator('#town-action').click();await p.getByRole('button',{name:'魔法調合與素材寄存'}).click();assert.equal(await p.locator('.alchemy-recipes article').count(),6);
await p.screenshot({path:path.join(out,'offline-alchemy.png')});await p.keyboard.press('Escape');
await p.goto(base+'?qa=floor&act=tower');await p.waitForFunction(()=>RPG_BALCONY.door&&HD_LOADED['hd:terrace']);
await p.evaluate(()=>{G.mons=[];const d=RPG_BALCONY.door;G.p.x=d.x;G.p.y=d.y+1;});await p.keyboard.press('ArrowUp');await p.locator('#tower-terrace').waitFor({state:'visible'});await p.screenshot({path:path.join(out,'offline-terrace-mobile.png')});
await p.getByRole('button',{name:'走回塔門'}).click();await p.locator('#tower-terrace').waitFor({state:'hidden'});
if(await p.evaluate(()=>!!globalThis.RPG_ENDING)){
 await p.evaluate(()=>{G.over=true;ending();});await p.locator('#ending-pause').click();
 for(let i=0;i<3;i++){if(i)await p.locator('#ending-next').click();await p.waitForFunction(()=>[...document.querySelectorAll('#ending-cast img')].every(im=>im.complete&&im.naturalWidth>0));}
 await p.screenshot({path:path.join(out,'offline-ending-mobile.png')});
 assert(await p.evaluate(()=>!!HD_LOADED['hd:hunter-lion-idle']&&!!HD_LOADED['hd:hunter-wall-emerge']&&!!HD_LOADED['weap#10']));
}
assert.deepEqual(errors,[]);assert.deepEqual(network,[]);const report=await p.evaluate(()=>({hdFailures:HD_FAILURES,assets:Object.keys(BABEL_HD_MANIFEST).length,chapters:ACTS.length,recipes:ALCHEMY_RECIPES.length}));assert.deepEqual(report.hdFailures,[]);
fs.writeFileSync(path.join(out,'offline-report.json'),JSON.stringify({...report,errors,network},null,2));console.log(report);
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
