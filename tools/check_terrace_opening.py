"""Real mobile interactions for the terrace and the grounded opening composition."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get('GAME_URL', (ROOT/'web/index.html').as_uri())
OUT = ROOT/'work/rpg-v23'
OUT.mkdir(parents=True, exist_ok=True)


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=['--allow-file-access-from-files'])
        try:
            for width,height in [(390,844),(360,640),(844,390),(1200,900)]:
                page=browser.new_page(viewport={'width':width,'height':height},has_touch=True)
                errors=[]
                page.on('pageerror',lambda e: errors.append(str(e)))
                def bounds(selector):
                    r=page.locator(selector).bounding_box()
                    assert r and r['x']>=-1 and r['y']>=-1 and r['x']+r['width']<=width+1 and r['y']+r['height']<=height+1,(selector,r)
                page.goto(BASE)
                page.wait_for_function("()=>HD_LOADED['hd:hero-back']&&globalThis.RPG_COVER")
                page.locator('#start').tap()
                page.locator('#propause').tap()
                for _ in range(3):page.locator('#pronext').tap()
                page.wait_for_function("()=>document.getElementById('prologuevisual').classList.contains('scene-3')")
                page.wait_for_timeout(400)
                for s in ['#prologuevisual','#prologuebox','#pronext','#proskip','#chapterhero']:bounds(s)
                assert page.locator('#prologuetitle').inner_text()=='門後的腳步'
                assert page.evaluate("""()=>document.getElementById('chapterhero').style.backgroundImage.includes(
                    hdHeroSprite(-1,-1,null,VILLAGE.skin,VILLAGE.col,[0,-1]).toDataURL('image/png'))""")
                stage=page.locator('#prologuevisual').bounding_box();caption=page.locator('#prologuebox').bounding_box()
                assert stage['y']+stage['height']<=caption['y']+1 or stage['x']+stage['width']<=caption['x']+1
                page.screenshot(path=str(OUT/f'opening-{width}.png'))
                page.goto(BASE.split('?')[0]+'?qa=floor&act=tower&seed=81291')
                page.wait_for_function("()=>RPG_BALCONY.door&&HD_LOADED['hd:town-stele']&&HD_LOADED['hd:terrace']")
                page.evaluate("""()=>{G.mons=[];G.p.hp=1;G.p.mp=0;const d=RPG_BALCONY.door;G.p.x=d.x;G.p.y=d.y+1;}""")
                initial=page.evaluate('()=>({x:G.p.x,y:G.p.y,turn:G.turn,pressure:G.f.elapsedTurns||0})')
                page.keyboard.press('ArrowUp')
                page.locator('#tower-terrace').wait_for(state='visible')
                page.wait_for_function('()=>RPG_BALCONY.state.view?.bw>0')
                for s in ['#terrace-return','#terrace-canvas','#terrace-message','#terrace-action','#terrace-stick']:bounds(s)
                assert page.locator('[data-terrace]').count()==0
                # Real touch movement: diagonal steering, release and cancellation.
                cdp=page.context.new_cdp_session(page)
                stick=page.locator('#terrace-stick').bounding_box()
                cx,cy=stick['x']+stick['width']/2,stick['y']+stick['height']/2
                before_move=page.evaluate('()=>({...RPG_BALCONY.state.p})')
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':cx,'y':cy,'id':1}]})
                cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':cx+24,'y':cy+24,'id':1}]})
                page.wait_for_timeout(350)
                moving=page.evaluate('()=>({...RPG_BALCONY.state.p})')
                assert moving['x']>before_move['x']+.15 and moving['y']>before_move['y']+.15
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                stopped=page.evaluate('()=>({...RPG_BALCONY.state.p})')
                page.wait_for_timeout(250)
                assert page.evaluate('()=>({...RPG_BALCONY.state.p})')==stopped
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':cx+28,'y':cy,'id':1}]})
                page.wait_for_timeout(100)
                cdp.send('Input.dispatchTouchEvent',{'type':'touchCancel','touchPoints':[]})
                stopped=page.evaluate('()=>({...RPG_BALCONY.state.p})')
                page.wait_for_timeout(150)
                assert page.evaluate('()=>({...RPG_BALCONY.state.p})')==stopped
                assert 'active' not in (page.locator('#terrace-stick').get_attribute('class') or '')
                cdp.detach()
                def approach(x,y):
                    box=page.locator('#terrace-canvas').bounding_box()
                    v=page.evaluate('()=>RPG_BALCONY.state.view')
                    page.touchscreen.tap(box['x']+v['ox']+v['bw']*(.14+(x-2)*.075),box['y']+v['oy']+v['bh']*(.57+(y-4)*.09)-4)
                    page.wait_for_function('q=>Math.hypot(RPG_BALCONY.state.p.x-q[0],RPG_BALCONY.state.p.y-q[1])<.9',arg=[x,y])
                    page.wait_for_timeout(300)
                approach(3.9,5.55)
                page.locator('#terrace-action').tap()
                assert '預覽模式' in page.locator('#terrace-message').inner_text()
                approach(6.3,5.45)
                page.locator('#terrace-action').tap()
                assert page.evaluate('()=>G.p.hp')>1
                hp=page.evaluate('()=>G.p.hp')
                page.locator('#terrace-action').tap()
                assert page.evaluate('()=>G.p.hp')==hp
                approach(9,5.1)
                page.wait_for_function('()=>RPG_BALCONY.state.revealed')
                before=page.evaluate('()=>G.p.inv.length')
                page.locator('#terrace-action').tap()
                assert page.evaluate('()=>G.p.inv.length')==before+1
                assert '獲得：' in page.locator('#terrace-message').inner_text()
                page.locator('#terrace-action').tap()
                assert page.evaluate('()=>G.p.inv.length')==before+1
                page.screenshot(path=str(OUT/f'terrace-{width}.png'))
                assert page.evaluate('()=>({x:G.p.x,y:G.p.y,turn:G.turn,pressure:G.f.elapsedTurns||0})')==initial
                page.locator('#terrace-return').tap()
                page.locator('#tower-terrace').wait_for(state='hidden')
                page.keyboard.press('ArrowUp')
                assert page.evaluate('()=>terraceState().rested&&terraceState().claimed')
                assert not errors,errors
                page.close()
                print(f'PASS {width}x{height}: unarmed opening, joystick drag/release/cancel, discoveries, save, limited rest, no turn leak')
        finally:browser.close()

if __name__=='__main__':main()
