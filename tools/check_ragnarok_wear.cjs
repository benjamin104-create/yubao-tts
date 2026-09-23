const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});try{
 const p=await b.newPage({viewport:{width:390,height:844}}),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto('http://127.0.0.1:8876/?qa=floor&act=tower');await p.waitForFunction(()=>globalThis.RPG_ENDING&&HD_LOADED['hero-worn:cone#front']&&HD_LOADED['weap#10']);
 await p.evaluate(()=>{VILLAGE.relicForged=true;G.p.weap=mk('weap','ragnarok',{known:1});G.p.hat='cone';G.over=true;G.won=true;refreshHero();ending();});await p.locator('#ending-pause').click();
 for(let i=0;i<6;i++)await p.locator('#ending-next').click();await p.waitForTimeout(1700);
 assert((await p.locator('#ending-body').innerText()).includes('諸神的黃昏'));assert(await p.locator('.end-hero').evaluate(e=>e.complete&&e.naturalWidth===256));
 await p.screenshot({path:path.resolve(__dirname,'../work/rpg-v21/ragnarok-ending-mobile.png')});assert.deepEqual(errors,[]);console.log('PASS actual equipped Ragnarok with fitted wizard hat in ending');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
