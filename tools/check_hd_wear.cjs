/* Render the actual game's compositor, not a mockup. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:true});
  const page = await browser.newPage({viewport:{width:1320,height:1000},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror', e=>errors.push(e.message));
  await page.goto(process.env.QA_URL || 'http://127.0.0.1:8876/?qa=menu');
  await page.waitForFunction(()=>typeof HD_LOADED!=='undefined' && HD_LOADED['hero#blob'] && HAT.every(h=>HD_LOADED['hat#'+h.id]));
  await page.evaluate(async()=>{
    await Promise.all(Object.values(HD_ASSETS).map(file=>new Promise(resolve=>{const i=new Image();i.onload=i.onerror=resolve;i.src='art-hd/'+file;})));
  });
  const status=await page.evaluate(()=>({hd:HD_MODE,failed:HD_FAILURES,loaded:Object.keys(HD_LOADED).length,hats:HAT.map(h=>h.id)}));
  await page.evaluate((gear)=>{
    const box=document.createElement('div');box.id='wear-audit';
    box.style='position:fixed;inset:0;z-index:999999;background:#202735;overflow:auto;padding:24px;color:#eee;font:15px sans-serif';
    box.innerHTML='<h1>主角實際穿戴檢查</h1><p>每欄依序：正面、右側、背面；最後一列為遊戲大小。使用遊戲本身的角色繪製函式。</p>';
    const grid=document.createElement('div');grid.style='display:grid;grid-template-columns:repeat(10, 1fr);gap:6px';box.append(grid);
    for(const h of HAT){
      const col=document.createElement('div');col.style='text-align:center;background:#303a4a;border-radius:8px';
      col.innerHTML='<p>'+h.id+'</p>';
      for(const f of [[0,1],[1,0],[0,-1]]){
        const c=document.createElement('canvas');c.width=256;c.height=256;c.style='width:120px;height:120px;display:block';
        c.getContext('2d').drawImage(hdHeroSprite(gear?9:-1,gear?5:-1,h.id,'blob','#',f),0,0);col.append(c);
      }
      const small=document.createElement('canvas');small.width=64;small.height=64;small.style='width:48px;height:48px;margin:10px';
      small.getContext('2d').drawImage(hdHeroSprite(-1,-1,h.id,'blob','#',[0,1]),0,0,64,64);col.append(small);grid.append(col);
    }
    document.body.append(box);
  },!!process.env.AUDIT_GEAR);
  fs.mkdirSync(path.join(root,'work/hd-wear'),{recursive:true});
  await page.locator('#wear-audit').screenshot({path:path.join(root,'work/hd-wear/'+(process.env.AUDIT_NAME||'wear-after')+'.png')});
  console.log(JSON.stringify({...status,errors},null,2));
  await browser.close();
  if(errors.length || status.failed.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
