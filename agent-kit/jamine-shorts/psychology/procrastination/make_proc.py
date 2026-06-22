# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/proc"; os.makedirs(OUT,exist_ok=True)
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

# (number, 心法, 怎麼做)
METHODS=[
    ("01","先求開始，不求做完","久沒運動別急著跑步，先「走路」就好。事情也一樣，今天只要碰一下，就算數。"),
    ("02","綁在每天都要做的事旁邊","把想做的事，黏在刷牙、通勤、吃飯後，借你現成的慣性，帶它一起動。"),
    ("03","份量小到不會抗拒，再慢慢加","起步寧可少到「這也太簡單」。先動起來，份量自然加得上去。"),
    ("04","每天碰一下，勝過一次做好","慣性比意志力可靠。連續碰幾天，習慣就會自己回來幫你。"),
    ("05","催眠自己這一句","「只要開始，哪怕一點點，事情就在被解決了。」"),
    ("06","看清「不做」的代價","你越不碰，它不會消失，只會每天多壓你一點。多擱一件，心裡就多一塊石頭。"),
]

def method_card(idx,total,title,group):
    img=base(); d=ImageDraw.Draw(img); PAD=80
    d.text((PAD,70),"潔米爸的書房筆記 · 先動起來",font=F(30),fill=MUT)
    num=f"{idx} / {total}"; nw=tw(d,num,F(30,True))[0]
    d.text((W-PAD-nw,70),num,font=F(30,True),fill=GOLD)
    d.line([PAD,128,W-PAD,128],fill=(60,48,30),width=2)
    y=176; d.text((PAD,y),title,font=F(50,True),fill=GOLD); y+=100
    tf=F(41,True); bf=F(33); QW=W-2*PAD-76
    PADT=30; THG=8; TIT_H=52; B_LH=46; PADB=30
    heights=[]
    for n_,h_,body in group:
        bl=wrap(d,body,bf,QW)
        heights.append(PADT+TIT_H+THG+B_LH*len(bl)+PADB)
    tot=sum(heights)+34*(len(group)-1)
    slack=(H-110)-y-tot
    top=y+min(50,max(0,slack/2))
    for (n_,h_,body),bh in zip(group,heights):
        rr(d,[PAD,top,W-PAD,top+bh],24,fill=CARDBG,outline=(54,42,26),width=2)
        # number chip
        d.text((PAD+38,top+PADT+4),n_,font=F(30,True),fill=GOLD_D)
        d.text((PAD+38+60,top+PADT-2),h_,font=tf,fill=CREAM)
        iy=top+PADT+TIT_H+THG
        for ln in wrap(d,body,bf,QW):
            d.text((PAD+38,iy),ln,font=bf,fill=MUT); iy+=B_LH
        top+=bh+34
    foot="先動，哪怕一點點 · @jamine_pa"; fw=tw(d,foot,F(30))[0]
    d.text(((W-fw)/2,H-70),foot,font=F(30),fill=MUT)
    img.save(f"{OUT}/p{idx}.png")

def cover():
    img=base(); d=ImageDraw.Draw(img); PAD=80
    d.text((PAD,90),"潔米爸的書房筆記",font=F(34),fill=MUT)
    d.text((PAD,138),"心理學 · 拖延 · 行動力",font=F(30),fill=GOLD_D)
    y=290; y=ct(d,W/2,y,"先動起來",F(150,True),GOLD); y+=40
    y=ct(d,W/2,y,"給總是拖到最後的你",F(50,True),CREAM); y+=24
    y=ct(d,W/2,y,"6 個把「開始」變簡單的方法",F(36),MUT); y+=66
    for ln in ["不是逼自己一次做完，","是先把「動起來」的慣性，","慢慢找回來。"]:
        y=ct(d,W/2,y,ln,F(42,True),CREAM); y+=14
    try:
        av=Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw=300; sc=aw/av.width; av=av.resize((aw,int(av.height*sc)))
        img.paste(av,(int((W-aw)/2),H-av.height-118),av)
    except Exception as e: print(e)
    foot="向右滑，走出第一步 →"; fw=tw(d,foot,F(32,True))[0]
    d.text(((W-fw)/2,H-72),foot,font=F(32,True),fill=GOLD)
    img.save(f"{OUT}/p0.png")

def closing(idx,total):
    img=base(); d=ImageDraw.Draw(img); PAD=88
    d.text((PAD,70),"潔米爸的書房筆記 · 先動起來",font=F(30),fill=MUT)
    num=f"{idx} / {total}"; nw=tw(d,num,F(30,True))[0]
    d.text((W-PAD-nw,70),num,font=F(30,True),fill=GOLD)
    d.line([PAD,128,W-PAD,128],fill=(60,48,30),width=2)
    y=178; d.text((PAD,y),"潔米爸的真心話",font=F(46,True),fill=GOLD); y+=96
    story=["我也曾經很久沒運動，","久到光是「開始」這兩個字，","想到心裡就有滿滿的抗拒。","","後來身體被逼急了，","我才硬著頭皮，從「走路」開始──","因為那是我每天反正都要做的事。","","動起來之後，份量才慢慢加得上去，","那個失蹤好久的習慣，","竟然一點一點，自己回來了。"]
    sf=F(38)
    for ln in story:
        if ln=="": y+=22; continue
        y=ct(d,W/2,y,ln,sf,CREAM); y+=14
    y+=36
    # core box
    bx=PAD; bw=W-2*PAD
    lines=["不是先有動力才行動，","是先行動，","動力跟習慣，才會慢慢長回來。"]
    cf=F(44,True); bh=60+sum(54 for _ in lines)
    rr(d,[bx,y,bx+bw,y+bh],26,fill=CARDBG,outline=GOLD,width=3)
    iy=y+34
    for i,ln in enumerate(lines):
        iy=ct(d,W/2,iy,ln,cf,GOLD if i>=1 else CREAM); iy+=12
    foot="先動，哪怕一點點 · @jamine_pa"; fw=tw(d,foot,F(30))[0]
    d.text(((W-fw)/2,H-72),foot,font=F(30),fill=MUT)
    img.save(f"{OUT}/p{idx}.png")

TOTAL=4
cover()
method_card(1,TOTAL,"先把門檻降到最低",METHODS[:3])
method_card(2,TOTAL,"讓慣性回來幫你",METHODS[3:])
closing(3,TOTAL)
print("done",sorted(os.listdir(OUT)))
