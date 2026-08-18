#!/usr/bin/env python3
"""畫圖的時候不准省略目的地尺寸。

抓的是這個 bug：drawImage(img, x, y) 省略尺寸時，canvas 會照**來源圖的
像素大小**畫。過去所有精靈都是程式畫的 16px、剛好等於一格，所以省略尺寸
看起來完全正常，二十幾處都是這樣寫的。接上 32px 的外部圖之後，
同一行程式會畫成 2x2 格。

它不會報錯，而且只在「換了那張圖」之後才發作 ——
實測殺掉哥布林之後，屍體是一隻兩倍大的哥布林蓋在隔壁三格上，
飄 0.4 秒才散掉。怪物本體沒事（drawEnt 有指定尺寸），
只有屍體、道具、地磚這些順手寫的有事。

所以這一支用靜態掃描而不是跑起來看：跑起來只看得到「現在換過的那幾張」，
而這個 bug 的本質是「下一批圖進來才爆」。

    python3 tools/check_blit.py
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'web' / 'index.html'

# 這些呼叫的來源與目的地是同一個尺寸的畫布，整張複製，不需要指定尺寸。
# 列成白名單而不是放寬規則 —— 每多一個例外都要在這裡寫下來。
ALLOW = [
    'drawImage(im, 0, 0)',     # adoptArt：把載進來的圖原樣拓進畫布
    'drawImage(src, 0, 0)',    # crownSprite：從來源精靈複製
    'drawImage(img, 0, 0)',    # whiteOf / footOf：量測用的暫存拷貝
    'drawImage(tmp, 0, 4)',    # 圖示往下移四格，讓它落在格子中間
]

text = SRC.read_text(encoding='utf-8')
bad = []
for i, line in enumerate(text.split('\n'), 1):
    for m in re.finditer(r'drawImage\(', line):
        # 從左括號開始配對括號，取出整個呼叫
        depth, j = 0, m.end() - 1
        while j < len(line):
            if line[j] == '(':
                depth += 1
            elif line[j] == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        call = line[m.start():j + 1]
        if any(a in call for a in ALLOW):
            continue
        # 只數最外層的逗號 —— 內層的 makeBlob('l',{...}) 不算
        depth, commas = 0, 0
        for ch in call[m.end() - m.start():]:
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth -= 1
                if depth < 0:
                    break
            elif ch == ',' and depth == 0:
                commas += 1
        args = commas + 1
        # 3 個參數 = 省略了尺寸；5 或 9 個才是有指定的形式
        if args == 3:
            bad.append((i, line.strip()[:96]))

if bad:
    print('有 %d 處 drawImage 省略了目的地尺寸：' % len(bad))
    for i, line in bad:
        print('  web/index.html:%d  %s' % (i, line))
    print('\n改成 blit(img, x, y) 或補上尺寸參數。')
    sys.exit(1)

print('drawImage 全部都有指定尺寸')
