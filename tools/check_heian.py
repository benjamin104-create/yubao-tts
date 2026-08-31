"""Real-browser regression for the Heian sidequest, on isolated QA saves.

Unlike merely checking PNGs on disk, this exercises delayed art replacement
through the lighting/flash caches and real hit-tested mobile reward controls.
Quest/combat state permutations live in web/heian.js.
"""
import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from check_dialog_touch import LAUNCH, press

ROOT = Path(__file__).resolve().parent.parent
BOSSES = ['b_genmaan', 'b_musashimaru', 'b_doll_heal', 'b_doll_mage',
          'b_doll_tank', 'samurai_spirit']


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    handler = functools.partial(QuietHandler, directory=str(ROOT / 'web'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/?qa=heian&seed=260829'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**LAUNCH)
            # Force the exact bug: draw a placeholder before its real PNG loads.
            ctx = browser.new_context(viewport={'width': 390, 'height': 844})
            page = ctx.new_page()
            page.route('**/art/boss/b_genmaan.png*', lambda r: r.abort())
            page.goto(base + '&stage=1')
            page.wait_for_function('() => G && G.heian.active')
            page.evaluate('''() => {
              const id='b_genmaan', old=atlas[id];
              characterLiftOf(old,id); whiteOf(old,id+'@lit');
              footOf(old,id); auraOf(old,id);
            }''')
            assert page.evaluate("() => characterLiftOf(atlas.b_genmaan,'b_genmaan').width") < 48
            page.unroute('**/art/boss/b_genmaan.png*')
            page.evaluate("() => adoptArt('b_genmaan',ART_DIR+'boss/b_genmaan.png',true)")
            page.wait_for_function('() => ownArt.b_genmaan && atlas.b_genmaan.width===48')
            sizes = page.evaluate('''() => {
              const lit=characterLiftOf(atlas.b_genmaan,'b_genmaan');
              return [lit.width,whiteOf(lit,'b_genmaan@lit').width];
            }''')
            assert sizes == [48, 48], f'stale fallback cache survived: {sizes}'
            ctx.close()
            print('PASS delayed PNG replaces both lighting and hurt-flash fallback caches')

            for width, height, touch in [(360, 560, True), (390, 844, True), (1180, 820, True), (1280, 720, False)]:
                ctx = browser.new_context(viewport={'width': width, 'height': height},
                                          has_touch=touch, is_mobile=width < 600,
                                          device_scale_factor=3 if width < 600 else 2,
                                          locale='zh-TW', reduced_motion='reduce')
                page = ctx.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(base + '&stage=3')
                page.wait_for_function('''ids => ids.every(id=>ownArt[id] && atlas[id].width===48)
                  && atlas['weap#9'] && atlas['weap#9'].width===32''', arg=BOSSES)
                assert '異界三殿' in page.locator('#zone').inner_text()
                assert page.evaluate('() => G.mons.length') == 3
                assert page.evaluate('''() => G.mons.every(m=>
                  characterLiftOf(atlas[m.d.id],m.d.id).width===48)''')
                assert not page.locator('#tags').get_by_text('下樓', exact=True).count()
                # All required controls must survive portrait / landscape layouts.
                for selector in ['#btnA', '#btnB', '#cross button[aria-label="上"]',
                                 '#cross button[aria-label="下"]']:
                    from check_dialog_touch import reachable
                    reachable(page, selector)
                page.goto(base + '&stage=4')
                page.wait_for_function('() => G && G.heian.stage===4 && G.f.muramasaDrop')
                before_storage = page.evaluate('() => JSON.stringify(localStorage)')
                assert not page.locator('#btnR').is_visible()
                press(page, '#cross button[aria-label="右"]', touch)
                page.wait_for_function('() => G.p.weap && G.p.weap.d.muramasa')
                page.wait_for_function('() => !G.anim.length && !G.levelFx')
                assert page.locator('#btnR').is_visible()
                hp = page.evaluate('() => G.p.hp')
                press(page, '#btnR', touch)
                press(page, '#cross button[aria-label="左"]', touch)
                page.wait_for_function(f'() => G.p.hp < {hp}')
                page.wait_for_function('() => !G.anim.length && !G.p.lunge')
                # Return through the actual door, not a test-only stage switch.
                for _ in range(2):
                    press(page, '#cross button[aria-label="右"]', touch)
                    page.wait_for_function('() => !G.anim.length && !G.p.lunge')
                page.wait_for_function('() => !G.heian.active && G.heian.completed')
                assert page.evaluate('() => G.floor') == 2
                assert page.evaluate('() => G.p.weap.d.id') == 'muramasa'
                assert page.evaluate('() => JSON.stringify(localStorage)') == before_storage
                assert not errors, errors
                print(f'PASS {width}x{height}: 48px bosses, touch reward, distant slash, return, QA save isolation')
                ctx.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
