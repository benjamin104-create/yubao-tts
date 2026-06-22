# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "/tmp/NotoSansTC.ttf"
OUT = "/tmp/hfdemo/boundary5"
os.makedirs(OUT, exist_ok=True)
W, H = 1080, 1350
BG=(13,10,7); GOLD=(224,162,78); GOLD_D=(150,105,48); CREAM=(231,221,204); MUT=(150,138,117); CARDBG=(26,20,13)

def F(sz, bold=False):
    f=ImageFont.truetype(FONT,sz)
    try: f.set_variation_by_axes([700 if bold else 400])
    except: pass
    return f
def base():
    img=Image.new("RGB",(W,H),BG); glow=Image.new("L",(W,H),0); gd=ImageDraw.Draw(glow)
    gd.ellipse([W*0.05,-H*0.15,W*0.95,H*0.55],fill=70); glow=glow.filter(ImageFilter.GaussianBlur(180))
    return Image.composite(Image.new("RGB",(W,H),(54,40,22)),img,glow)
def tw(d,t,f):
    b=d.textbbox((0,0),t,font=f); return b[2]-b[0],b[3]-b[1]
def ctext(d,cx,y,t,f,fill):
    w,h=tw(d,t,f); d.text((cx-w/2,y),t,font=f,fill=fill); return y+h
def wrap(d,t,f,mw):
    L,c=[],""
    for ch in t:
        if ch=="\n": L.append(c);c="";continue
        if tw(d,c+ch,f)[0]>mw and c: L.append(c);c=ch
        else: c+=ch
    if c:L.append(c)
    return L
def rr(d,b,r,fill=None,outline=None,width=1): d.rounded_rectangle(b,radius=r,fill=fill,outline=outline,width=width)

# 3 themed groups; each item = (situation, line)
GROUPS = [
    ("面對別人的情緒與要求", [
        ("有人把壞情緒丟到你身上", "我願意聽你說，但請不要用這個語氣對我。"),
        ("又被臨時拜託、你其實已經很累", "這次我沒辦法，下次有空我再幫你。"),
        ("怕對方失望，所以很想答應", "我需要一點時間想想，再回覆你。"),
    ]),
    ("守住屬於你的空間", [
        ("被問了不想回答的私事", "這個我想自己留著，謝謝你關心。"),
        ("訊息一直追著你、壓力很大", "我看到了，我晚點再好好回你。"),
        ("聚會後，你需要獨處充電", "我今天先回家休息，下次再約。"),
    ]),
    ("也對自己溫柔一點", [
        ("你習慣先說「對不起」", "把「對不起」換成「謝謝你等我」。"),
        ("聽完別人的煩惱，自己也沉下去", "這是他的情緒，不是我的。"),
        ("有人隨意評價、否定你", "你可以有你的看法，我也可以保留我的。"),
        ("沒做到，就開始責怪自己", "我已經盡力了，這樣就夠了。"),
    ]),
]

def group_card(idx, total, title, items):
    img=base(); d=ImageDraw.Draw(img); PAD=80
    d.text((PAD,70),"潔米爸的書房筆記 · 溫柔邊界小卡",font=F(30),fill=MUT)
    num=f"{idx} / {total}"; nw=tw(d,num,F(30,True))[0]
    d.text((W-PAD-nw,70),num,font=F(30,True),fill=GOLD)
    d.line([PAD,128,W-PAD,128],fill=(60,48,30),width=2)
    # title
    y=176
    d.text((PAD,y),title,font=F(52,True),fill=GOLD)
    y+=104
    n=len(items)
    qf=F(40 if n>=4 else 41,True); sf=F(31)
    QW=W-2*PAD-50
    GAP=38; PADT=30; PADB=30; SIT_H=52; Q_H=58
    # measure box heights (compact, hug content)
    heights=[]
    for sit,line in items:
        qlines=wrap(d,"「"+line+"」",qf,QW)
        heights.append(PADT+SIT_H+Q_H*len(qlines)+PADB)
    total=sum(heights)+GAP*(n-1)
    avail_top=y; avail_bot=H-110
    # top-align under title, but nudge down a little if lots of slack
    slack=avail_bot-avail_top-total
    top=avail_top+min(60,max(0,slack/2))
    for (sit,line),bh in zip(items,heights):
        rr(d,[PAD,top,W-PAD,top+bh],24,fill=CARDBG,outline=(54,42,26),width=2)
        iy=top+PADT
        d.text((PAD+38,iy),"情境 · "+sit,font=sf,fill=MUT); iy+=SIT_H
        for ln in wrap(d,"「"+line+"」",qf,QW):
            d.text((PAD+38,iy),ln,font=qf,fill=CREAM); iy+=Q_H
        top+=bh+GAP
    foot="不傷人，也不傷自己 · @jamine_pa"; fw=tw(d,foot,F(30))[0]
    d.text(((W-fw)/2,H-70),foot,font=F(30),fill=MUT)
    img.save(f"{OUT}/p{idx}.png")

def cover(total):
    img=base(); d=ImageDraw.Draw(img); PAD=80
    d.text((PAD,90),"潔米爸的書房筆記",font=F(34),fill=MUT)
    d.text((PAD,138),"心理學 · 高敏感 · 自我照顧",font=F(30),fill=GOLD_D)
    y=300; y=ctext(d,W/2,y,"溫柔邊界",F(150,True),GOLD); y+=40
    y=ctext(d,W/2,y,"給高敏感的你",F(54,True),CREAM); y+=24
    y=ctext(d,W/2,y,"10 句不傷人、也不傷自己的話",F(36),MUT); y+=70
    for ln in ["不是要你變冷漠，","是讓你不再一直被消耗，","也還能保有你的柔軟。"]:
        y=ctext(d,W/2,y,ln,F(42,True),CREAM); y+=14
    try:
        av=Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw=300; sc=aw/av.width; av=av.resize((aw,int(av.height*sc)))
        img.paste(av,(int((W-aw)/2),H-av.height-120),av)
    except Exception as e: print("av",e)
    foot="向右滑，收下你的邊界 →"; fw=tw(d,foot,F(32,True))[0]
    d.text(((W-fw)/2,H-72),foot,font=F(32,True),fill=GOLD)
    img.save(f"{OUT}/p0.png")

def closing(idx,total):
    img=base(); d=ImageDraw.Draw(img); PAD=90
    y=380; y=ctext(d,W/2,y,"最後，記得——",F(48,True),MUT); y+=70
    for ln,col,bold in [("設立邊界，",CREAM,True),("不是把人推開，",CREAM,True),("",None,False),
                        ("是讓對的人，",GOLD,True),("用對的方式靠近你。",GOLD,True)]:
        if ln=="": y+=36; continue
        y=ctext(d,W/2,y,ln,F(60,bold),col); y+=20
    y+=70
    for ln in ["你值得被好好對待，","也包括，被你自己好好對待。"]:
        y=ctext(d,W/2,y,ln,F(40),CREAM); y+=16
    foot="潔米爸陪你慢慢練 · @jamine_pa"; fw=tw(d,foot,F(32))[0]
    d.text(((W-fw)/2,H-90),foot,font=F(32),fill=MUT)
    img.save(f"{OUT}/p{idx}.png")

TOTAL=5
cover(TOTAL)
for i,(t,items) in enumerate(GROUPS, start=1):
    group_card(i,TOTAL,t,items)
closing(4,TOTAL)
print("done",sorted(os.listdir(OUT)))
