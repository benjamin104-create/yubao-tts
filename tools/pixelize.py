#!/usr/bin/env python3
"""
把 AI 生成的圖轉成真正可用的像素美術。

為什麼需要這一步：影像模型不會產出 32x32 的圖。你要 32x32 像素風，
它會給你一張 1024x1024、「看起來像」像素風但每個「像素」其實是 32x32 一團、
邊緣還帶抗鋸齒與雜色的圖。直接丟進遊戲會糊掉，而且每張圖的色調都不一樣。

這支工具做四件事：
  1. 去背     —— 四角取樣，把背景轉成透明
  2. 找主體   —— 在 sheet 上自動框出每個角色（--auto）
  3. 降取樣   —— 先量化再取眾數，保住平塗與外框
  4. 統一調色 —— 全部量化到同一組固定色盤

第 4 步是讓不同批次生成的圖看起來像同一款遊戲的關鍵。

用法：
    # 一張 sheet 自動切成 N 張（推薦，不必是整齊的網格）
    python3 tools/pixelize.py sheet.png --auto \\
        --out-dir web/art/mon --prefix m --start 0

    # 單張
    python3 tools/pixelize.py in.png -o web/art/mon/m00.png

    # 檢查既有資產是否合規
    python3 tools/pixelize.py --check web/art
"""

import argparse
import os
import sys

from PIL import Image, ImageChops

TILE = 32

# 各分類的尺寸。頭目在遊戲裡放大 1.6 倍顯示（16 x 1.6 = 25.6 邏輯單位，
# 在 2 倍算圖下是 51 個真實像素），所以 48 最接近 1:1；照 32 畫會被拉糊。
SIZES = {"mon": 32, "boss": 48}

# 32 色固定色盤。所有資產都量化到這裡 —— 這是把不同批次的生成結果
# 綁成同一種視覺語言最有效的手段，比在提示詞裡描述顏色可靠得多。
PALETTE_HEX = [
    # 石材 / 灰階
    "0d0d12", "1a1a24", "2b2b38", "3d3d4d", "565668", "757589", "c8c8d4",
    # 泥土 / 木頭 / 地板
    "2a1d14", "43301f", "5e442c", "7d5c3c", "9c7850", "bb9668", "ecd3ae",
    # 血 / 火 / 敵意
    "6b1a1e", "9c2b2b", "c94a3a", "e87a4a", "f5a95e",
    # 綠 / 毒 / 自然
    "1e5230", "2f7d45", "4aa85e", "79c97a",
    # 藍 / 魔法 / 冰
    "101c3a", "1d3468", "2f57a0", "4a86cf", "7cb8ea",
    # 金 / 高光
    "6b4a12", "a87a1e", "dcae35", "f5dc7a",
]


# 主角的身體只准用這五個色：描邊、三階陶土、眼白。
#
# 為什麼要另外開一組，而不是併進上面那 32 色：主角有十種顏色可選，
# 而換顏色是**色階置換**（遊戲裡的 BLOB_RAMP）—— 只有這三階陶土會被換掉。
# 身體上多出來的任何一個顏色都換不到，於是玩家選了苔綠，
# 身上還是會留幾塊陶土色。多一個色不會報錯，只會讓九種顏色都髒掉。
#
# 反過來也要成立：這四個陶土色**不在**通用色盤裡，所以怪物與道具
# 永遠不會被量化成主角的顏色 —— 整張地牢裡只有主角是這個色調。
HERO_HEX = ["0d0d12", "a8452c", "d97757", "eaa88c", "f2efe7"]
# 分類 → 專用色盤。沒列到的用上面那 32 色。
PALETTES = {"hero": HERO_HEX}


def hex_to_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def palette_hex_for(rel):
    """這個檔案該用哪一組色盤，看它放在哪個資料夾。"""
    return PALETTES.get(rel.replace("\\", "/").split("/")[0], PALETTE_HEX)


PALETTE_RGB = tuple(hex_to_rgb(h) for h in PALETTE_HEX)


def palette_rgb_for(name):
    """分類名 → 那一組色盤的 RGB。名字對不上就用通用的。"""
    return tuple(hex_to_rgb(h) for h in (PALETTES.get(name) or PALETTE_HEX))
_NEAR_CACHE = {}
_LAB_CACHE = {}


def to_lab(c):
    """sRGB → CIELAB。配色一定要在感知空間裡比，不能在 RGB 裡比。

    加權 RGB 距離看起來很合理，但實測會出這種事：
    橄欖綠的皮膚 (137,170,77) 到色盤裡「亮綠 (74,168,94)」的距離是 8821，
    到「淺棕 (187,150,104)」是 8787 —— 棕色以 34 之差勝出，
    於是綠皮膚的哥布林變成棕色的。差 0.4% 的數字，換來的是**換了一個色相**。
    在 Lab 裡，色相的差距會被算進 a/b 兩軸，這種事就不會發生。
    """
    hit = _LAB_CACHE.get(c)
    if hit is not None:
        return hit
    r, g, b = [v / 255.0 for v in c]
    f = lambda u: u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722)
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    t = lambda u: u ** (1 / 3) if u > 0.008856 else (7.787 * u + 16 / 116)
    fx, fy, fz = t(x), t(y), t(z)
    lab = (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))
    _LAB_CACHE[c] = lab
    return lab


def nearest(c, pal=None):
    """把一個顏色配到色盤裡最近的那一個。

    pal：要配到哪一組色盤（RGB 三元組的序列）。主角的身體只准用五個色，
    所以它走的是另一組 —— 沒有這個參數的話，量化永遠配到通用色盤，
    而 --palette 這個旗標會變成「設了也沒用」的裝飾。

    為什麼要自己寫，不用 PIL 的 quantize(palette=)：**它會配錯**。
    實測 (137,170,77) 這個綠色被它配成 (156,120,80) 的棕色，
    而隔壁的 (138,176,82) 卻正確配到綠色 —— 差一階就翻到完全不同的色相。
    症狀是「綠皮膚的哥布林變成棕色的」，看起來像色盤裡沒有綠色，
    其實色盤裡有四階綠。PIL 用的是近似查表，不是真的最近鄰。

    距離在 CIELAB 裡用 CIE76 算（理由見 to_lab）。RGB 空間的距離
    —— 不管有沒有加權 —— 都會在深綠與深棕之間翻車。
    """
    pal = tuple(pal) if pal else PALETTE_RGB
    hit = _NEAR_CACHE.get((c, pal))
    if hit is not None:
        return hit
    L1, a1, b1 = to_lab(c)
    best, bd = pal[0], None
    for p in pal:
        L2, a2, b2 = to_lab(p)
        d = (L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2
        if bd is None or d < bd:
            bd, best = d, p
    _NEAR_CACHE[(c, pal)] = best
    return best


def strip_background(im, tolerance=18):
    """把背景轉成透明。四角取樣決定背景色，但**只挖從外面連得進來的**。

    用四角取樣而非固定色鍵，才不會在背景色換了一批之後整個失效。

    「只挖從外面連得進來的」這一條是踩過才加的：主角的眼白是 #f2efe7，
    離純白只有 13 —— 在容差之內。於是六種體型的眼睛全部被挖成洞，
    轉出來的主角沒有眼睛。而檔案照樣寫得出來、尺寸色盤全部合規。
    同樣的事會發生在任何有白色斑塊的東西上（骨頭、牙齒、雲、雪）。

    只看顏色是分不出「背景」與「主體上剛好同色的一塊」的 ——
    分得出來的只有**連通性**：背景一定接到畫面邊緣，眼白一定不會。

    連通元件在 1/4 縮圖上做（跟 find_subjects 同一個理由：全解析度是
    一百多萬個像素，純 Python 會慢到不能用）。精度不足只會讓「洞」
    的還原範圍多蓋到幾格主體 —— 而主體本來就是不透明的，蓋到也沒事。
    """
    im = im.convert("RGBA")
    w, h = im.size
    corners = [im.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    r = sum(c[0] for c in corners) // 4
    g = sum(c[1] for c in corners) // 4
    b = sum(c[2] for c in corners) // 4

    px = im.load()
    for y in range(h):
        for x in range(w):
            cr, cg, cb, ca = px[x, y]
            if abs(cr - r) <= tolerance and abs(cg - g) <= tolerance \
                    and abs(cb - b) <= tolerance:
                px[x, y] = (cr, cg, cb, 0)

    # 把「挖出來卻連不到畫面邊緣」的區塊還原 —— 那些不是背景，是主體的一部分
    S = 4
    sw, sh = max(1, w // S), max(1, h // S)
    small = im.getchannel("A").resize((sw, sh), Image.BOX).load()
    seen = [[False] * sw for _ in range(sh)]
    holes = Image.new("L", (sw, sh), 0)
    hp = holes.load()
    found = False
    for sy in range(sh):
        for sx in range(sw):
            if seen[sy][sx] or small[sx, sy] >= 64:
                continue
            cells, stack, edge = [], [(sx, sy)], False
            seen[sy][sx] = True
            while stack:
                cx, cy = stack.pop()
                cells.append((cx, cy))
                if cx == 0 or cy == 0 or cx == sw - 1 or cy == sh - 1:
                    edge = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < sw and 0 <= ny < sh and not seen[ny][nx] \
                            and small[nx, ny] < 64:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if edge:
                continue                      # 連到邊緣 —— 這才是真的背景
            found = True
            for cx, cy in cells:
                hp[cx, cy] = 255
    if found:
        im.putalpha(ImageChops.lighter(im.getchannel("A"),
                                       holes.resize(im.size, Image.NEAREST)))
    return im


def trim_to_subject(im, margin=1, headroom=0.0, band=0.0, pad=0.0, zone=None):
    """裁到主體的外框，再補成正方形，**主體靠下對齊**。

    為什麼一定要這一步：模型輸出的每一格都有大量留白，主體常常只佔六成。
    不裁就降取樣的話，32x32 裡真正畫到角色的只剩十七、八格，
    而且邊緣像素會把白背景平均進來 —— 實測綠皮膚的哥布林量化完是**棕色**的。
    看起來像「色盤沒有綠色」，其實是主體太小、平均進了背景。

    補成正方形而不是直接拉伸：拉伸會把瘦高的角色壓扁，
    而剪影是這個尺寸下唯一可靠的辨識依據。

    垂直靠下、水平置中，不是兩軸都置中。**這是踩過才知道的：**
    俯視角遊戲的每張精靈底下都有一道影子，影子畫在格子底部。
    兩軸都置中的話，趴著的洞穴鼠（436x212，補完上下各多四格空白）
    就會浮在自己的影子上方四個邏輯單位 —— 使用者的原話是
    「我不希望怪獸是懸浮在空中的感覺」。高瘦的角色看不出來（它們本來就填滿），
    所以這個 bug 只會出現在一部分角色身上，更難察覺。
    靠下對齊之後，「精靈的最後一列」就是「腳踩的那一條線」。

    headroom：頭頂上面要留多少比例的空白（主角用 6/32）。
    主角的六種體型共用同一組帽子圖，而帽子畫在固定的位置 ——
    所以六種體型的頭頂必須落在同一列。填滿整格的話頭頂在第 0 列，
    帽子就會整頂跑到畫面外。留白是這裡唯一能保證的東西：
    要求模型畫的時候對齊某一條線是做不到的，裁的時候留出來才做得到。

    band：**改成靠上對齊**，而且主體最多只佔這個比例的高度（帽子用）。
    帽子不是站在地上的東西，是疊在頭上的一層 —— 它的方框跟身體共用
    同一個座標系，所以它要待在上面那一段，下面留給臉。
    靠下對齊的帽子會整頂蓋住臉，而檔案照樣寫得出來。

    zone=(左, 上, 寬, 高)：把主體縮到方框裡的這一塊，並在那一塊裡置中。
    穿在身上的武器與盾用這個 —— 武器握在右手（右邊那一條），
    盾立在左手前面（左邊偏下那一塊）。

    為什麼不是「叫模型畫在正確的位置」：做不到。跟帽子那次的結論一樣，
    位置只能在裁切的時候決定。模型只要把東西畫正、畫清楚就好。

    zone 與 band 的差別只在垂直對齊：band 是靠上（帽子要頂著頭），
    zone 是在那一塊裡置中（武器與盾要對準手）。兩條規則都有東西在用，
    合成一個就會有一邊變成特例。
    """
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - margin); y0 = max(0, y0 - margin)
    x1 = min(im.width, x1 + margin); y1 = min(im.height, y1 + margin)
    cut = im.crop((x0, y0, x1, y1))
    side = max(cut.width, cut.height)
    if zone:
        zl, zt, zw, zh = zone
        side = max(1, int(round(max(cut.width / zw, cut.height / zh))))
        sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sq.paste(cut, (int(round(zl * side + (zw * side - cut.width) / 2)),
                       int(round(zt * side + (zh * side - cut.height) / 2))))
        return sq
    if band > 0:
        side = max(cut.width, int(round(cut.height / band)))
        sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sq.paste(cut, ((side - cut.width) // 2, 0))
        return sq
    if headroom > 0:
        side = max(side, int(round(cut.height / (1.0 - headroom))))
    # pad：左右與上面留一點空隙，下緣不動（下緣是腳踩的那一條線）。
    # 方形的東西（木之盾）裁完會剛好塞滿整格 —— 在格子鋪成的畫面上，
    # 塞滿整格的東西讀起來是「一塊地磚」，不是「一個掉在地上的道具」。
    if pad > 0:
        side = int(round(side * (1.0 + pad)))
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(cut, ((side - cut.width) // 2, side - cut.height))
    return sq


def pixelize(im, size, palette=None, keep_bg=False, trim=True, headroom=0.0,
             band=0.0, pad=0.0, zone=None):
    if not keep_bg:
        im = strip_background(im)
    im = im.convert("RGBA")
    if trim:
        im = trim_to_subject(im, headroom=headroom, band=band, pad=pad, zone=zone)

    """降取樣的順序很重要，這裡是「先量化、再取眾數」而不是「先平均、再量化」。

    先平均的話：一格輸出蓋住原圖 26x26 個像素，綠皮膚會跟深色外框、
    棕色腰布平均在一起，結果是一團濁色 —— 實測綠哥布林量化完是**棕色**的，
    而色盤裡明明有四階綠。那不是色盤的問題，是平均把顏色吃掉了。

    先量化再取眾數：每一格輸出取「原圖那一塊裡出現最多次的色盤顏色」。
    平塗區塊因此原封不動地留下來，外框也不會糊掉 ——
    這才是像素美術該有的降取樣方式。
    """
    src = im.convert("RGB").load()
    a_full = im.getchannel("A").load()
    W, H = im.size
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dst = out.load()
    for oy in range(size):
        y0, y1 = oy * H // size, max(oy * H // size + 1, (oy + 1) * H // size)
        for ox in range(size):
            x0, x1 = ox * W // size, max(ox * W // size + 1, (ox + 1) * W // size)
            tally, opaque, total = {}, 0, 0
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    total += 1
                    if a_full[xx, yy] < 128:
                        continue
                    opaque += 1
                    c = nearest(src[xx, yy], palette)
                    tally[c] = tally.get(c, 0) + 1
            # 這一格有一半以上是背景就當透明 —— 不然剪影會被外框撐胖一圈
            if not tally or opaque * 2 < total:
                continue
            best = max(tally.items(), key=lambda kv: kv[1])[0]
            dst[ox, oy] = (best[0], best[1], best[2], 255)
    return out


def find_subjects(im, min_frac=0.0015, gap=12):
    """在一張 sheet 上自動找出每個角色，回傳依閱讀順序排好的外框。

    為什麼不用 --grid 硬切：**模型不會照著網格畫**。實測那張 2x2 的圖，
    史萊姆的下緣壓過水平中線、骷髏的頭蓋骨正好從中線開始 ——
    硬切的結果是史萊姆下面多一塊不明的白球、骷髏的頭被切掉一半。
    而且這件事每一批都會重來一次，因為它取決於模型當下怎麼排版。

    做法是對透明遮罩做連通元件標記，再把「靠得夠近」的元件併起來
    （劍尖、飄起來的布料常常會因為抗鋸齒而斷開成獨立的一塊）。
    標記在 1/4 縮圖上做 —— 全解析度是 150 萬個像素，純 Python 會慢到不能用，
    而我們只需要外框，不需要每個像素的歸屬。
    """
    S = 4
    w, h = im.width // S, im.height // S
    mask = im.getchannel("A").resize((w, h), Image.BOX).load()
    lab = [[0] * w for _ in range(h)]
    boxes = []
    for sy in range(h):
        for sx in range(w):
            if mask[sx, sy] < 64 or lab[sy][sx]:
                continue
            n = len(boxes) + 1
            x0 = x1 = sx; y0 = y1 = sy; area = 0
            stack = [(sx, sy)]
            lab[sy][sx] = n
            while stack:
                cx, cy = stack.pop()
                area += 1
                if cx < x0: x0 = cx
                if cx > x1: x1 = cx
                if cy < y0: y0 = cy
                if cy > y1: y1 = cy
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and not lab[ny][nx] \
                            and mask[nx, ny] >= 64:
                        lab[ny][nx] = n
                        stack.append((nx, ny))
            boxes.append([x0, y0, x1, y1, area])

    # 併掉離得近的碎片（劍尖、耳朵、飄起的布）
    #
    # **只併小碎片，不併兩個大塊。** 光看距離會出事：第三批那張 sheet 裡，
    # 苔背熊的蕈菇與幻光蝶的翅尖相距不到 48px，於是兩隻被併成一個 948px 寬的
    # 「角色」—— 轉出來是一張同時有熊和蝶的圖，而且數量從 6 變成 5，
    # 後面照順序命名的東西全部錯位。
    # 「碎片」的定義是面積明顯小於鄰居：劍尖、耳朵、飄起的布都是這樣，
    # 而兩隻怪不會。距離只是必要條件，大小才是判準。
    FRAG = 0.25
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                near = (a[0] - gap <= b[2] and b[0] - gap <= a[2]
                        and a[1] - gap <= b[3] and b[1] - gap <= a[3])
                if not near:
                    continue
                overlap = (a[0] <= b[2] and b[0] <= a[2]
                           and a[1] <= b[3] and b[1] <= a[3])
                small = min(a[4], b[4]) <= FRAG * max(a[4], b[4])
                if not (overlap or small):
                    continue
                boxes[i] = [min(a[0], b[0]), min(a[1], b[1]),
                            max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4]]
                boxes.pop(j)
                merged = True
                break
            if merged:
                break

    # 濾掉雜點：面積不到整張圖 0.15% 的當作雜訊
    floor = w * h * min_frac
    boxes = [b for b in boxes if b[4] >= floor]

    # 閱讀順序：先分列（同一列的縱向中心相差不到半個列高），列內再由左至右
    boxes.sort(key=lambda b: b[1])
    rows, cur = [], []
    for b in boxes:
        if cur and b[1] > max(c[3] for c in cur):
            rows.append(cur); cur = []
        cur.append(b)
    if cur:
        rows.append(cur)
    out = []
    for r in rows:
        for b in sorted(r, key=lambda b: b[0]):
            out.append((b[0] * S, b[1] * S, (b[2] + 1) * S, (b[3] + 1) * S))
    return out


def split_grid(im, cols, rows):
    w, h = im.size
    cw, ch = w // cols, h // rows
    for r in range(rows):
        for c in range(cols):
            yield im.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))


def size_for(rel, default):
    """這個檔案該是幾像素見方，看它放在哪個資料夾。

    頭目畫得比雜魚大（遊戲裡放大 1.6 倍顯示），照 32 檢查會全部報錯，
    照「最大的那個尺寸」檢查則等於放掉雜魚。尺寸是分類的屬性，不是全域常數。
    """
    top = rel.replace("\\", "/").split("/")[0]
    return SIZES.get(top, default)


def check_assets(root, size):
    problems = 0
    checked = 0
    for dirpath, _, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith(".png"):
                continue
            path = os.path.join(dirpath, name)
            im = Image.open(path).convert("RGBA")
            checked += 1
            w, h = im.size
            rel = os.path.relpath(path, root)
            want = size_for(rel, size)

            if h != want or w % want != 0:
                print("  [尺寸] %s 是 %dx%d，應為 %d 的倍數 x %d"
                      % (rel, w, h, want, want))
                problems += 1

            # 色盤也是分類的屬性：主角的身體只准用那五個色，
            # 因為換顏色是色階置換，換不到的顏色會在九種顏色裡留成髒塊。
            palette = {hex_to_rgb(h) for h in palette_hex_for(rel)}
            off = {c[:3] for c in im.getdata() if c[3] > 0} - palette
            if off:
                print("  [色盤] %s 有 %d 個色盤外的顏色（例：%s）"
                      % (rel, len(off), list(off)[:3]))
                problems += 1

            if all(c[3] == 255 for c in im.getdata()):
                print("  [透明] %s 完全不透明，背景可能沒去乾淨" % rel)
                problems += 1

    print("檢查 %d 個檔案，%d 個問題" % (checked, problems))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--out-dir")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--grid", help="例如 4x4：把來源切成 4 欄 4 列")
    ap.add_argument("--auto", action="store_true",
                    help="自動在 sheet 上找出每個角色（不必是整齊的網格，建議用這個）")
    ap.add_argument("--expect", type=int,
                    help="這張 sheet 應該有幾個角色。數量不符就中止 —— "
                         "少一個會讓後面所有檔名往前錯位，而檔案照樣寫得出來")
    ap.add_argument("--names",
                    help="用逗號分隔的檔名，取代 prefix+序號（依閱讀順序）")
    ap.add_argument("--size", type=int, default=TILE)
    ap.add_argument("--keep-bg", action="store_true")
    ap.add_argument("--no-trim", action="store_true",
                    help="不要裁到主體（地形圖塊要用，它本來就該填滿整格）")
    ap.add_argument("--headroom", type=float, default=0.0,
                    help="頭頂上面留多少比例的空白（主角用 0.1875 = 6/32，帽子要疊在那裡）")
    ap.add_argument("--zone",
                    help="縮到方框裡的某一塊並在其中置中，格式 左,上,寬,高（0~1）。穿在身上的武器與盾用這個")
    ap.add_argument("--pad", type=float, default=0.0,
                    help="左右與上面留一點空隙（下緣不動）。方形的東西會塞滿整格，在格子鋪成的畫面上讀起來像地磚")
    ap.add_argument("--band", type=float, default=0.0,
                    help="改成靠上對齊，主體最多佔這個比例的高度（帽子用 0.5）")
    ap.add_argument("--palette", choices=sorted(PALETTES),
                    help="改用某個分類的專用色盤（hero：主角身體的五色）")
    ap.add_argument("--check", help="檢查資產目錄是否合規")
    args = ap.parse_args()

    if args.check:
        sys.exit(1 if check_assets(args.check, args.size) else 0)

    if not args.src:
        ap.error("需要來源圖，或用 --check")

    palette = palette_rgb_for(args.palette)
    zone = None
    if args.zone:
        zone = tuple(float(v) for v in args.zone.split(","))
        if len(zone) != 4 or not all(0 < v <= 1 for v in zone[2:]) \
                or not all(0 <= v < 1 for v in zone[:2]):
            ap.error("--zone 要四個 0~1 的數字：左,上,寬,高")
    im = Image.open(args.src)

    if args.auto:
        out_dir = args.out_dir or "."
        os.makedirs(out_dir, exist_ok=True)
        stripped = strip_background(im)
        boxes = find_subjects(stripped)
        print("找到 %d 個角色" % len(boxes))
        names = [n.strip() for n in args.names.split(",")] if args.names else None
        want = args.expect if args.expect else (len(names) if names else None)
        if want is not None and len(boxes) != want:
            # 這裡一定要中止而不是繼續。少偵測到一個，後面每個檔名都會往前
            # 錯一格 —— 熊的圖存成蝶的檔名，而每一步都「成功」。
            sys.exit("角色數不符：找到 %d 個，應為 %d 個。"
                     "兩隻被併成一塊或有一隻沒偵測到，先確認原圖。" % (len(boxes), want))
        for i, box in enumerate(boxes):
            path = os.path.join(
                out_dir, ("%s.png" % names[i]) if names
                else ("%s%02d.png" % (args.prefix, args.start + i)))
            pixelize(stripped.crop(box), args.size, palette,
                     keep_bg=True, trim=not args.no_trim,
                     headroom=args.headroom, band=args.band, pad=args.pad,
                     zone=zone).save(path)
            print("寫出 %s（來源 %dx%d）" % (path, box[2] - box[0], box[3] - box[1]))
    elif args.grid:
        cols, rows = (int(x) for x in args.grid.lower().split("x"))
        out_dir = args.out_dir or "."
        os.makedirs(out_dir, exist_ok=True)
        for i, cell in enumerate(split_grid(im, cols, rows)):
            path = os.path.join(
                out_dir, "%s%02d.png" % (args.prefix, args.start + i))
            pixelize(cell, args.size, palette, args.keep_bg, not args.no_trim,
                     headroom=args.headroom, band=args.band, pad=args.pad,
                     zone=zone).save(path)
            print("寫出 %s" % path)
    else:
        if not args.out:
            ap.error("單張模式需要 -o")
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        pixelize(im, args.size, palette, args.keep_bg, not args.no_trim,
                 headroom=args.headroom, band=args.band, pad=args.pad,
                 zone=zone).save(args.out)
        print("寫出 %s" % args.out)


if __name__ == "__main__":
    main()
