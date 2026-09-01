# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont

FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/caibo"; os.makedirs(OUT,exist_ok=True)
W,H=1080,1350
CBG=(244,239,228); FRAME=(201,170,112); INK=(40,36,30); GOLDT=(176,132,56)
BODY=(78,70,60); MUT=(150,140,124); CELL=(250,247,240); CELL_LINE=(210,198,172)
H_GOLD=(224,162,78)

def F(sz,bold=False):
    f=ImageFont.truetype(FONT,sz)
    try: f.set_variation_by_axes([700 if bold else 400])
    except: pass
    return f
def tw(d,t,f):
    b=d.textbbox((0,0),t,font=f); return b[2]-b[0],b[3]-b[1]
def ct(d,cx,y,t,f,fill):
    w,h=tw(d,t,f); d.text((cx-w/2,y),t,font=f,fill=fill); return y+h
def rr(d,b,r,fill=None,outline=None,width=1): d.rounded_rectangle(b,radius=r,fill=fill,outline=outline,width=width)
def wrap(d,t,f,mw):
    L,c=[],""
    for ch in t:
        if tw(d,c+ch,f)[0]>mw and c: L.append(c);c=ch
        else: c+=ch
    if c:L.append(c)
    return L
def base():
    img=Image.new("RGB",(W,H),CBG); d=ImageDraw.Draw(img)
    rr(d,[26,26,W-26,H-26],28,outline=FRAME,width=3)
    rr(d,[40,40,W-40,H-40],22,outline=(220,200,160),width=1)
    ct(d,W/2,90,"# 潔米爸的書房筆記",F(25),MUT)
    ct(d,W/2,128,"紫微斗數筆記",F(28,True),GOLDT)
    return img,d

# (num,標題,內文)
ITEMS=[
    ("01","你會不會「不敢收」？","機會來了卻先退，也許是還不相信自己值得。"),
    ("02","賺到了，還是怕不夠？","怕的常常不是數字，是怕失去依靠。"),
    ("03","會用「成就」證明自己值得嗎？","你的價值，不需要業績來背書。"),
    ("04","我最怕失去的，是什麼？","把它說清楚，焦慮就會少一塊。"),
    ("05","我在哪裡，最想穩下來？","找到那個點，錢才有方向。"),
    ("06","我需要什麼，才覺得有依靠？","有時候要的不是更多錢，是被在乎。"),
]

def card(idx,total,title,group):
    img,d=base()
    ct(d,W/2,196,title,F(50,True),INK)
    d.line([W/2-130,272,W/2+130,272],fill=FRAME,width=3)
    tf=F(38,True); bf=F(33); PAD=84; QW=W-2*PAD-60
    PADT=28; NUM_H=44; TIT_LH=54; THG=8; B_LH=46; PADB=30
    heights=[]
    for n_,h_,body in group:
        tl=len(wrap(d,h_,tf,QW)); bl=len(wrap(d,body,bf,QW))
        heights.append(PADT+NUM_H+tl*TIT_LH+THG+bl*B_LH+PADB)
    tot=sum(heights)+30*(len(group)-1)
    y=320; slack=(H-130)-y-tot; top=y+min(150,max(0,slack/2))
    for (n_,h_,body),bh in zip(group,heights):
        rr(d,[PAD,top,W-PAD,top+bh],22,fill=CELL,outline=CELL_LINE,width=2)
        iy=top+PADT
        ct(d,W/2,iy,n_,F(28,True),GOLDT); iy+=NUM_H
        for ln in wrap(d,h_,tf,QW):
            ct(d,W/2,iy,ln,tf,INK); iy+=TIT_LH
        iy+=THG
        for ln in wrap(d,body,bf,QW):
            ct(d,W/2,iy,ln,bf,BODY); iy+=B_LH
        top+=bh+30
    ct(d,W/2,H-112,"錢的背後，是安全感 · @jamine_pa",F(25),MUT)
    img.save(f"{OUT}/p{idx}.png")

def cover():
    img,d=base()
    y=ct(d,W/2,278,"錢，不只是錢",F(102,True),INK); y+=14
    d.line([W/2-185,y+6,W/2+185,y+6],fill=FRAME,width=4); y+=44
    y=ct(d,W/2,y,"財帛宮，其實在問「安全感」",F(46,True),GOLDT); y+=64
    for ln in ["它問的不只是你賺多少，","是你怎麼面對資源與價值。","","6 個關於金錢與安全感的","自我觀察。"]:
        if ln=="": y+=18; continue
        y=ct(d,W/2,y,ln,F(40),BODY); y+=14
    try:
        av=Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw=290; sc=aw/av.width; av=av.resize((aw,int(av.height*sc)))
        img.paste(av,(int((W-aw)/2),H-av.height-138),av)
    except Exception as e: print(e)
    ct(d,W/2,H-104,"向右滑，看見你的安全感 →",F(32,True),GOLDT)
    img.save(f"{OUT}/p0.png")

def closing(idx,total):
    img,d=base()
    ct(d,W/2,300,"不是每個焦慮，",F(54,True),INK)
    ct(d,W/2,372,"都能用收入解決。",F(54,True),INK)
    y=508
    for ln in ["有些人賺得更多，還是怕不夠，","因為怕的不是數字，","是怕失去依靠。"]:
        y=ct(d,W/2,y,ln,F(40),BODY); y+=18
    y+=44
    bx=84; bw=W-2*84
    lines=["先看見害怕，","才知道怎麼穩。"]
    boxh=64+70*len(lines)
    rr(d,[bx,y,bx+bw,y+boxh],26,fill=CELL,outline=FRAME,width=3)
    iy=y+34
    for i,ln in enumerate(lines):
        iy=ct(d,W/2,iy,ln,F(52,True),GOLDT if i==1 else INK); iy+=18
    ct(d,W/2,H-150,"安全感被看見，心會比較不急",F(32,True),BODY)
    ct(d,W/2,H-104,"@jamine_pa",F(34,True),GOLDT)
    img.save(f"{OUT}/p{idx}.png")

TOTAL=4
cover()
card(1,TOTAL,"先看見金錢的焦慮",ITEMS[:3])
card(2,TOTAL,"再把安全感找回來",ITEMS[3:])
closing(3,TOTAL)
print("ok",sorted(os.listdir(OUT)))
