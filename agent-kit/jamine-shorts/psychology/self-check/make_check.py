# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/check"; os.makedirs(OUT,exist_ok=True)
W,H=1080,1350
BG=(13,10,7); GOLD=(224,162,78); GOLD_D=(150,105,48); CREAM=(231,221,204); MUT=(150,138,117); CARDBG=(26,20,13)

def F(sz,bold=False):
    f=ImageFont.truetype(FONT,sz)
    try: f.set_variation_by_axes([700 if bold else 400])
    except: pass
    return f
def base():
    img=Image.new("RGB",(W,H),BG); g=Image.new("L",(W,H),0); gd=ImageDraw.Draw(g)
    gd.ellipse([W*0.05,-H*0.15,W*0.95,H*0.55],fill=70); g=g.filter(ImageFilter.GaussianBlur(180))
    return Image.composite(Image.new("RGB",(W,H),(54,40,22)),img,g)
def tw(d,t,f):
    b=d.textbbox((0,0),t,font=f); return b[2]-b[0],b[3]-b[1]
def ct(d,cx,y,t,f,fill):
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

# (number, 標題, 內文)
ITEMS=[
    ("01","先看看你在用誰的標準","問自己一句：「這是我自己想要的，還是別人說的？」搞清楚，心就鬆一半。"),
    ("02","別跟別人比，跟昨天的自己比","今天比昨天多會一點點，就是進步了，不用贏過誰。"),
    ("03","換個說法對自己講","「我不夠好」其實是「我想變更好」。同一件事，換句話說，就沒那麼刺。"),
    ("04","每天記一件你有做到的小事","再小都算。看到自己有在動，你就撐得住。"),
    ("05","對自己說話客氣一點","別罵自己「怎麼還不會」，改成「我有看到我在努力」。"),
    ("06","太累了，就把尺放下","放下不是放棄，是讓自己喘口氣。喘夠了，才走得遠。"),
]

def card(idx,total,title,group):
    img=base(); d=ImageDraw.Draw(img); PAD=80
    d.text((PAD,70),"潔米爸的書房筆記 · 溫柔自我檢查",font=F(30),fill=MUT)
    num=f"{idx} / {total}"; nw=tw(d,num,F(30,True))[0]
    d.text((W-PAD-nw,70),num,font=F(30,True),fill=GOLD)
    d.line([PAD,128,W-PAD,128],fill=(60,48,30),width=2)
    y=176; d.text((PAD,y),title,font=F(50,True),fill=GOLD); y+=100
    tf=F(41,True); bf=F(34); QW=W-2*PAD-76
    PADT=30; THG=10; TIT_H=52; B_LH=48; PADB=30
    heights=[]
    for n_,h_,body in group:
        heights.append(PADT+TIT_H+THG+B_LH*len(wrap(d,body,bf,QW))+PADB)
    tot=sum(heights)+34*(len(group)-1)
    slack=(H-110)-y-tot
    top=y+min(50,max(0,slack/2))
    for (n_,h_,body),bh in zip(group,heights):
        rr(d,[PAD,top,W-PAD,top+bh],24,fill=CARDBG,outline=(54,42,26),width=2)
        d.text((PAD+38,top+PADT+4),n_,font=F(30,True),fill=GOLD_D)
        d.text((PAD+38+60,top+PADT-2),h_,font=tf,fill=CREAM)
        iy=top+PADT+TIT_H+THG
        for ln in wrap(d,body,bf,QW):
            d.text((PAD+38,iy),ln,font=bf,fill=MUT); iy+=B_LH
        top+=bh+34
    foot="慢慢量回自己 · @jamine_pa"; fw=tw(d,foot,F(30))[0]
    d.text(((W-fw)/2,H-70),foot,font=F(30),fill=MUT)
    img.save(f"{OUT}/p{idx}.png")

def cover():
    img=base(); d=ImageDraw.Draw(img); PAD=80
    d.text((PAD,90),"潔米爸的書房筆記",font=F(34),fill=MUT)
    d.text((PAD,138),"心理學 · 自我價值 · 阿德勒",font=F(30),fill=GOLD_D)
    y=300; y=ct(d,W/2,y,"量回自己",F(150,True),GOLD); y+=40
    y=ct(d,W/2,y,"給總是覺得「不夠好」的你",F(48,True),CREAM); y+=24
    y=ct(d,W/2,y,"6 題溫柔的自我檢查",F(36),MUT); y+=66
    for ln in ["你不是不夠好，","只是拿錯了尺，","在量自己。"]:
        y=ct(d,W/2,y,ln,F(42,True),CREAM); y+=14
    try:
        av=Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw=300; sc=aw/av.width; av=av.resize((aw,int(av.height*sc)))
        img.paste(av,(int((W-aw)/2),H-av.height-118),av)
    except Exception as e: print(e)
    foot="向右滑，把尺拿回來 →"; fw=tw(d,foot,F(32,True))[0]
    d.text(((W-fw)/2,H-72),foot,font=F(32,True),fill=GOLD)
    img.save(f"{OUT}/p0.png")

def closing(idx,total):
    img=base(); d=ImageDraw.Draw(img); PAD=88
    d.text((PAD,70),"潔米爸的書房筆記 · 溫柔自我檢查",font=F(30),fill=MUT)
    num=f"{idx} / {total}"; nw=tw(d,num,F(30,True))[0]
    d.text((W-PAD-nw,70),num,font=F(30,True),fill=GOLD)
    d.line([PAD,128,W-PAD,128],fill=(60,48,30),width=2)
    y=230; y=ct(d,W/2,y,"最後，想對你說——",F(46,True),MUT); y+=90
    for ln in ["你一直都很努力，","只是太常用別人的尺，","來證明自己。"]:
        y=ct(d,W/2,y,ln,F(46),CREAM); y+=18
    y+=70
    bx=PAD; bw=W-2*PAD
    lines=["你不用變成","別人覺得的「夠好」，","只要慢慢變回","你自己想要的樣子，就好。"]
    cf=F(46,True); bh=64+sum(60 for _ in lines)
    rr(d,[bx,y,bx+bw,y+bh],26,fill=CARDBG,outline=GOLD,width=3)
    iy=y+36
    for i,ln in enumerate(lines):
        iy=ct(d,W/2,iy,ln,cf,GOLD if i>=2 else CREAM); iy+=14
    foot="潔米爸陪你量回自己 · @jamine_pa"; fw=tw(d,foot,F(30))[0]
    d.text(((W-fw)/2,H-78),foot,font=F(30),fill=MUT)
    img.save(f"{OUT}/p{idx}.png")

TOTAL=4
cover()
card(1,TOTAL,"先把尺看清楚",ITEMS[:3])
card(2,TOTAL,"對自己溫柔一點",ITEMS[3:])
closing(3,TOTAL)
print("done",sorted(os.listdir(OUT)))
