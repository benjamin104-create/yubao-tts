"""Exercise real town dialog actions, including their mobile hit targets."""
import pathlib
from playwright.sync_api import sync_playwright

URL = (pathlib.Path(__file__).resolve().parent.parent / 'web/index.html').as_uri()


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=['--allow-file-access-from-files'])
        try:
            for width, height in [(390, 844), (844, 390), (1200, 900)]:
                page = browser.new_page(viewport={'width': width, 'height': height}, has_touch=True)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(URL + '?qa=village&act=1')
                page.wait_for_function("()=>globalThis.RPG_TOWN?.state&&HD_LOADED['hd:town-healer']")
                # Freeze wandering only in the fixture so taps target the observed NPC.
                page.evaluate("""()=>{for(const n of RPG_TOWN.state.npcs){n.goal=null;n.next=999;}
                  VILLAGE.condition={hp:.4,mp:.25,sat:.3};}""")

                def speak(npc):
                    page.evaluate("""id=>{const n=RPG_TOWN.state.npcs.find(n=>n.id===id);
                      Object.assign(RPG_TOWN.state.p,{x:n.x,y:n.y+.6});}""", npc)
                    page.locator('#town-action').tap()
                    page.locator('#town-modal').wait_for(state='visible')
                    assert not errors, errors
                    rect = page.locator('#town-modal').bounding_box()
                    assert rect and rect['y'] >= 0 and rect['y'] + rect['height'] <= height + 1, rect

                speak('smith')
                assert page.locator('#town-modal #vstock').count() == 1
                page.keyboard.press('Escape')
                speak('innkeeper')
                page.locator('#town-modal-actions button').filter(has_text='住宿 ·').tap()
                assert page.evaluate('()=>VILLAGE.condition.hp') == 1
                page.keyboard.press('Escape')
                speak('healer')
                page.get_by_role('button', name='魔法調合與素材寄存', exact=True).tap()
                assert page.locator('.alchemy-recipes article').count() == 6
                page.keyboard.press('Escape')
                speak('child')
                page.get_by_role('button', name='幫忙找鈴鐺', exact=True).tap()
                assert page.evaluate('()=>VILLAGE.townQuest[villageStyle()]') == 1
                assert not errors, errors
                print(f'PASS {width}x{height}: shop, inn recovery, alchemy and town quest actions')
                page.close()
        finally:
            browser.close()


if __name__ == '__main__':
    main()
