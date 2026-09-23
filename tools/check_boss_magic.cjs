const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const out=path.resolve(__dirname,'../work/rpg-v19');const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});try{
 const ctx=await b.newContext({viewport:{width:1100,height:800}});const p=await ctx.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:8876/?qa=floor&act=forest&floor=7');await p.waitForFunction(()=>RPG_BOSS_FX&&HD_LOADED['b_treant']);
 await p.evaluate(()=>{const chunks=[],stream=document.getElementById('game').captureStream(24),r=new MediaRecorder(stream,{mimeType:'video/webm',videoBitsPerSecond:2200000});globalThis.magicRecording={r,chunks,stream};r.ondataavailable=e=>chunks.push(e.data);r.start();});
 await p.evaluate(()=>{G.mons=[];G.items={};G.gold={};G.p.x=10;G.p.y=14;G.p.hp=G.p.mhp=100;for(let y=6;y<=16;y++)for(let x=5;x<=15;x++){G.f.t[key(x,y)]=1;G.seen[key(x,y)]=2;}const m=spawnMon(bossById('b_treant'),10,10);m.qWarn=1;m.d={...m.d,adds:null,ward:null};globalThis.fxBoss=m;camX=10-VW/2;camY=11-VH/2;});
 await p.waitForTimeout(350);await p.screenshot({path:path.join(out,'magic-root-charge.png')});
 const before=await p.evaluate(()=>[G.turn,G.p.hp,G.p.x,G.p.y,G.f.t.join(',')]);
 await p.evaluate(()=>{fxBoss.qWarn=0;RPG_BOSS_FX.release(fxBoss,'quake');});await p.waitForTimeout(500);await p.screenshot({path:path.join(out,'magic-root-impact.png')});
 assert.deepEqual(await p.evaluate(()=>[G.turn,G.p.hp,G.p.x,G.p.y,G.f.t.join(',')]),before,'presentation cannot change combat state');
 await p.waitForTimeout(1250);assert.equal(await p.evaluate(()=>RPG_BOSS_FX.active.length),0);
 for(const [id,kind]of [['b_pyro','quake'],['b_queen','beam'],['b_keeper','slam']]){
   await p.evaluate(([id,kind])=>{fxBoss.d={...bossById(id),boss:1};fxBoss.warn=kind==='slam'?{kind:'slam',x:10,y:11,cx:10,cy:10}:kind==='beam'?{x:10,y:14}:null;fxBoss.qWarn=kind==='quake'?1:0;G.turn++;},[id,kind]);await p.waitForTimeout(500);
   await p.evaluate(kind=>{const aim=fxBoss.warn;fxBoss.warn=null;fxBoss.qWarn=0;RPG_BOSS_FX.release(fxBoss,kind,aim);},kind);await p.waitForTimeout(450);await p.screenshot({path:path.join(out,`magic-${id}.png`)});await p.waitForTimeout(1200);
 }
 const movie=await p.evaluate(()=>new Promise(resolve=>{const {r,chunks,stream}=magicRecording;r.onstop=async()=>{resolve(Array.from(new Uint8Array(await new Blob(chunks,{type:'video/webm'}).arrayBuffer())));stream.getTracks().forEach(t=>t.stop());};r.stop();}));fs.writeFileSync(path.join(out,'boss-magic-demo.webm'),Buffer.from(movie));
 await p.setViewportSize({width:390,height:844});await p.evaluate(()=>{fxBoss.warn={kind:'slam',cx:10,cy:10,x:10,y:11};});await p.waitForTimeout(150);await p.screenshot({path:path.join(out,'magic-mobile.png')});const box=await p.locator('#boss-art-banner').boundingBox();assert(box.x>=0&&box.x+box.width<=390);
 await p.close();await ctx.close();
 const reduced=await b.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});reduced.on('pageerror',e=>errors.push(e.message));await reduced.goto('http://127.0.0.1:8876/?qa=floor&act=temple&floor=3');await reduced.waitForFunction(()=>RPG_BOSS_FX&&G.mons.some(m=>m.d.boss));await reduced.evaluate(()=>{const m=G.mons.find(m=>m.d.boss);RPG_BOSS_FX.release(m,'quake');});await reduced.waitForTimeout(100);assert.equal(await reduced.evaluate(()=>RPG_BOSS_FX.active[0].dur),.5);await reduced.close();
 assert.deepEqual(errors,[]);console.log('Boss magic: four visual families, world-state invariant, effect expiry, mobile banner, reduced motion.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
