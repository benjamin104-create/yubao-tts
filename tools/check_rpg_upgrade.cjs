const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const out=path.resolve(__dirname,'../work/rpg-v19');fs.mkdirSync(out,{recursive:true});
 try{
  for(const [width,height] of [[1200,900],[390,844],[844,390],[360,640]]){
   const page=await browser.newPage({viewport:{width,height}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto('http://127.0.0.1:8876/?qa=village&act=1');
   await page.waitForFunction(()=>globalThis.RPG_TOWN?.state&&HD_LOADED['hd:town-euro-forge']);
   await page.screenshot({path:path.join(out,`town-${width}.png`)});
   const layout=await page.evaluate(()=>({scroll:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],size:[innerWidth,innerHeight],canvas:document.getElementById('town-world').getBoundingClientRect().toJSON(),button:document.getElementById('town-action').getBoundingClientRect().toJSON()}));
   assert(layout.scroll[0]<=width+1&&layout.scroll[1]<=height+1,JSON.stringify(layout));
   assert(layout.button.bottom<=height+1&&layout.canvas.height>100,JSON.stringify(layout));
   const initial=await page.evaluate(()=>({x:RPG_TOWN.state.p.x,y:RPG_TOWN.state.p.y,npcs:RPG_TOWN.state.npcs.map(n=>[n.x,n.y])}));
   await page.keyboard.down('ArrowRight');await page.waitForTimeout(360);await page.keyboard.up('ArrowRight');
   assert((await page.evaluate(()=>RPG_TOWN.state.p.x))>initial.x+.3,'town movement');
   await page.evaluate(()=>{const n=RPG_TOWN.state.npcs.find(n=>n.id==='smith');Object.assign(RPG_TOWN.state.p,{x:n.x,y:n.y+1});});
   await page.locator('#town-action').click();await page.locator('#town-modal').waitFor({state:'visible'});
   assert(await page.locator('#town-modal #vstock').count(),'shop mounted');
   const p=await page.evaluate(()=>({x:G.p.x,y:G.p.y,t:G.turn}));
   await page.keyboard.press('ArrowRight');assert.deepEqual(await page.evaluate(()=>({x:G.p.x,y:G.p.y,t:G.turn})),p,'modal blocks dungeon');
   await page.screenshot({path:path.join(out,`shop-${width}.png`)});
   await page.keyboard.press('Escape');
   await page.evaluate(()=>{const n=RPG_TOWN.state.npcs.find(n=>n.id==='child');Object.assign(RPG_TOWN.state.p,{x:n.x,y:n.y+1});});
   await page.locator('#town-action').click();await page.getByRole('button',{name:'幫忙找鈴鐺',exact:true}).click();
   await page.evaluate(()=>Object.assign(RPG_TOWN.state.p,{x:3,y:13}));
   await page.locator('#town-action').click();assert.equal(await page.evaluate(()=>VILLAGE.townQuest[villageStyle()]),2);
   await page.keyboard.press('Escape');
   await page.evaluate(()=>{const n=RPG_TOWN.state.npcs.find(n=>n.id==='child');Object.assign(RPG_TOWN.state.p,{x:n.x,y:n.y+1});});
   await page.locator('#town-action').click();const gold=await page.evaluate(()=>VILLAGE.gold);
   await page.getByRole('button',{name:'交還鈴鐺，領取 80 G',exact:true}).click();assert.equal(await page.evaluate(()=>VILLAGE.gold),gold+80);
   assert.equal(errors.length,0,errors.join('\n'));console.log(JSON.stringify({width,height,layout,errors}));await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
