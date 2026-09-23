const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const root=path.resolve(__dirname,'../work/hd-wear');fs.mkdirSync(root,{recursive:true});
  const results=[];
  for(const act of ['temple','forest','crystal','tower']){
    const page=await browser.newPage({viewport:{width:1200,height:900}});const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8876/?qa=floor&act='+act+'&seed=260822');
    await page.waitForFunction(()=>Object.keys(HD_ASSETS).filter(k=>k.startsWith('hero-worn:')).every(k=>HD_LOADED[k]));
    await page.evaluate(()=>{G.p.hat='helm';VILLAGE.skin='blob';VILLAGE.col='#';heroArtIn();refresh();});
    await page.screenshot({path:path.join(root,'scene-'+act+'.png')});
    results.push(await page.evaluate(()=>({act:G.act,hd:HD_MODE,failed:HD_FAILURES,weaponKeys:Object.keys(HD_LOADED).filter(k=>k.startsWith('weap#')),worn:!!hdHeroSprite(-1,-1,'helm','blob','#',[0,1])})));
    if(errors.length)throw Error(errors.join('\n'));await page.close();
  }
  const mobile=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:2});
  await mobile.goto('http://127.0.0.1:8876/?qa=floor&act=temple');
  await mobile.waitForFunction(()=>HD_LOADED['hero-worn:helm#front']);
  await mobile.evaluate(()=>{G.p.hat='helm';refresh();});
  await mobile.screenshot({path:path.join(root,'scene-mobile.png')});
  console.log(JSON.stringify(results,null,2));await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
