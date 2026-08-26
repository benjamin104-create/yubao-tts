#!/usr/bin/env python3
"""把 docs/art_prompts_tile.md 組成「可以直接貼」的完整提示詞。

文件裡是拆開放的（共用前綴 / 色盤 / 材質描述 / 變體尾綴），
那樣好維護，但要用的人得自己拼四段 —— 拼錯一段就白生一批圖。

這一支負責拼。**來源只有那份文件**，所以文件改了這裡就跟著改，
不會出現「文件寫 A、實際貼出去是 B」。

    python3 tools/tile_prompts.py stone            # 印出 stone 全部 11 張
    python3 tools/tile_prompts.py stone -o out.txt # 寫成檔案
    python3 tools/tile_prompts.py --list           # 有哪些地貌
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / 'docs' / 'art_prompts_tile.md'

FLOOR_SUFFIX = [
    'Variant 1: the plainest, almost featureless. This is the base tile.',
    'Variant 2: one chipped corner and a short hairline crack.',
    'Variant 3: a faint dark stain across one third of the tile.',
    'Variant 4: a scatter of small grit and two small fragments in the seams.',
]
CORR_SUFFIX = [
    'Variant 1: plain.',
    'Variant 2: a diagonal crack.',
    'Variant 3: loose rubble along one edge.',
]


def load():
    doc = DOC.read_text(encoding='utf-8')

    # A 段的共用前綴：'## A.' 之後的第一個 ``` 區塊
    a = doc.index('## A.')
    prefix = re.search(r'```(.*?)```', doc[a:], re.S).group(1).strip()
    # A2 的亮度校準：第一批四個地貌交出來之後量到的唯一預測因子。
    # 神殿是唯一亮度超過 85 的，也是唯一失敗的 —— 所以這一段要跟著每一張走。
    a2 = doc.find('## A2.')
    if a2 >= 0:
        m2 = re.search(r'```(.*?)```', doc[a2:doc.index('## B.')], re.S)
        if m2:
            prefix = prefix + '\n' + m2.group(1).strip()

    # F 段的柱子／巨石：表格 + 通用敘述
    f = doc.index('## F.')
    blocker_body = re.search(r'```(.*?)```', doc[f:], re.S).group(1).strip()
    # 文件裡那一行 `[A 共用前綴（…）] + [該地貌的 Palette 那一行] +` 是寫給人看的
    # 組裝說明，不是給模型的指令。組好之後那幾段已經真的接在上面了，
    # 留著的話模型會把「把 SEAMLESS TILING 那一條拿掉」當成畫圖要求。
    blocker_body = '\n'.join(
        l for l in blocker_body.splitlines() if not l.lstrip().startswith('[')).strip()
    blockers = {}
    for th, b0, b1 in re.findall(
            r'\|\s*`([a-z]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', doc[f:]):
        blockers[th] = (b0, b1)

    themes = {}
    for m in re.finditer(r'### \d+\. `([a-z]+)` —— ([^\n]*)\n(.*?)(?=\n### |\n## )',
                         doc, re.S):
        th, chapters, body = m.group(1), m.group(2).strip(), m.group(3)
        pal = re.search(r'```\s*(Palette anchored to:.*?)```', body, re.S)
        parts = {}
        for slot in ('floor', 'corr', 'wall', 'wallface'):
            s = re.search(r'\*\*%s\*\*：`(.*?)`' % slot, body, re.S)
            if s:
                parts[slot] = ' '.join(s.group(1).split())
        themes[th] = {'chapters': chapters,
                      'palette': ' '.join(pal.group(1).split()) if pal else '',
                      'parts': parts}
    return prefix, themes, blockers, blocker_body


def emit(theme, prefix, themes, blockers, blocker_body):
    t = themes[theme]
    out = []
    out.append('=' * 68)
    out.append('地貌 %s —— %s' % (theme, t['chapters']))
    out.append('共 11 張。每一段都是完整的，直接整段複製貼給生圖模型。')
    out.append('轉檔：python3 tools/pixelize.py <圖> --grid 4x3 --size 32 '
               '--keep-bg --no-trim --out-dir web/art/tile/%s' % theme)
    out.append('=' * 68)

    def block(name, body, extra=''):
        out.append('')
        out.append('-' * 68)
        out.append('### %s.png' % name)
        out.append('-' * 68)
        out.append(prefix)
        out.append('')
        out.append(t['palette'])
        out.append('')
        out.append(body + ((' ' + extra) if extra else ''))

    for i, suf in enumerate(FLOOR_SUFFIX):
        block('floor%d' % i, t['parts']['floor'], suf)
    for i, suf in enumerate(CORR_SUFFIX):
        block('corr%d' % i, t['parts']['corr'], suf)
    block('wall', t['parts']['wall'])
    block('wallface', t['parts']['wallface'])

    # 柱子／巨石：背景要透明，所以要把無縫鋪貼那一條拿掉
    nb = '\n'.join(l for l in prefix.splitlines()
                   if 'SEAMLESS' not in l and 'Do NOT draw a border' not in l
                   and 'four edges must flow' not in l)
    for i, what in enumerate(blockers.get(theme, ('', ''))):
        if not what:
            continue
        out.append('')
        out.append('-' * 68)
        out.append('### blocker%d.png　（背景透明，轉檔時**不要**加 --keep-bg）' % i)
        out.append('-' * 68)
        out.append(nb)
        out.append('')
        out.append(t['palette'])
        out.append('')
        out.append(blocker_body)
        out.append('')
        out.append('The obstacle is: %s.' % what)
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('theme', nargs='?')
    ap.add_argument('-o', '--out')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--all', action='store_true')
    args = ap.parse_args()

    prefix, themes, blockers, blocker_body = load()
    if args.list or (not args.theme and not args.all):
        print('地貌（共 %d 個）：' % len(themes))
        for th, t in themes.items():
            print('  %-10s %s' % (th, t['chapters']))
        return 0
    picked = list(themes) if args.all else [args.theme]
    bad = [p for p in picked if p not in themes]
    if bad:
        sys.exit('沒有這個地貌：%s\n可用的：%s' % ('、'.join(bad), '、'.join(themes)))
    text = '\n\n'.join(emit(p, prefix, themes, blockers, blocker_body) for p in picked)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding='utf-8')
        print('寫出 %s（%d 字）' % (args.out, len(text)))
    else:
        print(text)
    return 0


sys.exit(main())
