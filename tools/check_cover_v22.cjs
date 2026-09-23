const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});const out=path.resolve(__dirname,'../work/rpg-v22');fs.mkdirSync(out,{recursive:true});const report=[];try{
 for(const [width,height]of process.env.COVER_PALETTE_ONLY?[]:[[390,844],[360,640],[320,568],[844,390],[1200,900]]){
  const p=await b.newPage({viewport:{width,height},hasTouch:width<621,isMobile:width<621}),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto('http://127.0.0.1:8876/');
  await p.waitForFunction(()=>globalThis.RPG_COVER&&['helm#front','cone#side','plume#side'].every(k=>HD_LOADED['hero-worn:'+k])&&HD_LOADED['weap#3']&&HD_LOADED['shld#2']);await p.waitForTimeout(350);
  assert.equal(await p.locator('#cols button').count(),4);
  const equipment=await p.evaluate(()=>JSON.stringify([G.p.hat,G.p.weap,G.p.shld,G.p.inv]));
  for(const color of ['#','l','magenta','gunmetal']){
   await p.locator('#cols button').filter({has:p.locator('span')}).evaluateAll((bs,c)=>bs.find(b=>b.dataset.color===c).click(),color);
   assert.equal(await p.evaluate(()=>VILLAGE.col),color);assert.equal(await p.evaluate(()=>JSON.stringify([G.p.hat,G.p.weap,G.p.shld,G.p.inv])),equipment,'preview does not grant equipment');
   assert.equal(await p.locator('#cols button[aria-pressed="true"]').count(),1);
   for(const sel of ['#covertext','#cover-party','#cols','#start','#covermusic','#pname']){const z=await p.locator(sel).boundingBox();assert(z&&z.x>=-1&&z.y>=-1&&z.x+z.width<=width+1&&z.y+z.height<=height+1,JSON.stringify({width,height,sel,z}));}
   const size=await p.locator('#cols button').first().boundingBox();assert(size.width>=44&&size.height>=44);
   if(width===390||color==='#')await p.screenshot({path:path.join(out,`cover-${color==='#'?'orange':color}-${width}.png`)});
  }
  await p.reload();await p.waitForFunction(()=>globalThis.RPG_COVER&&HD_LOADED['hero-worn:helm#front']);assert.equal(await p.evaluate(()=>VILLAGE.col),'gunmetal','saved colour survives reload');
  await p.evaluate(()=>{saveRun();refreshResume();});assert(await p.locator('#resume').isVisible());for(const sel of ['#resume','#cover-party','#start','#cols']){const z=await p.locator(sel).boundingBox();assert(z&&z.y>=-1&&z.y+z.height<=height+1,'resume layout '+sel);}if(width===320)await p.screenshot({path:path.join(out,'cover-resume-320.png')});
  assert.deepEqual(errors,[]);report.push({width,height,errors,colors:4,save:'persists',preview:'no equipment mutation'});console.log('PASS cover '+width+'x'+height);await p.close();
 }
 const p=await b.newPage({viewport:{width:1200,height:900}});await p.goto('http://127.0.0.1:8876/?qa=floor&act=mine');await p.waitForFunction(()=>globalThis.RPG_COVER&&HD_LOADED['hero-worn:helm#front']&&HD_LOADED['shld#2']);
 const palette=await p.evaluate(()=>{
  const samples=COVER_COLORS.map(col=>{const c=hdHeroSprite(3,2,'helm','blob',col,[0,1]),x=c.getContext('2d');return {col,canvas:c,pixels:Array.from(x.getImageData(0,0,256,256).data),image:c.toDataURL(),crown:Array.from(x.getImageData(0,0,256,98).data),face:Array.from(x.getImageData(95,178,12,12).data)};});
  G.p.hat='helm';G.p.weap=mk('weap','steel');G.p.shld=mk('shld','steel');VILLAGE.col='gunmetal';refreshHero();
  const current=heroNow(),pixels=current.getContext('2d').getImageData(0,0,256,256).data;
  // Chrome may round a translucent channel by one during GPU canvas readback.
  const maxChannelDelta=pixels.reduce((d,v,i)=>Math.max(d,Math.abs(v-samples[3].pixels[i])),0);
  return {unique:new Set(samples.map(s=>s.image)).size,crownStable:samples.every(s=>s.crown.every((v,i)=>Math.abs(v-samples[0].crown[i])<=1)),gameMatches:current===samples[3].canvas&&maxChannelDelta<=1,maxChannelDelta}; });console.log(palette);assert.equal(palette.unique,4);assert(palette.crownStable,'hat colours remain unchanged');assert(palette.gameMatches,'cover and game use identical equipped sprite');report.push(palette);
 // Make the body-only palettes reviewable alongside the real fitted costumes.
 await p.evaluate(()=>{const box=document.createElement('div');box.id='palette-audit';box.style='position:fixed;inset:0;z-index:99999;background:#102433;color:#eadcc2;padding:25px;font:18px sans-serif;display:grid;grid-template-columns:repeat(4,1fr);gap:16px';
 for(const col of COVER_COLORS){const cell=document.createElement('div');cell.textContent=coverColorLabel(col);for(const [hat,face]of [['helm',[0,1]],['cone',[1,0]],['plume',[-1,0]]]){const img=hdHeroSprite(3,2,hat,'blob',col,face),c=document.createElement('canvas');c.width=c.height=256;c.style='display:block;width:225px;height:225px';c.getContext('2d').drawImage(img,0,0);cell.append(c);}box.append(cell);}document.body.append(box);});
 await p.locator('#palette-audit').screenshot({path:path.join(out,'palette-wear-audit.png')});await p.close();fs.writeFileSync(path.join(out,'cover-report.json'),JSON.stringify(report,null,2));
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1});





