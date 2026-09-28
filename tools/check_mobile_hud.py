"""The readable phone HUD stays between map and controls through viewport changes."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent
BASE=os.environ.get('GAME_URL',(ROOT/'web/index.html').as_uri())
OUT=ROOT/'work/rpg-v23'
OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
    browser=pw.chromium.launch(args=['--allow-file-access-from-files'])
    page=browser.new_page(viewport={'width':390,'height':740},device_scale_factor=3,has_touch=True,is_mobile=True,locale='zh-TW')
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+('&' if '?' in BASE else '?')+'qa=floor&act=tower&seed=81291')
    page.wait_for_function('()=>G&&document.querySelector("#mobile-status-dock #hud")')
    page.evaluate("()=>{G.mons=[];G.p.hp=395;G.p.mhp=395;G.p.mp=242;G.p.mmp=242;G.p.gold=21135;refresh();}")
    for w,h in [(390,740),(390,640),(390,780),(360,560),(844,390),(390,740)]:
        page.set_viewport_size({'width':w,'height':h})
        page.wait_for_timeout(400)
        result=page.evaluate('''()=>{
          const rect=s=>document.querySelector(s).getBoundingClientRect();
          const problems=[];
          for(const s of ['#hud','#hp','#mp','#full','#atk','#def','#gold','#pressure-status','#btnA','#btnB','#btnS']){
            const e=document.querySelector(s),r=rect(s),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
            if(r.top<0||r.bottom>innerHeight+1||r.left<0||r.right>innerWidth+1||!hit||!(e.contains(hit)||hit.contains(e)))problems.push(s);
          }
          if(innerWidth<=620){
            if(rect('#hud').top<rect('#game').bottom-1)problems.push('HUD covers map');
            if(rect('#pressure-status').bottom>rect('#cross').top)problems.push('HUD covers controls');
            if(document.querySelectorAll('#mobile-status-dock #hud').length!==1)problems.push('HUD not docked');
          }else if(document.querySelector('#hud').parentElement.id!=='cabinet')problems.push('desktop HUD not restored');
          return {problems,cell:rect('#game').width/VW,cols:VW,rows:VH,width:rect('#game').width,top:rect('#game').top,padding:getComputedStyle(document.querySelector('#screenwrap')).paddingBottom};
        }''')
        assert not result['problems'],(w,h,result)
        if w==390:assert result['cell']>=32,result
        print('PASS HUD',w,h,result,flush=True)
    page.screenshot(path=str(OUT/'hud-phone.png'))
    # Safari may shift the visual viewport without resizing the layout viewport.
    page.evaluate('''()=>{
      Object.defineProperty(visualViewport,'offsetTop',{configurable:true,value:70});
      Object.defineProperty(visualViewport,'height',{configurable:true,value:620});
      visualViewport.dispatchEvent(new Event('scroll'));
    }''')
    page.wait_for_timeout(400)
    assert page.evaluate('''()=>{
      const h=document.querySelector('#hud').getBoundingClientRect(),a=document.querySelector('#btnA').getBoundingClientRect();
      return h.top>=70&&a.bottom<=690;
    }''')
    page.add_style_tag(content='#cabinet{padding-top:44px!important;padding-bottom:34px!important}')
    page.evaluate('()=>fitViewport()')
    assert page.evaluate('''()=>{
      const h=document.querySelector('#hud').getBoundingClientRect(),a=document.querySelector('#btnA').getBoundingClientRect();
      return h.top>=114&&a.bottom<=656;
    }''')
    assert not errors,errors
    print('PASS shifted visual viewport and no runtime errors',flush=True)
    browser.close()
