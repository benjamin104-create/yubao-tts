#!/usr/bin/env python3
"""把兩套字型縮成遊戲真的用得到的那幾個字，內嵌進 index.html。

為什麼要自己做字型：
    使用者的原話是「字型選一下吧？感覺好醜」。原本的寫法是系統字型堆疊
    （PingFang / 微軟正黑 / Georgia），而系統 UI 字型的問題不是「難看」，
    是「沒有立場」—— 它讓一款 16-bit 地牢遊戲讀起來像一個設定頁面。

為什麼不能直接連 Google Fonts：
    這款遊戲的識別是「一個檔案，打開就能玩」，而且要能離線跑。
    連外部字型等於在最基本的那件事上加一個會壞掉的相依。
    所以字型必須內嵌，而內嵌就必須先縮到很小。

    Cinzel        羅馬碑刻體。標題、章節卡、英文副標本來就是加了字距的
                  大寫 —— 那正是碑刻體長出來的地方。可變字重，26 KB，
                  拉丁字母全收（玩家可以打英文名字）。
    Noto Serif TC 思源宋體。敘事用的中文：標題、章名、村名、訊息視窗。
                  完整的檔案是十幾 MB，所以只留遊戲真的會顯示的字。

    子集化之後**沒有涵蓋到的字仍然有救** —— @font-face 後面接的還是
    原本那套系統字型堆疊，玩家自己打的名字會落到 PingFang 上。
    少了那一層的話，取名叫「𩸽」的人會看到一個豆腐。

怎麼決定「遊戲真的會顯示的字」：
    掃的是**字串字面值與 HTML 文字**，不是整份原始碼 —— 這份檔案有大量
    中文註解，而註解玩家看不到。多收註解不會壞掉，只是白白多幾百個字，
    而每一個字在子集裡都是幾百個位元組。

    Google 的 CJK 字型是切成一百多片送的（每一片一段 unicode-range），
    而且 text= 參數對 CJK 無效。所以做法是：挑出跟我們的字有交集的切片、
    各自縮到只剩我們要的字、再合併成一份。

    python3 tools/build_font.py            # 重建 web/font/*.woff2
    python3 tools/build_font.py --check    # 只檢查現有的檔案還夠不夠用
"""

import base64
import io
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'web' / 'font'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')

# 這兩套都是 SIL Open Font License 1.1 —— 可以自由使用、修改、內嵌散布，
# 唯一的條件是不能單獨販售字型本身，而且衍生檔案要保留授權。
# 授權全文放在 web/font/OFL.txt，跟字型檔一起散布。
# rename = 內嵌之後對外用的名字。OFL 第 3 條規定「修改版不得沿用
# 保留字型名稱」，而**子集化就是修改**（思源系列的保留名稱是 Source）。
# 換個名字既是照規矩來，也順便避免跟使用者系統上真的裝了同名字型時打架。
FACES = {
    # 拉丁：碑刻體。可變字重 400~900，一個檔案涵蓋所有粗細。
    'cinzel': dict(family='Cinzel', axis='wght@400..900', latin_only=True,
                   rename='Babel Display'),
    # 中文與假名：思源宋體。只取 400 —— 粗體交給瀏覽器合成，
    # 兩個字重等於檔案大一倍，而遊戲裡真正需要粗中文的地方只有標題。
    'serif-tc': dict(family='Noto Serif TC', axis='wght@400', latin_only=False,
                     rename='Babel Serif'),
}


def fetch(url, binary=True, tries=5):
    """重試是必要的，不是保險：這一支要抓四十幾個切片，
    而中間任何一次斷線都會讓整份字型只做到一半 —— 而且做到一半的
    字型檔仍然寫得出來，只是少了幾百個字。"""
    import time
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            return data if binary else data.decode('utf-8')
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def wanted_chars():
    """玩家真的看得到的字。掃字串字面值與 HTML 文字，不掃註解。"""
    src = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
    head, script = src.split('<script>\n"use strict";', 1)
    script = script.rsplit('</script>', 1)[0]

    # 美術／音樂驗收頁（?qa=...）整段不算。跟 web/strings.js 同一條規矩：
    # 那是開發用的工具頁，只有帶 ?qa= 參數才進得去，玩家永遠看不到。
    # 把它的字算進來的話，字型會為了一個沒有玩家的畫面多內嵌三十個字 ——
    # 而其中「ⅠⅡⅢ」這種羅馬數字思源宋體根本沒有，於是檢查會永遠紅，
    # 紅得沒有道理（子集裡補不進一個來源字型就沒有的字）。
    a = script.find('/* ═══ 美術驗收入口（?qa=...）')
    b = script.find('/* ─── 啟動 ───', a + 1) if a >= 0 else -1
    if a >= 0 and b > a:
        script = script[:a] + script[b:]

    lit = ''.join(m.group(1) or m.group(2) or m.group(3) or '' for m in re.finditer(
        r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"|`((?:[^`\\]|\\.)*)`", script))
    body = re.sub(r'<style[\s\S]*?</style>', '', head)
    body = re.sub(r'<!--[\s\S]*?-->', '', body)
    attrs = ' '.join(re.findall(
        r'(?:placeholder|aria-label|data-lbl|title)="([^"]*)"', body))
    text = ' '.join(re.sub(r'<[^>]*>', ' ', body).split())

    # web/*.js 不掃。那幾支全部是測試（sim / campaign / story / music …），
    # 它們的字串是印到終端機的斷言訊息，一個字都不會到玩家眼前。
    # 掃了的話，每改一句測試訊息就要重建一次字型，而且子集裡會多出
    # 一堆只有機器人看得到的字 —— 每一個都是幾百個位元組。
    # （真的踩過：加了一條「側室夠多」的斷言，字型檢查就紅了。）
    all_text = lit + ' ' + attrs + ' ' + text
    # 一律附上完整的可見 ASCII：玩家會打英文名字，數字與標點到處都是
    ascii_ = ''.join(chr(c) for c in range(0x20, 0x7f))
    # 控制字元不是字。換行、tab 這些會從 HTML 的文字節點掃進來，
    # 而字型裡本來就沒有它們 —— 不濾掉的話檢查會永遠紅，而且紅得沒有道理。
    return {c for c in set(all_text) | set(ascii_) if ord(c) >= 0x20 and ord(c) != 0x7f}


def parse_css(css):
    """切出每一段 @font-face 的 (url, 這一片涵蓋哪些碼位)。"""
    out = []
    for blk in re.findall(r'@font-face\s*\{([^}]*)\}', css):
        u = re.search(r'src:\s*url\((\S+?)\)', blk)
        r = re.search(r'unicode-range:\s*([^;]+);', blk)
        if not u:
            continue
        cps = set()
        if r:
            for part in r.group(1).split(','):
                part = part.strip().replace('U+', '')
                if '-' in part:
                    a, b = part.split('-')
                    cps |= set(range(int(a, 16), int(b, 16) + 1))
                elif part:
                    cps.add(int(part, 16))
        out.append((u.group(1), cps))
    return out


def build(name, spec, want, verbose=True):
    from fontTools import merge, subset
    from fontTools.ttLib import TTFont

    url = ('https://fonts.googleapis.com/css2?family='
           + urllib.parse.quote(spec['family']) + ':' + spec['axis'] + '&display=swap')
    slices = parse_css(fetch(url, binary=False))
    if verbose:
        print('%s：%d 片' % (spec['family'], len(slices)))

    keep = [(u, cps) for u, cps in slices if not cps or (cps & set(map(ord, want)))]
    if verbose:
        print('  用得到 %d 片' % len(keep))

    parts, got = [], 0
    for i, (u, cps) in enumerate(keep):
        raw = fetch(u)
        got += len(raw)
        f = TTFont(io.BytesIO(raw))
        # 這一片只留「我們要的 ∩ 這一片有的」。先縮再合併，
        # 合併整片的話中間產物會是好幾 MB，而且字符名稱衝突的機會高得多。
        have = set()
        for t in f['cmap'].tables:
            have |= set(t.cmap.keys())
        take = have & set(map(ord, want))
        if not take:
            continue
        opt = subset.Options(layout_features=['*'], notdef_outline=True,
                             recalc_bounds=True, drop_tables=['DSIG'])
        s = subset.Subsetter(options=opt)
        s.populate(unicodes=take)
        s.subset(f)
        buf = io.BytesIO()
        f.save(buf)
        buf.seek(0)
        parts.append(TTFont(buf))
    if verbose:
        print('  下載 %.1f MB' % (got / 1e6))

    if not parts:
        raise SystemExit('%s：一片都沒挑到' % name)
    if len(parts) == 1:
        font = parts[0]
    else:
        tmp = OUT / '_tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, f in enumerate(parts):
            p = tmp / ('%s-%03d.ttf' % (name, i))
            f.save(p)
            paths.append(str(p))
        font = merge.Merger().merge(paths)
        for p in paths:
            pathlib.Path(p).unlink()
        tmp.rmdir()

    # 改名（OFL 第 3 條）。1/2 是家族名與樣式名，4 是完整名，6 是 PostScript 名，
    # 16/17 是排版家族／子family。全部一起換，只換其中一個的話，
    # 有些系統仍然會報出舊名字。
    ps = spec['rename'].replace(' ', '')
    for rec in font['name'].names:
        if rec.nameID in (1, 16):
            rec.string = spec['rename']
        elif rec.nameID in (2, 17):
            rec.string = 'Regular'
        elif rec.nameID == 4:
            rec.string = spec['rename'] + ' Regular'
        elif rec.nameID == 6:
            rec.string = ps + '-Regular'

    font.flavor = 'woff2'
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / (name + '.woff2')
    font.save(dst)
    n = len({c for t in TTFont(dst)['cmap'].tables for c in t.cmap})
    print('  → %s　%d 字　%.0f KB' % (dst.name, n, dst.stat().st_size / 1024))
    return dst


"""刻意交給系統字型的那幾個字 —— 它們**不是**漏掉的。

箭頭、✕、␣、≠、Ⓣ 這一類是介面符號，不是文字：碑刻體與宋體裡就算有，
畫出來也不會比系統的好看，而每一個都要多佔子集的位置。

残 / 満 是日文的新字體。這兩個字在繁體中文的思源宋體裡根本不存在
（正體是「殘」「滿」），而為了兩個字再內嵌一整套思源宋體日文版
要多兩百多 KB。讓它們落到系統字型上，只有日文介面的那兩個詞
會跟旁邊的字差一點點 —— 那個代價比兩百 KB 便宜太多。"""
SYSTEM_FALLBACK = (set('←↑→↓↔↖↗↘↙≠≡␣Ⓣ✕✗×·　ⅠⅡⅢ')
                   | set('残満戻数継続聴覚険剣壊巻薬静'))


def check(want):
    """現有的字型檔還夠不夠用。這一支是給 CI 跑的 ——
    加了新的中文訊息卻忘了重建字型，畫面上會冒出幾個豆腐，
    而那不會報錯、也不會有任何測試看得見。"""
    from fontTools.ttLib import TTFont
    bad = 0
    for name in FACES:
        p = OUT / (name + '.woff2')
        if not p.exists():
            print('✗ 缺少 %s' % p)
            bad += 1
            continue
        have = {c for t in TTFont(p)['cmap'].tables for c in t.cmap}
        need = {ord(c) for c in want if c not in SYSTEM_FALLBACK}
        if FACES[name]['latin_only']:
            # 碑刻體只負責拉丁字母與基本標點；中日文由另一套接手
            need = {c for c in need if c < 0x0250}
        miss = sorted(need - have)
        if miss:
            print('✗ %s 少了 %d 個字：%s'
                  % (p.name, len(miss), ''.join(chr(c) for c in miss)))
            bad += 1
        else:
            print('✓ %s　%d 字　%.0f KB' % (p.name, len(have), p.stat().st_size / 1024))
    return bad


if __name__ == '__main__':
    want = wanted_chars()
    print('遊戲會顯示的字元：%d 個' % len(want))
    if '--check' in sys.argv:
        sys.exit(1 if check(want) else 0)
    for name, spec in FACES.items():
        build(name, spec, want)
    print()
    sys.exit(1 if check(want) else 0)
