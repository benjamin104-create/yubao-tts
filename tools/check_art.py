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
        # 下限擋的是「把雜點當成角色」，上限擋的是「兩個角色被併成一塊」。
        #
        # 上限要分兩種情況。45% 是給**多角色的一張大圖**用的：那種圖上
        # 一個角色不可能佔到快一半，佔到就是併框了。但整張圖只框到
        # **一個**主體時，那多半就是一張單角色的圖 —— 它本來就會填滿畫面
        # （實測有一張 1254x1254 的單角色圖，主體佔 66.7%）。
        # 對這種圖，「有沒有併框」要改用**長寬比**問：兩個角色並排併成一塊
        # 會變成又扁又寬（大約 2:1 以上），單一個角色不會。
        # 面積上限仍然留著，只是放到 0.90 —— 那一條擋的是另一件事：
        # 背景沒去乾淨，整張圖被當成主體。
        if len(boxes) > 1:
            ok(0.005 <= frac <= 0.45,
               "%s 第 %d 個主體佔比合理（%.1f%%）" % (name, i, frac * 100))
        else:
            ar = (x1 - x0) / float(y1 - y0)
            ok(0.005 <= frac <= 0.90,
               "%s 唯一的主體佔比合理（%.1f%%，單角色圖上限 90%%）"
               % (name, frac * 100))
            ok(0.35 <= ar <= 2.2,
               "%s 唯一的主體不是兩個併成一塊（長寬比 %.2f，要 0.35~2.2）"
               % (name, ar))
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
# 有些類別「所有外觀共用同一張圖」（卷軸：十一個名字、一張圖）——
# 那種只會有 00 一個檔案，照 LOOK 的個數去要求會逼出十一張一模一樣的圖。
_one = dict(re.findall(r"(\w+): (\d+)",
                       _html[_html.index("const ART_ONE = {"):
                             _html.index("};", _html.index("const ART_ONE = {"))]))
_ii = _html.index("const ART_ITEM = {")
_item = dict(re.findall(r"(\w+): (\d+)", _html[_ii:_html.index("};", _ii)]))
ok(not (set(_one) & set(_item)),
   "ART_ONE 與 ART_ITEM 沒有重疊（重疊的：%s）" % (sorted(set(_one) & set(_item)) or "無"))
for _k in _one:
    _want[_k] = 1
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

SIDES = {}
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
            parts = rel.replace("\\", "/").split("/")
            # 動畫圖集是三層：anim/<類別>/<id>.png。只取第一段的話，
            # **每一張圖集的類別都會變成 "anim"** —— 於是底下那些
            # 「帽子要待在上半格」「武器要待在右半邊」的規則一條都跑不到，
            # 全部掉進最後那個 else，被當成一隻站在地上的怪來驗。
            # 症狀就是：九張帽子圖集全部報「主體沒有貼齊底部」，
            # 而帽子本來就**不該**貼齊底部 —— 它戴在頭上。
            # 規則本身沒錯，是分不出來這張圖是什麼東西。
            is_sheet = parts[0] == "anim"
            cat = parts[1] if is_sheet and len(parts) >= 3 else parts[0]
            is_tile_blocker = (not is_sheet and cat == "tile" and
                               parts[-1].startswith("blocker"))
            # 海報、村莊全景、旅程地圖不是精靈，是**整張畫**。
            # 它們的工作就是填滿畫面，用精靈的規則去驗會把每一張刻意的
            # 全景都判成「背景沒去乾淨」。
            # 地板、走道與牆面也必須填滿整張：透明背景或外圍留白反而會在
            # 重複鋪設時露出接縫。blocker* 則相反 —— 它是疊在地板上的
            # 獨立障礙物，規格要求透明背景、四周留白與落地接觸陰影。
            # chapter-charcoal-hero 是疊在十八張炭筆全景上的透明角色層，
            # 不是另一張全景。它刻意只佔畫面中央偏下，若要求 92% 覆蓋率，
            # 反而會逼它帶著不透明背景，破壞序章的分層動畫。
            is_scene_overlay = (cat == "promo" and
                                parts[-1].startswith("chapter-charcoal-hero-"))
            is_scene = ((cat in ("promo", "village", "map") and not is_scene_overlay) or
                        (cat == "tile" and not is_tile_blocker))
            im = Image.open(os.path.join(dirpath, name)).convert("RGBA")
            px = list(im.getdata())
            cols = {p[:3] for p in px if p[3] > 0}
            solid = sum(1 for p in px if p[3] > 0)
            # 只有兩三色的精靈代表降取樣把東西吃掉了 —— 檔案照樣寫得出來
            if cat == "hero":
                # 48px 預設主角保留八階陶土；舊的 32px fallback 可以只用其中
                # 三階，所以驗「必要色＋至少一階明暗」，不強迫 fallback 灌滿十色。
                want = {"外框": hex_to_rgb(HERO_HEX[0]),
                        "主色": hex_to_rgb("d97757")}
                for wn, wc in want.items():
                    ok(wc in cols, "%s 有%s" % (rel, wn))
                shade = {hex_to_rgb(h) for h in HERO_HEX[1:-1] if h != "d97757"} & cols
                ok(bool(shade), "%s 有明暗（暗面或亮面至少一階）" % rel)
            elif cat == "tile":
                # 地磚的色階品質由 check_tile.py 直接量「明度階數與跨度」。
                # 這裡原本沿用精靈的「至少五色」，會把刻意只有 2~4 色、
                # 低明度的虛空與鏡廳判壞；增加無意義的顏色反而會製造噪點。
                ok(len(cols) >= 2, "%s 至少有底色與明暗層次（實際 %d 色）" % (rel, len(cols)))
            else:
                ok(len(cols) >= 5, "%s 至少五色（實際 %d）" % (rel, len(cols)))
            # ── 幾何：一律**逐格**量 ──────────────────────────────
            # 動畫圖集是 10 欄 x 3 列的 30 格，而下面每一條門檻
            #（帽子只佔上半格、主體貼齊底部）寫的都是**一格**的座標。
            # 拿整張圖集的 bbox 去比，等於問「這三十格裡有沒有任何一格
            # 碰到最下面」—— 三十格裡有一格對就過，那條斷言等於沒有。
            # 逐格量之後同一條門檻反而變嚴，而且才問得出真正的問題。
            CELL_OF = {"boss": 48, "hero": 48}
            # 非圖集就是**整張一格**，而且格子要用整張的長寬 ——
            # 只拿寬度當邊長的話，寬扁的海報會算出 height//c == 0，
            # 一格都切不出來，然後報「這張圖是空的」。
            c = (CELL_OF.get(cat, 32) if is_sheet else im.width)
            cw, ch = (c, c) if is_sheet else (im.width, im.height)
            boxes = []          # 每個非空格子的 (欄, 列, bbox, 填充率)
            for _r in range(max(1, im.height // ch)):
                for _k in range(max(1, im.width // cw)):
                    _cell = im.crop((_k * cw, _r * ch, _k * cw + cw, _r * ch + ch))
                    _bb = _cell.getchannel("A").getbbox()
                    if not _bb:
                        continue          # 空格子：圖集不一定塞滿三十格
                    _fill = sum(1 for q in _cell.getdata() if q[3] > 0) / float(cw * ch)
                    boxes.append((_k, _r, _bb, _fill))
            ok(bool(boxes), "%s 不是空的" % rel)
            if not boxes:
                continue

            # 剪影佔比：太少代表主體沒框到，太多代表背景沒去掉。
            # 量的是**最飽滿的那一格**，不是平均 —— 攻擊的蓄力格本來就縮成
            # 一團，拿三十格的平均去比，等於用最瘦的姿勢去判「有沒有框到」。
            # 下限分類別：怪物與頭目是一團有體積的東西；但**細長的東西不是缺陷**
            #（長槍只佔 7%，那就是一把槍的樣子；針尾蜂 14%，那就是一隻蜂）。
            frac = max(b[3] for b in boxes)
            # 散落石片、骨堆等 blocker 可以是刻意疏鬆的障礙物；它的工作
            # 是在透明格內留下清楚輪廓，不必填到怪物精靈的 12%。
            lo = 0.05 if is_tile_blocker else \
                 (0.06 if cat in ("item", "hat", "weapon", "shield") else 0.12)
            if is_scene:
                ok(frac >= 0.92,
                   "%s 全景覆蓋畫面（%.0f%%，下限 92%%）" % (rel, frac * 100))
            else:
                ok(lo <= frac <= 0.92,
                   "%s 剪影佔比合理（最飽滿的一格 %.0f%%，下限 %.0f%%）"
                   % (rel, frac * 100, lo * 100))
            # 「有沒有框到」真正該問的是**跨度**，不是填充率 ——
            # 一把槍很細但橫跨整格，一張沒框好的圖則是縮在角落的一小塊。
            # 實測：所有怪最瘦的一隻仍跨 81%、頭目 88%，所以 60% 是安全的下限，
            # 而它抓得到「主體只佔一個角落」這種轉檔失敗。
            if cat in ("mon", "boss", "hero"):
                span = max(max((b[2][2]-b[2][0])/float(cw), (b[2][3]-b[2][1])/float(ch)) for b in boxes)
                ok(span >= 0.60,
                   "%s 主體有框到（最大跨度 %.0f%% 格寬，下限 60%%）" % (rel, span * 100))

            # 主體必須碰到**自己那一格**的最底下那一列。
            #
            # 轉檔工具如果把主體在方框裡上下置中，趴著的洞穴鼠就會在
            # 下方留四格空白 —— 牠因此不是站在地磚上，是站在格子中間一道
            # 看不見的台階上。使用者：「我不希望怪獸是懸浮在空中的感覺」。
            #
            # 為什麼這一條非要在這裡驗，不能靠 check_ground：
            # 遊戲那邊的影子會跟著精靈實際的腳走，所以圖畫歪了影子也跟著歪，
            # 兩者永遠貼在一起 —— check_ground 量的是「身體與影子的距離」，
            # 它看不到「這一組整個被抬高了」。一條斷言只看得到它量的東西。
            if is_tile_blocker:
                # blocker 是一格裡的獨立立體物，不該像角色那樣把腳貼到圖片
                # 最下列；底部要保留少量透明空間，讓接觸陰影完整留在格內。
                # 但它也不能被放在格子中央漂浮：陰影下緣必須進入底部 12%。
                for _k, _r, bb, _fill in boxes:
                    x0, y0, x1, y1 = bb
                    ok(x0 > 0 and y0 > 0 and x1 < cw and y1 < ch,
                       "%s 障礙物四周都有透明留白（bbox %s，畫布 %dx%d）"
                       % (rel, bb, cw, ch))
                    center = (x0 + x1) / 2.0
                    ok(abs(center - cw / 2.0) <= cw * 0.08,
                       "%s 障礙物水平置中（中心 %.1f，畫布中心 %.1f）"
                       % (rel, center, cw / 2.0))
                    gap = ch - y1
                    # 障礙物的接觸陰影已包含在 alpha bbox 裡。64px 的立體物
                    # 為了不在 32px 地磚上顯得塞滿，允許下方最多留四分之一格；
                    # 超過才視為被整組抬高。舊的 12% 是角色「腳貼地」規則的
                    # 延伸，會誤判有完整接觸陰影、但刻意置中的石堆與骨堆。
                    ok(gap <= ch * 0.26,
                       "%s 接觸陰影靠近格底、沒有漂浮（底部留白 %dpx，上限 %.1fpx）"
                       % (rel, gap, ch * 0.26))
            elif cat == "hat":
                # 帽子是**疊在頭上的一層**，不是站在地上的東西 ——
                # 它的方框跟身體的方框是同一個座標系，帽子畫在上緣、
                # 身體畫在下面。所以這裡問的正好相反：它有沒有待在頭那一段。
                #
                # 兩個門檻分開寫，因為它們防的是兩件不同的事：
                #   上緣要靠近格子頂　→ 帽子沒有整頂往下掉
                #   下緣不可以到底　　→ 帽子沒有被轉檔工具當成「站在地上的東西」
                #                       而貼齊底部（那正是這一支原本誤報的那條）
                # 為什麼不是「只佔上半格」：實測頭盔、頭巾、鬼面兜的下緣到
                # 第 25~28 列 —— 它們本來就包到臉頰。用 16 去卡會逼出一頂
                # 只蓋住頭頂一小片的帽子。單張的靜態帽子仍然用 16（實測 14~16）。
                topmax = max(b[2][1] for b in boxes)
                botmax = max(b[2][3] for b in boxes)
                hat_bot = int(c * 0.90) if is_sheet else 16
                ok(topmax <= c * 0.32,
                   "%s 從頭頂開始（最低的上緣在第 %d 列，上限 %d）"
                   % (rel, topmax, int(c * 0.32)))
                ok(botmax <= hat_bot,
                   "%s 沒有掉到腳邊（最下緣在第 %d 列，上限 %d）"
                   % (rel, botmax, hat_bot))
                ok(max(b[2][2] - b[2][0] for b in boxes) >= 12,
                   "%s 夠寬，戴得住（寬 %s，下限 12）"
                   % (rel, max(b[2][2] - b[2][0] for b in boxes)))
            elif cat in ("weapon", "shield"):
                # 武器與盾也是**疊在角色身上的一層**，「貼齊底部」對它們
                # 沒有意義。原本驗的是「武器在右、盾在左」——
                # 那條在動畫圖集上是錯的，而且錯在兩個地方：
                #   1. 揮擊的那幾格本來就會橫過中線，那正是動畫的用途
                #   2. 動畫圖集第 0 列是**正面朝向鏡頭**，角色的右手在觀眾的
                #      左邊 —— 所以圖集的慣例跟單張的正好相反（實測：
                #      圖集的武器在 x 1~13、盾在 x 15~32）
                # 真正該成立的是：**待機格裡兩者分別在相反的半邊**（中間那一條
                # 留給臉），而且同一類的每一件都站在同一側。哪一側由資產自己
                # 決定，不由這支檢查規定 —— 規定側別只會把某一批的慣例寫死。
                idle = [b for b in boxes if b[0] == 0 and b[1] == 0] or boxes[:1]
                bb = idle[0][2]
                mid = (bb[0] + bb[2]) / 2.0
                SIDES.setdefault(cat, []).append((rel, mid < c / 2.0, bb))
                ok(bb[2] - bb[0] <= c * 0.62,
                   "%s 待機時不會橫跨整格（寬 %d，上限 %d）"
                   % (rel, bb[2] - bb[0], int(c * 0.62)))
            else:
                # 容許 1px —— 那**正是動畫規格要求的東西**：
                # 欄 1「待機 B：只做 1px 呼吸」、欄 3「行走 2：身體下降 1px」、
                # 欄 5「行走 4：身體回升 1px」。實測三張新的頭目圖集，
                # 沒貼底的格子全部剛好差 1px，而且全部落在那幾欄上，
                # check_ground 量到的實際著地距離是 0.5 邏輯單位（合格）。
                # 要求「每一格都貼死」等於禁止角色呼吸。
                #
                # 但仍然要抓「整組被抬高」（那是這條規則本來要防的：
                # 趴著的洞穴鼠浮在自己的影子上方四格）——
                # 所以另外要求**至少有一格真的貼到底**。
                bad = [b for b in boxes if b[2][3] < ch - 1]
                ok(not bad,
                   "%s 每一格都貼齊底部（容許 1px 呼吸；%d/%d 格差太多，格高 %d）"
                   % (rel, len(bad), len(boxes), ch))
                ok(any(b[2][3] == ch for b in boxes),
                   "%s 至少有一格真的貼到底（不然就是整組被抬高了）" % rel)
            if cat == "hero":
                # 頭頂要落在第 4~9 列之間。六種體型共用同一組帽子圖，
                # 而帽子畫在固定的位置（drawHat 不做量測）——
                # 頭頂高了帽子會陷進頭裡，低了帽子會浮在半空。
                # 這是六張圖之間唯一**必須**對齊的一件事。
                #
                # 48px 動畫圖集放寬到 6~18：實測新版三十格是 15~17
                #（走路與受擊本來就會讓身體上下浮一兩格，那是動畫該有的）。
                # 用單張的 4~9 去卡，等於要求走路時頭不准動。
                # 「戴上去會不會對齊」那一條由下面**疊起來實際量**的檢查負責，
                # 那才是真正要成立的事；這裡只擋「整組畫得太高或太低」。
                lo_top, hi = ((6, 18) if is_sheet else (4, 9))
                tops = [b[2][1] for b in boxes]
                ok(lo_top <= min(tops) and max(tops) <= hi,
                   "%s 頭頂落在帽子接得上的高度（第 %d~%d 列，要 %d~%d）"
                   % (rel, min(tops), max(tops), lo_top, hi))

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
            lum = [0.2126*p[0] + 0.7152*p[1] + 0.0722*p[2] for p in px if p[3] > 0]
            top = max(lum) if lum else 0
            if cat == "tile":
                # 地形提示詞明確要求整體維持 40~70 的低明度，亮色只准做
                # 1~2px 細線；拿角色的「至少亮到 140」來驗，會逼得地板比
                # 主角更亮。地形是否有光影改由 check_tile.py 的階數與跨度驗。
                ok(bool(lum), "%s 有可見的地形像素" % rel)
            else:
                need = 110 if cat in ("item", "hat", "weapon", "shield") else 140
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
    hero_dir = os.path.join(ART, "hero")
    if os.path.isdir(hero_dir):
        # 三層都要疊起來量：帽子、武器、盾。
        # 每一層自己都合規，只有疊起來才知道它正好落在眼睛上。
        hats = {}
        for d in ("hat", "weapon", "shield"):
            dd = os.path.join(ART, d)
            if not os.path.isdir(dd):
                continue
            for f in sorted(os.listdir(dd)):
                if f.endswith(".png"):
                    hats[d + "/" + f[:-4]] = Image.open(os.path.join(dd, f)).convert("RGBA")
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
                ok(left >= 6, "hero/%s 疊上 %s 之後眼睛還看得見（剩 %d 格，下限 6）"
                   % (f[:-4], hn, left))

# ── 武器與盾必須在相反的兩側，而且同類要一致 ────────────────────
# 側別本身不由這支檢查規定：單張的靜態圖與動作表的慣例是**相反的**
#（動作表第 0 列是正面朝鏡頭，角色的右手在觀眾的左邊），
# 硬性規定哪一側只會把其中一批的慣例寫死。
# 真正必須成立的是兩件事，而且兩件都會直接影響畫面：
#   1. 同一類的每一件都在同一側 —— 有一把劍畫反了，換武器時它會跳到另一邊
#   2. 武器與盾在相反側 —— 同一側的話兩層會疊在一起，中間那條臉就沒了
for _grp, _rows in sorted(SIDES.items()):
    if not _rows:
        continue
    _l = [r for r in _rows if r[1]]
    ok(not _l or len(_l) == len(_rows),
       "%s 每一件都在同一側（靠左 %d／靠右 %d）"
       % (_grp, len(_l), len(_rows) - len(_l)))
if "weapon" in SIDES and "shield" in SIDES and SIDES["weapon"] and SIDES["shield"]:
    _w = SIDES["weapon"][0][1]
    _s = SIDES["shield"][0][1]
    ok(_w != _s, "武器與盾在相反的兩側（武器靠%s、盾靠%s）"
       % ("左" if _w else "右", "左" if _s else "右"))

print("\n%d 項檢查，%d 項失敗" % (total, len(fails)))
sys.exit(1 if fails else 0)
