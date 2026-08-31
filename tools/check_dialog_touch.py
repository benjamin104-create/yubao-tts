"""Exercise the real modal and hit-tested input, not just handler existence.

The dying samurai's long dialogue used to hide its choices while its backdrop
intercepted the gamepad A button. A wired handler alone did not catch this.
Run in CI with Playwright; no changes to a player's real saves.
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = (ROOT / 'web/index.html').as_uri() + '?qa=heian&seed=260829'
SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}
SIZES = [(360, 560, True), (390, 844, True), (1180, 820, True), (1280, 720, False)]
STATE = '() => ({x:G.p.x,y:G.p.y,turn:G.turn,hp:G.p.hp,accepted:G.heian.accepted})'


def reachable(page, selector):
    box = page.locator(selector).bounding_box()
    assert box and box['width'] > 0 and box['height'] > 0, selector
    hit = page.evaluate('''sel => {
      const e=document.querySelector(sel),r=e.getBoundingClientRect();
      const h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
      return !!h && (h===e || e.contains(h));
    }''', selector)
    assert hit, f'{selector} is covered or clipped'
    return box


def press(page, selector, touch):
    reachable(page, selector)
    if touch:
        page.locator(selector).tap(timeout=5000)
    else:
        page.locator(selector).click(timeout=5000)


def pages_to_choices(page, control, touch):
    initial = page.evaluate(STATE)
    assert not page.locator('#talkyes').is_visible(), 'expected a multi-page dialogue'
    before = page.locator('#talkbody').inner_text()
    press(page, control, touch)
    assert page.locator('#talkbody').inner_text() != before, 'input did not turn the page'
    for _ in range(8):
        assert page.locator('#talk').is_visible(), 'paging accidentally accepted the quest'
        assert page.evaluate(STATE) == initial, 'dialogue input advanced gameplay'
        if page.locator('#talkyes').is_visible():
            break
        press(page, control, touch)
    assert page.locator('#talkyes').is_visible(), 'could not reach choices'
    assert not page.locator('#talknext').is_visible(), 'continue can accidentally accept'
    reachable(page, '#talkyes')
    reachable(page, '#talkno')


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**LAUNCH)
        for width, height, touch in SIZES:
            ctx = browser.new_context(viewport={'width': width, 'height': height},
                                      has_touch=touch, is_mobile=touch, locale='zh-TW',
                                      device_scale_factor=3 if width < 600 else 2,
                                      reduced_motion='reduce')
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            for control, yes in [('#btnA', True), ('#talknext', False)]:
                page.goto(URL)
                page.locator('#talknext').wait_for(state='visible')
                nxt = reachable(page, '#talknext')
                assert nxt['height'] >= 48, 'touch target too small'
                reachable(page, '#btnA')
                reachable(page, '#btnB')
                arrow = page.locator('#talkmore').bounding_box()
                assert arrow and nxt['x'] <= arrow['x'] and nxt['y'] <= arrow['y']
                assert arrow['x']+arrow['width'] <= nxt['x']+nxt['width']
                assert arrow['y']+arrow['height'] <= nxt['y']+nxt['height']
                # A blocked direction must not walk or spend a turn while modal.
                initial = page.evaluate(STATE)
                cross = page.locator('#cross').bounding_box()
                page.mouse.click(cross['x']+cross['width']/2, cross['y']+cross['height']/2)
                assert page.evaluate(STATE) == initial
                pages_to_choices(page, control, touch)
                press(page, '#talkyes' if yes else '#talkno', touch)
                assert not page.locator('#talk').is_visible()
                assert page.evaluate('() => !!G.heian.accepted') == yes
                assert page.evaluate('() => !!G.f.heianGate') == yes
                assert page.evaluate('() => G.turn') == initial['turn'], 'click leaked to ground'
            # B must also be reachable and reject, without moving or opening inventory.
            page.goto(URL)
            press(page, '#btnB', touch)
            assert not page.locator('#talk').is_visible()
            assert not page.evaluate('() => G.heian.accepted')
            assert not page.evaluate('() => panelMode')
            if not touch:
                page.goto(URL)
                before = page.locator('#talkbody').inner_text()
                page.keyboard.press('Enter')
                assert page.locator('#talkbody').inner_text() != before
                page.keyboard.press('Escape')
                assert not page.locator('#talk').is_visible()
            assert not errors, errors
            print(f'PASS {width}x{height}: A, continue, choices, B, triangle, no gameplay leak')
            ctx.close()
        # Without reduced motion, the first tap reveals this page, not the next one.
        ctx = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True,
                                  is_mobile=True, locale='zh-TW', reduced_motion='no-preference')
        page = ctx.new_page()
        page.goto(URL)
        page.locator('#talknext').wait_for(state='visible')
        page.locator('#talkbody').wait_for(state='visible')
        initial_page = page.evaluate('() => talkPage')
        if page.evaluate('() => talkTyping'):
            press(page, '#talknext', True)
            assert page.evaluate('() => talkPage') == initial_page
            assert not page.evaluate('() => talkTyping')
        ctx.close()
        browser.close()
    print('Dialogue touch regression passed.')


if __name__ == '__main__':
    main()
