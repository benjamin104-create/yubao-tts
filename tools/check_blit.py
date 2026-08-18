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
# 驗收頁的產生器也要掃：它一樣在畫精靈，而且犯過一模一樣的錯 ——
# 畫進 16x16 的畫布卻沒指定尺寸，32px 的圖只會出現左上角四分之一。
# 掃產生器而不是掃產出的 sprite_sheet.html：產出的檔案是可以重建的，
# 錯誤的來源永遠在產生器裡。
SRCS = [ROOT / 'web' / 'index.html', ROOT / 'tools' / 'build_sprite_sheet.py']

# 豁免清單：來源與目的地是同一尺寸的畫布，整張複製，不需要指定尺寸。
#
# 鍵是「哪個檔案裡、長這樣的行，最多幾個」。試過兩種更差的寫法：
#
#   只比字面 —— 驗收頁裡新寫的 `x.drawImage(src, 0, 0)` 剛好跟 crownSprite
#   那行長得一樣，直接被放行，破壞測試沒有變紅。豁免不能是「長這樣的每一行」。
#
#   綁行號 —— 在檔案前面插一行，五個豁免全部失效，而且報成「這五行漏了尺寸」，
#   等於叫人去改五個本來就沒問題的地方。行號對這種檔案太脆。
#
# 綁數量剛好：行搬到哪裡都無所謂，但**多出一個**就會被抓到 ——
# 而「多出一個」正是我們要防的那件事。
ALLOW = {
    'web/index.html': {
        'x.drawImage(src, 0, 0);': 1,   # crownSprite：從來源精靈複製
        'x.drawImage(im, 0, 0);': 1,    # adoptArt：把載進來的圖原樣拓進畫布
        'x.drawImage(tmp, 0, 4);': 1,   # 圖示往下移，讓它落在格子中間
        'x.drawImage(img, 0, 0);': 2,   # whiteOf 與 footOf 的量測用暫存拷貝
    },
}

seen = {}


def exempt(rel, line):
    quota = ALLOW.get(rel, {})
    for want, cap in quota.items():
        if line.startswith(want):
            k = (rel, want)
            seen[k] = seen.get(k, 0) + 1
            return seen[k] <= cap
    return False


bad = []
for SRC in SRCS:
  for i, line in enumerate(SRC.read_text(encoding='utf-8').split('\n'), 1):
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
        if exempt(str(SRC.relative_to(ROOT)), line.strip()):
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
            bad.append((SRC.relative_to(ROOT), i, line.strip()[:96]))

if bad:
    print('有 %d 處 drawImage 省略了目的地尺寸：' % len(bad))
    for f, i, line in bad:
        print('  %s:%d  %s' % (f, i, line))
    print('\n改成 blit(img, x, y) 或補上尺寸參數。')
    sys.exit(1)

print('drawImage 全部都有指定尺寸')
