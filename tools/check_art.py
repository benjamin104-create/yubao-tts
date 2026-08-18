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

from pixelize import (PALETTE_HEX, TILE, build_palette_image, check_assets,
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
    pal = build_palette_image()
    for i, box in enumerate(boxes):
        src_ar = (box[2] - box[0]) / float(box[3] - box[1])
        spr = pixelize(im.crop(box), TILE, pal, keep_bg=True)
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
for _nm, _k in [("FOOD", "food"), ("WEAP", "weap"), ("SHLD", "shld"), ("HAT", "hat")]:
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
            im = Image.open(os.path.join(dirpath, name)).convert("RGBA")
            px = list(im.getdata())
            cols = {p[:3] for p in px if p[3] > 0}
            solid = sum(1 for p in px if p[3] > 0)
            # 只有兩三色的精靈代表降取樣把東西吃掉了 —— 檔案照樣寫得出來
            ok(len(cols) >= 5, "%s 至少五色（實際 %d）" % (rel, len(cols)))
            # 剪影佔比：太少代表主體沒框到，太多代表背景沒去掉
            frac = solid / float(len(px))
            ok(0.15 <= frac <= 0.92, "%s 剪影佔比合理（%.0f%%）" % (rel, frac * 100))
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
            ok(bot is not None and bot[3] == im.height,
               "%s 主體貼齊底部（最下緣在第 %s 列，共 %d 列）"
               % (rel, bot[3] if bot else "—", im.height))

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
            name0 = os.path.splitext(os.path.basename(rel))[0]
            lum = [0.2126*p[0] + 0.7152*p[1] + 0.0722*p[2] for p in px if p[3] > 0]
            top = max(lum) if lum else 0
            if name0 in TOO_DARK:
                print("  · %s 已知偏暗（最亮 %.0f），等重畫" % (rel, top))
            else:
                ok(top >= 140, "%s 有被照亮的地方（最亮 %.0f，要 >= 140）" % (rel, top))
    ok(n > 0, "web/art/ 裡有檔案（%d 個）" % n)

print("\n%d 項檢查，%d 項失敗" % (total, len(fails)))
sys.exit(1 if fails else 0)
