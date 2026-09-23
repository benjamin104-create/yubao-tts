const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});try{
 const p=await b.newPage(),errors=[],report=[];p.on('pageerror',e=>errors.push(e.message));await p.goto('http://127.0.0.1:8876/?qa=floor&act=mine');await p.waitForFunction(()=>globalThis.RPG_ENDING);await p.mouse.click(5,5);await p.evaluate(()=>{BGM.stop();SFX.unlock();});
 for(const id of ['ending_afterglow','ending_home','ending_horizon']){
  await p.evaluate(id=>{const t=BGM.TRACKS[id];if(!t||!t.lead.flat().every(([s,n,d])=>s>=0&&s+d<=16&&n>20&&n<110))throw Error(id);BGM.force(id);BGM.start();},id);await p.waitForTimeout(1600);
  const meter=await p.evaluate(()=>new Promise(resolve=>{const c=SFX.ctx(),a=c.createAnalyser();a.fftSize=2048;SFX.bus().connect(a);const v=new Float32Array(2048);let peak=0,sum=0,n=0,start=performance.now();function tick(){a.getFloatTimeDomainData(v);for(const x of v){peak=Math.max(peak,Math.abs(x));sum+=x*x;n++;}if(performance.now()-start<2200)requestAnimationFrame(tick);else{SFX.bus().disconnect(a);resolve({peak:20*Math.log10(peak||1e-9),rms:20*Math.log10(Math.sqrt(sum/n)||1e-9),state:c.state});}}tick();}));
  assert(meter.peak<-1&&meter.rms>-48&&meter.state==='running',JSON.stringify({id,meter}));report.push({id,...meter});
 }
 assert.deepEqual(errors,[]);fs.writeFileSync(path.resolve(__dirname,'../work/rpg-v21/audio-report.json'),JSON.stringify(report,null,2));console.log(report);
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
