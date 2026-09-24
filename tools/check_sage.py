"""The equipped circlet must show a real job and usable skills on small screens."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent
BASE=os.environ.get('GAME_URL',(ROOT/'web/index.html').as_uri()).split('?')[0]
OUT=ROOT/'work/rpg-v23'
OUT.mkdir(parents=True,exist_ok=True)

with sync_playwright() as pw:
    browser=pw.chromium.launch(args=['--allow-file-access-from-files'])
    for width,height in [(360,640),(390,844),(844,390)]:
        page=browser.new_page(viewport={'width':width,'height':height},has_touch=True,locale='zh-TW')
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'?qa=floor&act=tower&seed=81291')
        page.wait_for_function('()=>G&&globalThis.RPG_PLAYER_FX')
        page.evaluate('''()=>{
          G.mons=[];VILLAGE.jobs.sage={lv:0,prog:0};wearHat(mk('hat','circlet'));
          openPanel('magic');
        }''')
        assert '賢者' in page.locator('#list').inner_text()
        assert '靜心' in page.locator('#list').inner_text()
        assert '找一頂帽子' not in page.locator('#list').inner_text()
        page.evaluate('''()=>{for(let i=0;i<4;i++)jobLevelUp();G.p.lv=24;G.p.mmp=maxMp(G.p);G.p.mp=10;
          G.p.slots=['meditate','sageward',null];renderPanel();}''')
        row=page.locator('#list .spell').filter(has=page.locator('.nm',has_text='靜心'))
        row.scroll_into_view_if_needed()
        before=page.evaluate('()=>({turn:G.turn,mp:G.p.mp,sat:G.p.sat})')
        page.screenshot(path=str(OUT/f'sage-{width}.png'))
        row.tap()
        after=page.evaluate('()=>({turn:G.turn,mp:G.p.mp,sat:G.p.sat})')
        assert after['turn']==before['turn']+1 and after['mp']>before['mp'] and after['sat']<before['sat']
        assert page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1')
        assert not errors,errors
        print('PASS Sage mobile',width,height,flush=True)
        page.close()
    browser.close()
