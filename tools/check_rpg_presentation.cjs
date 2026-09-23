const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const out=path.resolve(__dirname,'../work/rpg-v19');fs.mkdirSync(out,{recursive:true});const report=[];
 try{
  const page=await browser.newPage({viewport:{width:1200,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8876/?qa=floor&act=tower');await page.waitForFunction(()=>globalThis.RPG_BALCONY?.door&&HD_LOADED['hd:chapter-tower']);
  const before=await page.evaluate(()=>{G.mons=[];const d=RPG_BALCONY.door;G.p.x=d.x;G.p.y=d.y+1;refresh();return {x:G.p.x,y:G.p.y,turn:G.turn,hp:G.p.hp,inv:JSON.stringify(G.p.inv)};});
  await page.keyboard.press('ArrowUp');await page.locator('#tower-terrace').waitFor({state:'visible'});
  await page.keyboard.down('ArrowRight');await page.waitForTimeout(700);await page.keyboard.up('ArrowRight');
  await page.screenshot({path:path.join(out,'terrace-desktop.png')});await page.locator('#terrace-return').click();await page.locator('#tower-terrace').waitFor({state:'hidden'});
  assert.deepEqual(await page.evaluate(()=>({x:G.p.x,y:G.p.y,turn:G.turn,hp:G.p.hp,inv:JSON.stringify(G.p.inv)})),before,'terrace preserves dungeon');
  for(const [width,height]of [[390,844],[844,390],[360,640],[1200,900]]){
    await page.setViewportSize({width,height});await page.evaluate(()=>{openPanel('inv');});
    await page.waitForTimeout(250);
    const box=await page.locator('#panel').boundingBox();assert(box.x>=-1&&box.y>=-1&&box.x+box.width<=width+1&&box.y+box.height<=height+1,JSON.stringify({width,height,box}));
    const pos=await page.evaluate(()=>[G.p.x,G.p.y]);await page.keyboard.press('ArrowDown');assert.deepEqual(await page.evaluate(()=>[G.p.x,G.p.y]),pos,'inventory does not move player');
    await page.locator('#panel-tabs').getByRole('button',{name:'技能',exact:true}).click();assert.equal(await page.evaluate(()=>panelMode),'magic');
    await page.locator('#panel-tabs').getByRole('button',{name:'背包',exact:true}).click();await page.screenshot({path:path.join(out,`inventory-${width}.png`)});
    await page.keyboard.press('Escape');
  }
  await page.setViewportSize({width:1200,height:900});
  for(const act of ['temple','forest','hall','tower']){
    await page.evaluate(id=>playChapterPrelude(ACTS.findIndex(a=>a.id===id),()=>{},true),act);await page.waitForTimeout(700);
    assert((await page.locator('#prologueart').evaluate(el=>el.style.backgroundImage)).includes('hd-chapter-'+act),'new chapter art');
    await page.screenshot({path:path.join(out,`cinema-${act}.png`)});await page.locator('#proskip').click();
  }
  const scores=await page.evaluate(()=>ACTS.map(a=>{const t=BGM.TRACKS['chapter_'+a.id];return{id:a.id,exists:!!t,title:t?.title,bpm:t?.bpm,bars:t?.bars,answer:t?.answer,lead:t?.lead};}));
  for(const t of scores){assert(t.exists&&t.bars===16,t.id);assert.equal(t.answer.length,4);for(const bar of [...t.answer,...t.lead])for(const [s,n,d]of bar)assert(s>=0&&s+d<=16&&n>20&&n<110,t.id);}
  assert.equal(new Set(scores.map(t=>JSON.stringify([t.lead,t.answer]))).size,18,'18 chapter compositions');
  await page.evaluate(()=>{BGM.stop();SFX.unlock();});
  for(const id of ['chapter_temple','chapter_heian','chapter_tower','terrace']){
    await page.evaluate(id=>{BGM.force(id);BGM.start();},id);await page.waitForTimeout(1500);
    for(const section of [0,2]){
      await page.evaluate(n=>BGM.qaSection(n),section);
      const meter=await page.evaluate(()=>new Promise(resolve=>{const c=SFX.ctx(),a=c.createAnalyser();a.fftSize=2048;SFX.bus().connect(a);const v=new Float32Array(a.fftSize);let peak=0,sum=0,n=0,start=performance.now();function tick(){a.getFloatTimeDomainData(v);for(const x of v){peak=Math.max(peak,Math.abs(x));sum+=x*x;n++;}if(performance.now()-start<2200)requestAnimationFrame(tick);else{SFX.bus().disconnect(a);resolve({peak:20*Math.log10(peak||1e-9),rms:20*Math.log10(Math.sqrt(sum/n)||1e-9),state:c.state});}}tick();}));
      assert(meter.peak<-1&&meter.rms>-45,JSON.stringify({id,section,meter}));report.push({id,section,...meter});
    }
  }
  assert.equal(errors.length,0,errors.join('\n'));report.push({scores:scores.map(({id,title,bpm,bars})=>({id,title,bpm,bars})),errors});
  fs.writeFileSync(path.join(out,'presentation-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
