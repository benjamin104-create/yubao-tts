#!/usr/bin/env python3
"""美術資產與轉檔管線的檢查。

寫這一支的理由：第一批圖轉了四輪才對，而**每一輪的錯誤都不會報錯**——
綠皮膚的哥布林轉出來是棕色的、史萊姆下面多一塊白球、骷髏的頭差點被切掉。
檔案都寫出來了，尺寸都對，色盤也都合規，只有「看起來不對」。
這種東西不掃就是會漏，所以這裡把每一輪抓到的問題各留一條斷言。

  python3 tools/check_art.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image

from pixelize import (HERO_HEX, PALETTE_HEX, TILE, check_assets,
                      find_subjects, hex_to_rgb, nearest, pixelize,
                      strip_background)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# 已知偏暗、等著重畫的精靈。放這裡而不是把門檻調低：
# 調低門檻等於把問題藏起來，之後每一張太暗的圖都會安靜地通過。
# 這份名單應該越來越短，空了就把這段拿掉。
TOO_DARK = {"knight"}   # 深淵騎士：原圖的高光只有 1.8%，32px 裝不下
ART = os.path.join(ROOT, "web", "art")
RAW = os.path.join(ROOT, "art_raw")

fails = []
total = 0


def ok(cond, msg):
    global total
    total += 1
    if cond:
        print("  ✓ %s" % msg)
    else:
        print("  ✗ %s" % msg)
        fails.append(msg)


def hue_family(c):
    """把顏色歸到色盤的六個色群之一，用色相角判定。

    這樣寫而不是查色盤索引：斷言要說的是「綠的東西不可以配成棕的」，
    不是「一定要配到第 21 號」。後者會在色盤微調時假性紅燈。
    """
    r, g, b = [v / 255.0 for v in c]
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 0.10:
        return "灰"
    if mx == r:
        h = (60 * ((g - b) / (mx - mn))) % 360
    elif mx == g:
        h = 60 * (2 + (b - r) / (mx - mn))
    else:
        h = 60 * (4 + (r - g) / (mx - mn))
    if h < 20 or h >= 330:
        return "紅"
    if h < 45:
        return "棕橙"
    if h < 70:
        return "金"
    if h < 170:
        return "綠"
    return "藍"


print("色彩配對（Lab 最近鄰）")
# 每一組都是實際從第一批原圖裡抓出來的像素。前兩組是當初出事的那兩個 ——
# 哥布林的橄欖綠皮膚在 RGB 空間裡會以 0.4% 之差輸給淺棕。
for src, want, what in [
    ((137, 170, 77), "綠", "哥布林的橄欖綠皮膚"),
    ((106, 168, 79), "綠", "哥布林的亮面皮膚"),
    ((60, 140, 220), "藍", "史萊姆的藍"),
    ((230, 225, 205), "棕橙", "骷髏的骨白"),
    ((120, 80, 45), "棕橙", "老鼠的土棕"),
    ((200, 40, 40), "紅", "血紅"),
]:
    got = nearest(src)
    ok(hue_family(got) == want,
       "%s %s → %s（%s，期望 %s）" % (what, src, got, hue_family(got), want))

print("\n色盤本身")
pal = [hex_to_rgb(h) for h in PALETTE_HEX]
ok(len(set(pal)) == len(pal), "沒有重複的顏色")
ok(len(pal) <= 32, "不超過 32 色（實際 %d）" % len(pal))
for fam in ("綠", "藍", "棕橙", "紅"):
    n = sum(1 for c in pal if hue_family(c) == fam)
    # 每個色群至少要有三階，不然量化時同一個材質的亮暗面會被壓成同一色，
    # 立體感整個消失 —— 這不會報錯，只會變難看。
    ok(n >= 3, "%s 色群至少三階（實際 %d）" % (fam, n))

print("\n主體偵測")
sheets = [f for f in sorted(os.listdir(RAW)) if f.endswith(".png")] if os.path.isdir(RAW) else []
ok(bool(sheets), "art_raw/ 裡有原圖")
for name in sheets:
    im = strip_background(Image.open(os.path.join(RAW, name)))
    boxes = find_subjects(im)
    ok(len(boxes) >= 1, "%s 找得到主體（%d 個）" % (name, len(boxes)))
    W, H = im.size
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        frac = (x1 - x0) * (y1 - y0) / float(W * H)
        # 上限擋的是「兩個角色被併成一塊」，下限擋的是「把雜點當成角色」。
        ok(0.005 <= frac <= 0.45,
           "%s 第 %d 個主體佔比合理（%.1f%%）" % (name, i, frac * 100))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            hit = (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3])
            ok(not hit, "%s 第 %d 與第 %d 個主體不重疊" % (name, i, j))

    # 長寬比：轉檔前後必須一致。這條擋的是「直接拉伸成正方形」——
    # 趴著的老鼠原圖是 436x212，硬拉成 32x32 會變成一隻站起來的老鼠，
    # 而在這個尺寸下剪影是唯一可靠的辨識依據。
    # 檔案照樣寫得出來，色盤照樣合規，只有比例錯了。
    for i, box in enumerate(boxes):
        src_ar = (box[2] - box[0]) / float(box[3] - box[1])
        spr = pixelize(im.crop(box), TILE, keep_bg=True)
        bb = spr.getchannel("A").getbbox()
        out_ar = (bb[2] - bb[0]) / float(bb[3] - bb[1])
        ok(abs(out_ar - src_ar) / src_ar <= 0.18,
           "%s 第 %d 個主體長寬比沒跑掉（原圖 %.2f → 精靈 %.2f）"
           % (name, i, src_ar, out_ar))

print("\n提示詞清單與怪物／頭目表對得上")
# 之後加一隻新怪，很容易忘了同步提示詞文件 —— 那隻就會永遠沒有圖，
# 而且不會有任何東西提醒你：遊戲照跑，牠只是一直用程式畫的舊造型。
import re
_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()


def table_ids(marker, pat):
    i = _html.index(marker)
    return re.findall(pat, _html[i:_html.index("\n];", i)])


for what, marker, pat, doc_name, doc_pat in [
    ("怪", "const MONS = [", r"\{id:'([a-z_]+)',",
     "art_prompts_mon.md", r"`([a-z_]+)`"),
    ("頭目", "const BOSS = [", r"\{id:'([a-z_0-9]+)',",
     "art_prompts_boss.md", r"`(b_[a-z0-9_]+)`"),
]:
    want = set(table_ids(marker, pat))
    path = os.path.join(ROOT, "docs", doc_name)
    if not os.path.exists(path):
        ok(False, "docs/%s 存在" % doc_name)
        continue
    doc = open(path, encoding="utf-8").read()
    got = re.findall(doc_pat, doc.split("檔名對照")[1])
    ok(not (want - set(got)),
       "每隻%s都在提示詞文件裡（漏了：%s）" % (what, sorted(want - set(got)) or "無"))
    ok(not (set(got) - want),
       "%s的文件沒有列到不存在的（多了：%s）" % (what, sorted(set(got) - want) or "無"))
    dup = sorted({t for t in got if got.count(t) > 1})
    ok(not dup, "%s的文件裡沒有重複（重複：%s）" % (what, dup or "無"))

# 主角的兩份清單都不是 `const X = [`，所以走不進上面那個迴圈。
# 分開寫比把迴圈改複雜好 —— 那個迴圈的形狀就是「id 清單對提示詞」，
# 而主角是「體型清單 + 帽子清單」對同一份提示詞。
_hi = _html.index("const BLOB_SKINS = {")
_skins = re.findall(r"^  ([a-z]+): \[", _html[_hi:_html.index("\n};", _hi)], re.M)
_hats = table_ids("const HAT = [", r"\{id:'([a-z]+)'")
ok(len(_skins) > 1 and len(_hats) > 1, "讀得到體型與帽子清單（%d 體型、%d 帽子）"
   % (len(_skins), len(_hats)))
_hpath = os.path.join(ROOT, "docs", "art_prompts_hero.md")
if not os.path.exists(_hpath):
    ok(False, "docs/art_prompts_hero.md 存在")
else:
    _hdoc = open(_hpath, encoding="utf-8").read().split("檔名對照")[1]
    for _what, _want, _pat in [("體型", set(_skins), r"`hero/([a-z]+)`"),
                               ("帽子", set(_hats), r"`hat/([a-z]+)`")]:
        _got = re.findall(_pat, _hdoc)
        ok(not (_want - set(_got)), "每個%s都在主角提示詞文件裡（漏了：%s）"
           % (_what, sorted(_want - set(_got)) or "無"))
        ok(not (set(_got) - _want), "主角文件沒有列到不存在的%s（多了：%s）"
           % (_what, sorted(set(_got) - _want) or "無"))
        _dup = sorted({t for t in _got if _got.count(t) > 1})
        ok(not _dup, "主角文件裡的%s沒有重複（重複：%s）" % (_what, _dup or "無"))

# 換顏色的色階表：十種顏色一個都不能少，而且每一階都要在色盤裡。
# 少一種不會報錯 —— tintHero 回 null，那個顏色悄悄退回程式畫的舊主角。
_pal = dict(re.findall(r"'(.)':'(#[0-9a-f]{6})'",
                       _html[_html.index("const PAL = {"):_html.index("\n};", _html.index("const PAL = {"))]))
_cols = re.findall(r"'(.)'", _html[_html.index("const BLOB_COLS = ["):
                                   _html.index("];", _html.index("const BLOB_COLS = ["))])
_ri = _html.index("const BLOB_RAMP = {")
_ramp = dict((m.group(1), [m.group(2), m.group(3), m.group(4)]) for m in
             re.finditer(r"'(.)': \['(.)','(.)','(.)'\]", _html[_ri:_html.index("\n};", _ri)]))
ok(sorted(_ramp) == sorted(_cols),
   "十種可選顏色都有對應的色階（缺：%s）" % (sorted(set(_cols) - set(_ramp)) or "無"))
_bad = sorted(c for c in _ramp for s in _ramp[c] if s not in _pal)
ok(not _bad, "色階裡的每一階都在色盤裡（不在的：%s）" % (_bad or "無"))
# 十組色階必須互不相同 —— 相同的話，兩個選項在玩家眼裡是同一個顏色
_mid = [_ramp[c][1] for c in _ramp]
ok(len(set(_mid)) == len(_mid), "十種顏色的主色互不相同")

print("\n道具圖示的編號與遊戲對得上")
# 道具跟怪不一樣：檔名是**編號**不是 id，而編號直接對應遊戲裡的索引。
# 少一個、多一個、或跳號，圖示就會整批對錯道具 —— 而且不會報錯，
# 只是玩家看到的「赤紅的草」其實是別的東西的圖。
_look = {}
_i = _html.index("const LOOK = {")
for _m in re.finditer(r"(\w+):\[(.*?)\],?\n", _html[_i:_html.index("\n};", _i)] + "\n",
                      re.S):
    _look[_m.group(1)] = _m.group(2).count("'") // 2
_want = dict(_look)
# 帽子不在這裡：它跟主角是同一張圖（art/hat/<id>.png，檔名是 id 不是編號），
# 由上面那段主角的交叉檢查負責。留在這裡的話，這一支會去 art_prompts_item.md
# 找 hat00~hat08，而那九個檔案已經不存在了。
for _nm, _k in [("FOOD", "food"), ("WEAP", "weap"), ("SHLD", "shld")]:
    _a = re.search(r"const %s\s*=\s*\[" % _nm, _html).start()
    _want[_k] = len(re.findall(r"\{id:'[a-z_0-9]+',\s*nm:",
                               _html[_a:_html.index("\n];", _a)]))

_ipath = os.path.join(ROOT, "docs", "art_prompts_item.md")
if not os.path.exists(_ipath):
    ok(False, "docs/art_prompts_item.md 存在")
else:
    _idoc = open(_ipath, encoding="utf-8").read()
    _pairs = re.findall(r"`([a-z]+)(\d\d)`", _idoc.split("檔名對照")[1])
    _got = {}
    for _c, _n in _pairs:
        _got.setdefault(_c, []).append(int(_n))
    for _k in sorted(_want):
        _nums = sorted(_got.get(_k, []))
        # 一定要是 0..N-1 連續不重複 —— 只比個數的話，跳號會溜過去
        ok(_nums == list(range(_want[_k])),
           "%s 的編號是 0~%d 連續不重複（文件有 %d 個）"
           % (_k, _want[_k] - 1, len(_nums)))

print("\n轉檔成品")
if not os.path.isdir(ART):
    ok(False, "web/art/ 存在")
else:
    ok(check_assets(ART, TILE) == 0, "尺寸、色盤、透明度都合規")
    n = 0
    for dirpath, _, files in os.walk(ART):
        for name in sorted(files):
            if not name.endswith(".png"):
                continue
            n += 1
            rel = os.path.relpath(os.path.join(dirpath, name), ART)
            cat = rel.replace("\\", "/").split("/")[0]
            im = Image.open(os.path.join(dirpath, name)).convert("RGBA")
            px = list(im.getdata())
            cols = {p[:3] for p in px if p[3] > 0}
            solid = sum(1 for p in px if p[3] > 0)
            # 只有兩三色的精靈代表降取樣把東西吃掉了 —— 檔案照樣寫得出來
            if cat == "hero":
                # 主角的色盤只有五個色，其中亮面是一小塊高光，不是每種體型都有。
                # 拿「至少五色」去要求它，等於要求每一隻都畫出高光 ——
                # 那是把通用門檻套到一個色數本來就少的分類上。
                # 換成問真正要成立的三件事：外框在、主色在、至少有一階陰影。
                want = {"外框": hex_to_rgb(HERO_HEX[0]), "主色": hex_to_rgb(HERO_HEX[2])}
                for wn, wc in want.items():
                    ok(wc in cols, "%s 有%s（%s）" % (rel, wn, HERO_HEX[list(want).index(wn) * 2]))
                shade = {hex_to_rgb(HERO_HEX[1]), hex_to_rgb(HERO_HEX[3])} & cols
                ok(bool(shade), "%s 有明暗（暗面或亮面至少一階）" % rel)
            else:
                ok(len(cols) >= 5, "%s 至少五色（實際 %d）" % (rel, len(cols)))
            # 剪影佔比：太少代表主體沒框到，太多代表背景沒去掉。
            # 下限分類別：怪物與頭目一定是一團有體積的東西，佔不到 15% 就是
            # 沒框好；但**道具本來就有細長的**——長槍只佔 11%，那不是缺陷，
            # 那就是一把槍的樣子。原本的下限把「主體沒框到」跟「這東西本來就細」
            # 混為一談了。
            frac = solid / float(len(px))
            # 帽子跟道具一樣：它本來就只佔畫面上方那一條，
            # 用怪物的下限去要求，只會逼出一頂佔滿整格、把臉蓋掉的帽子。
            lo = 0.06 if cat in ("item", "hat") else 0.15
            ok(lo <= frac <= 0.92,
               "%s 剪影佔比合理（%.0f%%，下限 %.0f%%）" % (rel, frac * 100, lo * 100))
            # 主體必須碰到方框的最底下那一列。
            #
            # 轉檔工具如果把主體在方框裡上下置中，趴著的洞穴鼠就會在
            # 下方留四格空白 —— 牠因此不是站在地磚上，是站在格子中間一道
            # 看不見的台階上。使用者：「我不希望怪獸是懸浮在空中的感覺」。
            #
            # 為什麼這一條非要在這裡驗，不能靠 check_ground：
            # 遊戲那邊的影子會跟著精靈實際的腳走，所以圖畫歪了影子也跟著歪，
            # 兩者永遠貼在一起 —— check_ground 量的是「身體與影子的距離」，
            # 它看不到「這一組整個被抬高了」。一條斷言只看得到它量的東西。
            bot = im.getchannel("A").getbbox()
            if cat == "hat":
                # 帽子是**疊在頭上的一層**，不是站在地上的東西 ——
                # 它的方框跟身體的方框是同一個座標系，帽子畫在上緣、
                # 身體畫在下面。所以這裡問的正好相反：它有沒有乖乖待在頭頂那一段。
                #
                # 上限 16 是「上半格」，不是「不遮到眼睛」——
                # 後者沒辦法用一頂帽子自己的方框判斷，因為六種體型的眼睛
                # 高度各不相同。那一條在下面用**疊起來實際量**的方式驗。
                ok(bot is not None and bot[3] <= 16,
                   "%s 只佔上半格（最下緣在第 %s 列，上限 16）"
                   % (rel, bot[3] if bot else "—"))
                ok(bot is not None and (bot[2] - bot[0]) >= 12,
                   "%s 夠寬，戴得住（寬 %s，下限 12）"
                   % (rel, (bot[2] - bot[0]) if bot else "—"))
            else:
                ok(bot is not None and bot[3] == im.height,
                   "%s 主體貼齊底部（最下緣在第 %s 列，共 %d 列）"
                   % (rel, bot[3] if bot else "—", im.height))
            if cat == "hero":
                # 頭頂要落在第 4~9 列之間。六種體型共用同一組帽子圖，
                # 而帽子畫在固定的位置（drawHat 不做量測）——
                # 頭頂高了帽子會陷進頭裡，低了帽子會浮在半空。
                # 這是六張圖之間唯一**必須**對齊的一件事。
                ok(bot is not None and 4 <= bot[1] <= 9,
                   "%s 頭頂落在帽子接得上的高度（第 %s 列，要 4~9）"
                   % (rel, bot[1] if bot else "—"))

            # 每張精靈都要有一個真正被照亮的地方。
            #
            # 地牢的地板是暗的，整隻都是暗色的精靈會變成一個洞 ——
            # 玩家看得到「那裡有東西」，但讀不出是什麼、面向哪邊。
            # 風格規格寫的是「固定左上光源、右下留暗面」，兩半都要有；
            # 只有暗面等於只做了一半。
            #
            # 這一條抓得到的是**降取樣吃掉高光**：深淵騎士的原圖最亮到 236，
            # 但亮於 140 的像素只佔 1.8%（盔甲邊緣的細線），
            # 一個輸出格蓋住原圖 15x17 個像素，取眾數時細線永遠贏不了大片的暗甲，
            # 於是轉出來最亮只剩 118。那不是轉檔壞掉，是這個尺寸裝不下那種高光 ——
            # 要修得回頭讓圖有「一整塊」亮面，不是一條線。
            # 門檻同樣分類別。怪物要 140，因為玩家得在戰鬥中一眼把牠從暗地板上
            # 認出來，而牠腳下只有一道影子。
            # 道具站在遊戲畫的**金色光帶**上、旁邊還有名牌，而且不會動 ——
            # 條件寬得多。實測泛紫的草最亮只有 127，放到地上照樣讀得清楚。
            # 把兩者用同一個數字要求，等於逼所有深色的東西都要畫成亮的。
            name0 = os.path.splitext(os.path.basename(rel))[0]
            lum = [0.2126*p[0] + 0.7152*p[1] + 0.0722*p[2] for p in px if p[3] > 0]
            top = max(lum) if lum else 0
            need = 110 if cat in ("item", "hat") else 140
            if name0 in TOO_DARK:
                print("  · %s 已知偏暗（最亮 %.0f），等重畫" % (rel, top))
            else:
                ok(top >= need,
                   "%s 有被照亮的地方（最亮 %.0f，要 >= %d）" % (rel, top, need))
    ok(n > 0, "web/art/ 裡有檔案（%d 個）" % n)

    # 戴上帽子之後，眼睛還看得見嗎。
    #
    # 這一條非要**把兩張圖疊起來實際量**不可：帽子那張圖自己完全合規
    # （尺寸對、色盤對、待在上半格），身體那張也完全合規，
    # 只有疊起來才知道帽緣正好落在眼睛上。而眼睛是這個角色最重要的特徵 ——
    # 「看不到眼睛」在這款遊戲裡等於「這隻東西死了」。
    #
    # 實測就抓到一隻：旅人（biped）畫得比另外五種瘦一截，
    # 頭只有 12 格寬、眼睛又長在頭頂附近，九頂帽子有七頂把眼睛整個蓋掉。
    # 那張圖因此先不進遊戲，維持程式畫的版本 —— 跟怪物同一條規則。
    EYE = hex_to_rgb(HERO_HEX[-1])
    hero_dir, hat_dir = os.path.join(ART, "hero"), os.path.join(ART, "hat")
    if os.path.isdir(hero_dir) and os.path.isdir(hat_dir):
        hats = {}
        for f in sorted(os.listdir(hat_dir)):
            if f.endswith(".png"):
                hats[f[:-4]] = Image.open(os.path.join(hat_dir, f)).convert("RGBA")
        for f in sorted(os.listdir(hero_dir)):
            if not f.endswith(".png"):
                continue
            body = Image.open(os.path.join(hero_dir, f)).convert("RGBA")
            eyes = lambda im: sum(
                1 for y in range(im.height // 2 + 4) for x in range(im.width)
                if im.getpixel((x, y))[3] > 0 and im.getpixel((x, y))[:3] == EYE)
            bare = eyes(body)
            ok(bare >= 8, "hero/%s 有眼睛（眼白 %d 格，下限 8）" % (f[:-4], bare))
            for hn in sorted(hats):
                c = body.copy()
                c.alpha_composite(hats[hn])
                left = eyes(c)
                ok(left >= 6, "hero/%s 戴上 %s 之後眼睛還看得見（剩 %d 格，下限 6）"
                   % (f[:-4], hn, left))

print("\n%d 項檢查，%d 項失敗" % (total, len(fails)))
sys.exit(1 if fails else 0)
