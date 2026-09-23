const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const url=process.env.GAME_URL||'https://benjamin104-create.github.io/yubao-tts/?v=20260924-v22';
 const out=path.resolve(__dirname,'../work/publish-v22');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true}),errors=[],httpErrors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&!r.url().includes('favicon'))httpErrors.push([r.status(),r.url()]);});
  const response=await page.goto(url,{timeout:60000});assert.equal(response.status(),200);
  await page.waitForFunction(()=>globalThis.RPG_COVER&&HD_LOADED['hero-worn:helm#front']&&HD_LOADED['hero-worn:plume#side']&&HD_LOADED['hero-worn:cone#side'],{},{timeout:60000});
  assert.equal(await page.locator('#cols button').count(),4);
  await page.getByRole('button',{name:'霸王黑',exact:true}).tap();assert.equal(await page.evaluate(()=>VILLAGE.col),'gunmetal');
  const ranger=await page.locator('#cover-ranger').boundingBox(),mage=await page.locator('#cover-mage').boundingBox();assert(ranger.x<mage.x);
  await page.screenshot({path:path.join(out,'live-cover-phone.png')});
  await page.reload();await page.waitForFunction(()=>!!globalThis.RPG_COVER);assert.equal(await page.evaluate(()=>VILLAGE.col),'gunmetal');
  await page.locator('#start').tap();await page.locator('#prologue.show').waitFor();await page.locator('#proskip').tap();await page.locator('#prologue').waitFor({state:'hidden'});
  await page.waitForTimeout(500);
  await page.locator('#btnB').tap();await page.locator('#panel-tabs').getByRole('button',{name:'技能',exact:true}).tap();assert.equal(await page.evaluate(()=>panelMode),'magic');
  await page.locator('#panel-tabs').getByRole('button',{name:'背包',exact:true}).tap();assert.equal(await page.evaluate(()=>panelMode),'inv');await page.keyboard.press('Escape');
  await page.screenshot({path:path.join(out,'live-game-phone.png')});
  for(const selector of ['#hp','#btnA','#btnB','#game']){const r=await page.locator(selector).boundingBox();assert(r&&r.y>=0&&r.y+r.height<=845,selector+' outside phone viewport');}
  const state=await page.evaluate(()=>({colour:VILLAGE.col,hdFailures:HD_FAILURES,assets:Object.keys(HD_ASSETS).length,saved:!!loadedRun()}));
  assert(state.saved,'new run has a resume point');assert.deepEqual(state.hdFailures,[]);
  const townUrl=new URL(url);townUrl.searchParams.set('qa','village');townUrl.searchParams.set('act','1');
  await page.goto(townUrl.href);await page.waitForFunction(()=>globalThis.RPG_TOWN?.state&&HD_LOADED['hd:town-healer']);
  await page.evaluate(()=>{for(const n of RPG_TOWN.state.npcs){n.goal=null;n.next=999;}const n=RPG_TOWN.state.npcs.find(n=>n.id==='healer');Object.assign(RPG_TOWN.state.p,{x:n.x,y:n.y+.6});});
  await page.locator('#town-action').tap();await page.getByRole('button',{name:'魔法調合與素材寄存',exact:true}).tap();assert.equal(await page.locator('.alchemy-recipes article').count(),6);
  await page.screenshot({path:path.join(out,'live-alchemy-phone.png')});
  assert.deepEqual(errors,[]);assert.deepEqual(httpErrors,[]);
  fs.writeFileSync(path.join(out,'live-report.json'),JSON.stringify({url,...state,townAlchemy:true,errors,httpErrors},null,2));console.log('PASS phone cover, Overlord Black, persistence, opening, tabs, resume point and town alchemy: '+url);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
