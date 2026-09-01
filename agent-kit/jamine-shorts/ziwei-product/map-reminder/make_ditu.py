# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont

FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/ditu"; os.makedirs(OUT,exist_ok=True)
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
    ct(d,W/2,86,"# 潔米爸的書房筆記",F(30),MUT)
    ct(d,W/2,128,"紫微斗數筆記",F(30,True),GOLDT)
    return img,d

# (num,標題,內文)
ITEMS=[
    ("01","地圖不是命令，是提醒","它只是告訴你哪裡有坡，不是叫你不能走。"),
    ("02","知道風險，不等於被限制","看懂哪裡需要慢，是為了走得更穩。"),
    ("03","真正的自由，是看見了還能自己選","知道路況，再決定怎麼走，主導權在你。"),
    ("04","只剩害怕的時候，先停下來","你不需要被任何一句話，嚇到失去自己。"),
    ("05","可以多問，也可以查證","把選擇權，留在自己身上。"),
    ("06","命盤看的是「傾向」，不是「結局」","怎麼走，永遠是你決定的。"),
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
    ct(d,W/2,H-118,"命盤是地圖，不是算命 · @jamine_pa",F(30),MUT)
    img.save(f"{OUT}/p{idx}.png")

def cover():
    img,d=base()
    y=ct(d,W/2,288,"命盤是地圖",F(108,True),INK); y+=14
    d.line([W/2-180,y+6,W/2+180,y+6],fill=FRAME,width=4); y+=44
    y=ct(d,W/2,y,"不是命令，是提醒",F(50,True),GOLDT); y+=66
    for ln in ["地圖告訴你哪裡有坡，","不是叫你，不能走。","","看盤前，先收好這 6 句。"]:
        if ln=="": y+=20; continue
        y=ct(d,W/2,y,ln,F(40),BODY); y+=16
    try:
        av=Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw=300; sc=aw/av.width; av=av.resize((aw,int(av.height*sc)))
        img.paste(av,(int((W-aw)/2),H-av.height-150),av)
    except Exception as e: print(e)
    ct(d,W/2,H-110,"向右滑，把主導權拿回來 →",F(32,True),GOLDT)
    img.save(f"{OUT}/p0.png")

def closing(idx,total):
    img,d=base()
    ct(d,W/2,300,"看懂路況，",F(56,True),INK)
    ct(d,W/2,374,"是為了走得更穩。",F(56,True),INK)
    y=510
    for ln in ["地圖會告訴你哪裡有坡、","哪裡要慢、哪裡別硬衝，","但要不要走、怎麼走──"]:
        y=ct(d,W/2,y,ln,F(40),BODY); y+=18
    y+=44
    bx=84; bw=W-2*84
    lines=["走法，","永遠是你決定的。"]
    boxh=64+70*len(lines)
    rr(d,[bx,y,bx+bw,y+boxh],26,fill=CELL,outline=FRAME,width=3)
    iy=y+34
    for i,ln in enumerate(lines):
        iy=ct(d,W/2,iy,ln,F(52,True),GOLDT if i==1 else INK); iy+=18
    ct(d,W/2,H-150,"一起把玄學，講得明亮一點",F(32,True),BODY)
    ct(d,W/2,H-104,"@jamine_pa",F(34,True),GOLDT)
    img.save(f"{OUT}/p{idx}.png")

TOTAL=4
cover()
card(1,TOTAL,"先把地圖看對",ITEMS[:3])
card(2,TOTAL,"把主導權拿回來",ITEMS[3:])
closing(3,TOTAL)
print("ok",sorted(os.listdir(OUT)))
