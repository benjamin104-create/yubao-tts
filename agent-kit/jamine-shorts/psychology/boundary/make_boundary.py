# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/tmp/NotoSansTC.ttf"
OUT = "/tmp/hfdemo/boundary"
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1350
BG = (13, 10, 7)
GOLD = (224, 162, 78)
GOLD_D = (150, 105, 48)
CREAM = (231, 221, 204)
MUT = (150, 138, 117)
CARDBG = (28, 22, 15)

def F(sz, bold=False):
    f = ImageFont.truetype(FONT, sz)
    try:
        f.set_variation_by_axes([700 if bold else 400])
    except Exception:
        pass
    return f

def base():
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W*0.05, -H*0.15, W*0.95, H*0.55], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    warm = Image.new("RGB", (W, H), (54, 40, 22))
    return Image.composite(warm, img, glow)

def tw(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f); return b[2]-b[0], b[3]-b[1]

def ctext(d, cx, y, txt, f, fill):
    w, h = tw(d, txt, f); d.text((cx-w/2, y), txt, font=f, fill=fill); return y+h

def wrap(d, txt, f, maxw):
    lines, cur = [], ""
    for ch in txt:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        t = cur+ch
        if tw(d, t, f)[0] > maxw and cur:
            lines.append(cur); cur = ch
        else:
            cur = t
    if cur: lines.append(cur)
    return lines

def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

# situation, say-label, line(s), protect
CARDS = [
    ("有人把壞情緒丟到你身上", "你可以說",
     "我願意聽你說，\n但請不要用這個語氣對我。",
     "你可以同理別人，但不必承接他的情緒。"),
    ("又被臨時拜託，你其實已經很累", "你可以說",
     "這次我沒辦法，\n下次有空我再幫你。",
     "拒絕一件事，不等於拒絕一個人。"),
    ("你總是習慣先說「對不起」", "把它換成",
     "把「對不起」\n換成「謝謝你等我」。",
     "你沒有做錯，不需要為自己的存在道歉。"),
    ("被問了不想回答的私事", "你可以說",
     "這個我想自己留著，\n謝謝你關心。",
     "不回答，也是一種完整的回答。"),
    ("訊息一直追著你，壓力很大", "你可以回",
     "我看到了，\n我晚點再好好回你。",
     "你的回覆速度，不是你價值的證明。"),
    ("聽完別人的煩惱，自己也沉下去", "心裡默念",
     "這是他的情緒，\n不是我的。",
     "你可以陪伴，但不必把它扛回家。"),
    ("想答應，只因為怕對方失望", "你可以說",
     "我需要一點時間想想，\n再回覆你。",
     "別人的失望，是他要消化的，不是你要扛的。"),
    ("聚會後，你需要獨處充電", "你可以說",
     "我今天先回家休息，\n下次再約。",
     "獨處不是孤僻，是你回血的方式。"),
    ("有人隨意評價、否定你", "你可以說",
     "你可以有你的看法，\n我也可以保留我的。",
     "別人的評價是參考，不是判決。"),
    ("沒做到，就開始責怪自己", "對自己說",
     "我已經盡力了，\n這樣就夠了。",
     "你對自己的溫柔，也是一種邊界。"),
]

def card(idx, data):
    sit, saylab, line, protect = data
    img = base(); d = ImageDraw.Draw(img); PAD = 80
    d.text((PAD, 70), "潔米爸的書房筆記 · 溫柔邊界小卡", font=F(30), fill=MUT)
    num = f"{idx:02d} / 10"
    nw = tw(d, num, F(30, True))[0]
    d.text((W-PAD-nw, 70), num, font=F(30, True), fill=GOLD)
    d.line([PAD, 128, W-PAD, 128], fill=(60, 48, 30), width=2)

    # 情境 label + text
    y = 200
    d.text((PAD, y), "情境", font=F(34, True), fill=GOLD)
    d.line([PAD, y+58, PAD+72, y+58], fill=GOLD, width=4)
    y += 86
    for ln in wrap(d, sit, F(46, True), W-2*PAD):
        d.text((PAD, y), ln, font=F(46, True), fill=CREAM); y += 64
    y += 36

    # hero say-box
    box_top = y
    lines = line.split("\n")
    lf = F(62, True)
    line_h = 84
    box_h = 150 + line_h*len(lines)
    rrect(d, [PAD, box_top, W-PAD, box_top+box_h], 32, fill=CARDBG, outline=GOLD, width=3)
    # label chip
    lab = f"｜{saylab}｜"
    labf = F(34, True)
    lw = tw(d, lab, labf)[0]
    d.text(((W-lw)/2, box_top+38), lab, font=labf, fill=GOLD)
    ly = box_top+108
    for ln in lines:
        ctext(d, W/2, ly, ln, lf, CREAM); ly += line_h
    y = box_top+box_h+60

    # protect block
    d.text((PAD, y), "▍它在保護你", font=F(34, True), fill=GOLD)
    y += 64
    for ln in wrap(d, protect, F(40), W-2*PAD-10):
        d.text((PAD, y), ln, font=F(40), fill=CREAM); y += 56

    foot = "不傷人，也不傷自己 · @jamine_pa"
    fw = tw(d, foot, F(30))[0]
    d.text(((W-fw)/2, H-78), foot, font=F(30), fill=MUT)
    img.save(f"{OUT}/b_{idx:02d}.png")

def cover():
    img = base(); d = ImageDraw.Draw(img); PAD = 80
    d.text((PAD, 90), "潔米爸的書房筆記", font=F(34), fill=MUT)
    d.text((PAD, 138), "心理學 · 高敏感 · 自我照顧", font=F(30), fill=GOLD_D)
    y = 300
    y = ctext(d, W/2, y, "溫柔邊界", F(150, True), GOLD)
    y += 40
    y = ctext(d, W/2, y, "給高敏感的你", F(54, True), CREAM)
    y += 24
    y = ctext(d, W/2, y, "10 句不傷人、也不傷自己的話", F(36), MUT)
    y += 70
    for ln in ["不是要你變冷漠，", "是讓你不再一直被消耗，", "也還能保有你的柔軟。"]:
        y = ctext(d, W/2, y, ln, F(42, True), CREAM); y += 14
    try:
        av = Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw = 300; sc = aw/av.width
        av = av.resize((aw, int(av.height*sc)))
        img.paste(av, (int((W-aw)/2), H-av.height-120), av)
    except Exception as e:
        print("av", e)
    foot = "向右滑，收下你的邊界 →"
    fw = tw(d, foot, F(32, True))[0]
    d.text(((W-fw)/2, H-72), foot, font=F(32, True), fill=GOLD)
    img.save(f"{OUT}/b_00_封面.png")

def closing():
    img = base(); d = ImageDraw.Draw(img); PAD = 90
    y = 380
    y = ctext(d, W/2, y, "最後，記得——", F(48, True), MUT)
    y += 70
    for ln, col, bold in [
        ("設立邊界，", CREAM, True),
        ("不是把人推開，", CREAM, True),
        ("", None, False),
        ("是讓對的人，", GOLD, True),
        ("用對的方式靠近你。", GOLD, True),
    ]:
        if ln == "":
            y += 36; continue
        y = ctext(d, W/2, y, ln, F(60, bold), col); y += 20
    y += 70
    for ln in ["你值得被好好對待，", "也包括，被你自己好好對待。"]:
        y = ctext(d, W/2, y, ln, F(40), CREAM); y += 16
    foot = "潔米爸陪你慢慢練 · @jamine_pa"
    fw = tw(d, foot, F(32))[0]
    d.text(((W-fw)/2, H-90), foot, font=F(32), fill=MUT)
    img.save(f"{OUT}/b_11_結語.png")

cover()
for i, c in enumerate(CARDS, start=1):
    card(i, c)
closing()
print("done", len(os.listdir(OUT)))
