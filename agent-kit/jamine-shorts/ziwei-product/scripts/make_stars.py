# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/tmp/NotoSansTC.ttf"
OUT = "/tmp/hfdemo/stars"
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
    # subtle radial glow
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W*0.05, -H*0.15, W*0.95, H*0.55], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    warm = Image.new("RGB", (W, H), (54, 40, 22))
    img = Image.composite(warm, img, glow)
    return img

def tw(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f)
    return b[2]-b[0], b[3]-b[1]

def ctext(d, cx, y, txt, f, fill):
    w, h = tw(d, txt, f)
    d.text((cx-w/2, y), txt, font=f, fill=fill)
    return y + h

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
    if cur:
        lines.append(cur)
    return lines

def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def pill(d, x, y, txt, f, pad=22):
    w, h = tw(d, txt, f)
    box = [x, y, x+w+pad*2, y+h+18]
    rrect(d, box, 18, fill=(46, 36, 22), outline=GOLD_D, width=2)
    d.text((x+pad, y+7), txt, font=f, fill=GOLD)
    return box[2], box[3]

# ---- 14 star data: name, role, oneliner, keywords[3], like, tip
STARS = [
    ("紫微", "帝王星", "天生想當老大", ["有氣場", "重面子", "想被尊重"],
     "像公司裡不講話也有威嚴的大老闆。", "身邊要有人輔佐，沒人捧會有點孤單。"),
    ("天機", "軍師星", "腦子轉不停的聰明人", ["機靈", "點子多", "愛分析"],
     "像團隊裡一直在想策略的軍師。", "想太多容易內耗，記得讓腦袋休息。"),
    ("太陽", "大家長星", "發光發熱、照顧大家", ["熱心", "講義氣", "愛付出"],
     "像總是請客、罩全場的那位大哥大姊。", "照顧別人前，先留一點電給自己。"),
    ("武曲", "將軍星", "說到做到的行動派", ["果決", "重承諾", "會賺錢"],
     "像衝第一、目標必達的業務冠軍。", "講話太直，記得加一點溫度。"),
    ("天同", "福星", "樂天知足的大孩子", ["天真", "好相處", "懂享受"],
     "像永遠笑笑、人緣超好的同事。", "有時太被動，偶爾要推自己一把。"),
    ("廉貞", "外交官星", "能屈能伸的多面手", ["有魅力", "會交際", "有個性"],
     "像場面得體、檯面下有想法的公關高手。", "內心其實叛逆，別硬壓著自己。"),
    ("天府", "宰相星", "穩穩當當的大管家", ["包容", "會理財", "給安全感"],
     "像把家裡公司打理得井井有條的總管。", "有點愛囤、放不下，學著鬆手。"),
    ("太陰", "母親星", "溫柔細膩的月光", ["體貼", "重感情", "想很多"],
     "像默默把你照顧好、話不多的媽媽。", "心事別都自己扛，說出來會輕鬆。"),
    ("貪狼", "交際星", "多才多藝的玩家", ["好奇", "會玩會撩", "才華多"],
     "像什麼都會一點、走到哪都熱鬧的人。", "定性是功課，別只有三分鐘熱度。"),
    ("巨門", "評論家星", "靠一張嘴吃飯", ["能言", "追根究柢", "觀察力強"],
     "像律師、名嘴、最會吐槽的那位朋友。", "話別太利，容易不小心得罪人。"),
    ("天相", "副手星", "公道可靠的好幫手", ["講公平", "重形象", "樂輔佐"],
     "像最稱職的副手、左右手。", "太沒主見會被牽著走，學會說不。"),
    ("天梁", "長老星", "罩著你的老前輩", ["有原則", "愛照顧", "逢凶化吉"],
     "像會幫你擋事、給你建議的長輩。", "愛說教，點到為止就剛剛好。"),
    ("七殺", "前鋒星", "衝第一的勇者", ["果斷", "敢拚", "獨立"],
     "像第一個跳出來扛事的開路先鋒。", "怕被綁住，但記得也要把事收尾。"),
    ("破軍", "開創星", "打掉重練的開拓者", ["敢變", "有魄力", "不走老路"],
     "像勇於砍掉重練、開創新局的創業者。", "起伏較大，存點底氣再往前衝。"),
]

def star_card(idx, data):
    name, role, one, kws, like, tip = data
    img = base()
    d = ImageDraw.Draw(img)
    PAD = 80
    # top strip
    d.text((PAD, 70), "潔米爸的書房筆記 · 十四主星圖鑑", font=F(30), fill=MUT)
    num = f"{idx:02d} / 14"
    nw = tw(d, num, F(30, True))[0]
    d.text((W-PAD-nw, 70), num, font=F(30, True), fill=GOLD)
    d.line([PAD, 128, W-PAD, 128], fill=(60, 48, 30), width=2)

    # big star name
    y = 200
    y = ctext(d, W/2, y, name, F(168, True), GOLD)
    y += 36
    # role badge centered
    rf = F(46, True)
    rw, rh = tw(d, role, rf)
    bx = (W-(rw+90))/2
    rrect(d, [bx, y, bx+rw+90, y+rh+30], 26, fill=(46, 36, 22), outline=GOLD, width=3)
    d.text((bx+45, y+13), role, font=rf, fill=GOLD)
    y += rh+30+40
    # one-liner
    y = ctext(d, W/2, y, f"「{one}」", F(58, True), CREAM)
    y += 50
    d.line([W/2-90, y, W/2+90, y], fill=GOLD_D, width=3)
    y += 50

    # keyword pills row (centered)
    kf = F(34, True)
    widths = [tw(d, k, kf)[0]+44 for k in kws]
    gap = 24
    total = sum(widths)+gap*(len(kws)-1)
    x = (W-total)/2
    for k, wp in zip(kws, widths):
        rrect(d, [x, y, x+wp, y+62], 18, fill=(40, 31, 19), outline=GOLD_D, width=2)
        kw_ = tw(d, k, kf)[0]
        d.text((x+(wp-kw_)/2, y+12), k, font=kf, fill=GOLD)
        x += wp+gap
    y += 62+70

    # like block
    bf = F(34, True)
    sf = F(40)
    card_x = PAD
    cw = W-2*PAD
    # "像這樣的人"
    rrect(d, [card_x, y, card_x+cw, y+200], 28, fill=CARDBG, outline=(58, 46, 28), width=2)
    d.text((card_x+40, y+34), "▍像這樣的人", font=bf, fill=GOLD)
    ly = y+96
    for ln in wrap(d, like, sf, cw-80):
        d.text((card_x+40, ly), ln, font=sf, fill=CREAM)
        ly += 56
    y += 200+34

    # tip block
    rrect(d, [card_x, y, card_x+cw, y+200], 28, fill=CARDBG, outline=(58, 46, 28), width=2)
    d.text((card_x+40, y+34), "▍小提醒", font=bf, fill=GOLD)
    ly = y+96
    for ln in wrap(d, tip, sf, cw-80):
        d.text((card_x+40, ly), ln, font=sf, fill=CREAM)
        ly += 56

    # footer
    foot = "命盤是地圖，不是算命 · @jamine_pa"
    fw = tw(d, foot, F(30))[0]
    d.text(((W-fw)/2, H-78), foot, font=F(30), fill=MUT)
    img.save(f"{OUT}/star_{idx:02d}_{name}.png")

# ---- cover
def cover():
    img = base()
    d = ImageDraw.Draw(img)
    PAD = 80
    d.text((PAD, 90), "潔米爸的書房筆記", font=F(34), fill=MUT)
    d.text((PAD, 138), "心理學 × 紫微 × 心流", font=F(30), fill=GOLD_D)
    y = 270
    y = ctext(d, W/2, y, "十四主星", F(138, True), GOLD)
    y = ctext(d, W/2, y+6, "圖鑑", F(138, True), GOLD)
    y += 56
    y = ctext(d, W/2, y, "用一個角色，秒懂你是哪顆星", F(48, True), CREAM)
    y += 26
    y = ctext(d, W/2, y, "帝王 · 軍師 · 將軍 · 宰相 · 前鋒 · 外交官……", F(32), MUT)
    # avatar
    try:
        av = Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw = 330
        scale = aw/av.width
        av = av.resize((aw, int(av.height*scale)))
        img.paste(av, (int((W-aw)/2), H-av.height-130), av)
    except Exception as e:
        print("avatar", e)
    foot = "向右滑，看看你認識幾顆 →"
    fw = tw(d, foot, F(32, True))[0]
    d.text(((W-fw)/2, H-72), foot, font=F(32, True), fill=GOLD)
    img.save(f"{OUT}/star_00_封面.png")

# ---- CTA end
def cta():
    img = base()
    d = ImageDraw.Draw(img)
    y = 300
    y = ctext(d, W/2, y, "那……", F(60, True), MUT)
    y += 30
    y = ctext(d, W/2, y, "你的命宮", F(96, True), CREAM)
    y = ctext(d, W/2, y+10, "是哪一顆主星？", F(96, True), GOLD)
    y += 80
    for ln in ["十四顆星，落在你命盤不同位置，", "組成獨一無二的你。", "", "留言「主星」，", "我送你一份主星對照小卡，", "陪你慢慢看懂自己。"]:
        if ln == "":
            y += 30; continue
        col = GOLD if "主星" in ln and "留言" in ln else CREAM
        y = ctext(d, W/2, y, ln, F(46, True if "留言" in ln else False), col)
        y += 18
    # button
    y += 40
    bw, bh = 620, 120
    bx = (W-bw)/2
    rrect(d, [bx, y, bx+bw, y+bh], 30, fill=GOLD)
    btxt = "留言「主星」"
    bf = F(54, True)
    btw, bth = tw(d, btxt, bf)
    d.text(((W-btw)/2, y+(bh-bth)/2-6), btxt, font=bf, fill=(26, 18, 10))
    foot = "潔米爸陪你慢慢看 · @jamine_pa"
    fw = tw(d, foot, F(30))[0]
    d.text(((W-fw)/2, H-90), foot, font=F(30), fill=MUT)
    img.save(f"{OUT}/star_15_領取.png")

cover()
for i, s in enumerate(STARS, start=1):
    star_card(i, s)
cta()
print("done:", len(os.listdir(OUT)), "files")
