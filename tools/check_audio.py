"""音量檢查：音樂真的聽得到嗎，音效穿得過音樂嗎。

為什麼需要這一支：使用者回報「網頁版好像沒有音樂」，而查下去發現
**音樂一直都在播** —— AudioContext 是 running、振盪器持續產生、
曲目也對。壞的地方是音量：實測 RMS 只有 -40.4 dBFS，
而一般遊戲音樂在 -18 ~ -14。低了 20 dB 就等於十分之一的音量，
技術上完全正常，人耳聽起來就是「沒有音樂」。

這一類失敗沒有任何既有測試抓得到：web/music.js 驗的是**曲子的資料**
（音符落在小節內、鼓組編排不重複），驗不到「放出來有多大聲」。
所以要真的把它播出來，用 AnalyserNode 量。

量三件事：
  1. 音樂的 RMS 落在合理範圍 —— 太小聽不到，太大會蓋掉音效
  2. 尖峰沒有貼到 0 dBFS —— 貼到就是爆音
  3. 音效的尖峰高過音樂的 RMS —— 打擊聲要穿得過音樂床，不能被埋掉

外加一條回歸測試：靜音開關按兩次之後，音量要回到原來的值。
（那裡本來把音量寫死成 .5，跟總音量的設定各一份 ——
  總音量一改，玩家按過一次靜音，音量就永遠停在舊值。）

    python3 tools/check_audio.py
"""
from playwright.sync_api import sync_playwright
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = (ROOT / 'web' / 'index.html').as_uri()

SANDBOX = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
LAUNCH = {'executable_path': SANDBOX} if os.path.exists(SANDBOX) else {}

# 音樂的合理範圍。下限是「聽得到」，上限是「不會把音效蓋掉」。
MUSIC_RMS_MIN, MUSIC_RMS_MAX = -30.0, -14.0
PEAK_CEILING = -1.0          # 貼到 0 dBFS 就是爆音
# roar/fell 是頭目登場與倒下的兩記 —— 它們是整套裡最該被聽見的，
# 而且是新加的，最容易發生「加了但根本沒聲音」而沒有人發現。
SFX_CHECK = ['hit', 'crit', 'level', 'shatter', 'roar', 'fell']

# 掛一個分析節點在總線上，量一段時間的尖峰與 RMS
METER = """(ms)=>new Promise(done=>{
  const c = SFX.ctx();
  if(!c) { done(null); return; }
  const an = c.createAnalyser(); an.fftSize = 2048;
  SFX.bus().connect(an);
  const buf = new Float32Array(an.fftSize);
  let peak = 0, sum = 0, n = 0;
  const t0 = performance.now();
  const tick = ()=>{
    an.getFloatTimeDomainData(buf);
    for(let i=0;i<buf.length;i++){ const v = Math.abs(buf[i]); if(v > peak) peak = v; sum += v*v; n++; }
    if(performance.now() - t0 < ms) requestAnimationFrame(tick);
    else {
      an.disconnect();
      const db = x => +(20*Math.log10(x || 1e-9)).toFixed(1);
      done({peak: db(peak), rms: db(Math.sqrt(sum/n))});
    }
  };
  requestAnimationFrame(tick);
})"""

SFX_PEAK = """(name)=>new Promise(done=>{
  const c = SFX.ctx();
  const an = c.createAnalyser(); an.fftSize = 2048;
  SFX.bus().connect(an);
  const buf = new Float32Array(an.fftSize);
  let peak = 0;
  SFX.play(name);
  const t0 = performance.now();
  const tick = ()=>{
    an.getFloatTimeDomainData(buf);
    for(const v of buf) if(Math.abs(v) > peak) peak = Math.abs(v);
    if(performance.now() - t0 < 400) requestAnimationFrame(tick);
    else { an.disconnect(); done(+(20*Math.log10(peak || 1e-9)).toFixed(1)); }
  };
  requestAnimationFrame(tick);
})"""


def main():
    bad = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch(**LAUNCH)
        pg = b.new_page(viewport={'width': 1280, 'height': 720})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(HTML)
        pg.wait_for_timeout(400)
        pg.click('#start')          # 這一下就是瀏覽器要求的使用者手勢
        pg.wait_for_timeout(2200)   # 等淡入跑完

        state = pg.evaluate("()=>({ctx: SFX.ctx() ? SFX.ctx().state : null,"
                            " running: BGM.running, track: BGM.track})")
        print('音訊狀態　context %s　BGM %s　曲目 %s'
              % (state['ctx'], state['running'], state['track']))
        if state['ctx'] != 'running' or not state['running']:
            print('✗ 音樂根本沒有在跑')
            return 1

        m = pg.evaluate(METER, 4000)
        ok_rms = MUSIC_RMS_MIN <= m['rms'] <= MUSIC_RMS_MAX
        ok_peak = m['peak'] <= PEAK_CEILING
        print('%s 音樂　RMS %s dBFS（要在 %s ~ %s）'
              % ('✓' if ok_rms else '✗', m['rms'], MUSIC_RMS_MIN, MUSIC_RMS_MAX))
        print('%s 音樂　尖峰 %s dBFS（不得超過 %s）'
              % ('✓' if ok_peak else '✗', m['peak'], PEAK_CEILING))
        if not ok_rms:
            print('     太小聲就等於沒有音樂，太大聲會把音效蓋掉')
            bad += 1
        if not ok_peak:
            bad += 1

        # 音效要穿得過音樂床
        pg.evaluate("()=>BGM.stop()")
        pg.wait_for_timeout(300)
        for nm in SFX_CHECK:
            db = pg.evaluate(SFX_PEAK, nm)
            ok = db > m['rms']
            print('%s 音效 %-8s 尖峰 %s dBFS（要高過音樂的 RMS %s）'
                  % ('✓' if ok else '✗', nm, db, m['rms']))
            if not ok:
                bad += 1

        # 靜音開關按兩次要回到原值
        vol0 = pg.evaluate("()=>SFX.bus().gain.value")
        pg.evaluate("()=>SFX.toggle()")
        vmute = pg.evaluate("()=>SFX.bus().gain.value")
        pg.evaluate("()=>SFX.toggle()")
        vol1 = pg.evaluate("()=>SFX.bus().gain.value")
        ok = (vmute == 0) and abs(vol1 - vol0) < 1e-6
        print('%s 靜音開關　%s → %s → %s（按兩次要回到原值）'
              % ('✓' if ok else '✗', vol0, vmute, vol1))
        if not ok:
            print('     音量被寫死在兩個地方了 —— 總音量一改就會對不起來')
            bad += 1

        if errs:
            print('! 執行期錯誤 %s' % errs[:2])
            bad += 1
        b.close()
    print()
    print('全部通過' if not bad else '有 %d 項不合格' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
