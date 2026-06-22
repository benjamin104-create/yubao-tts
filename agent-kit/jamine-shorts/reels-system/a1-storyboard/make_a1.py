# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont
FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/a1"; os.makedirs(OUT,exist_ok=True)
W,H=1080,1920
CBG=(245,240,231); INK=(40,36,30); BODY=(78,70,60); MUT=(150,140,124)
GOLD=(198,150,60); GOLDT=(176,132,56); FRAME=(208,184,142)
CELL=(250,247,240); CELL_LN=(214,200,172); RED=(196,86,71)

def F(sz,b=False):
    f=ImageFont.truetype(FONT,sz)
    try: f.set_variation_by_axes([700 if b else 400])
    except: pass
    return f
def tw(d,t,f):
    bb=d.textbbox((0,0),t,font=f); return bb[2]-bb[0],bb[3]-bb[1]
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
def base():
    img=Image.new("RGB",(W,H),CBG); d=ImageDraw.Draw(img)
    rr(d,[28,28,W-28,H-28],30,outline=FRAME,width=3)
    ct(d,W/2,70,"# 潔米爸的書房筆記",F(30),MUT)
    return img,d
def chip(d,y,txt):
    cf=F(50,True); cw=tw(d,txt,cf)[0]
    rr(d,[(W-cw)/2-44,y,(W+cw)/2+44,y+86],26,fill=(60,46,20))
    ct(d,W/2,y+16,txt,cf,(255,238,205))
    return y+86

def hook():
    img,d=base()
    y=ct(d,W/2,440,"算命，別當乖乖牌",F(78,True),INK); y+=70
    y=ct(d,W/2,y,"花 20 萬學到的",F(46,True),BODY); y+=66
    y=ct(d,W/2,y,"「聰明質疑」",F(56,True),BODY); y+=120
    ct(d,W/2,y,"3 招",F(180,True),GOLD); y+=260
    y2=y+20
    rr(d,[200,y2,W-200,y2+130],28,fill=(60,46,20))
    ct(d,W/2,y2+30,"分得出大師，還是術士",F(46,True),(255,238,205))
    img.save(f"{OUT}/f0.png")

def method(idx,num,title,lines):
    img,d=base()
    y=chip(d,180,num); y+=70
    for ln in wrap(d,title,F(58,True),W-160):
        y=ct(d,W/2,y,ln,F(58,True),INK); y+=78
    y+=20
    d.line([W/2-120,y,W/2+120,y],fill=FRAME,width=4); y+=70
    # body box
    bf=F(42); rows=[]
    for L in lines: rows.extend(wrap(d,L,bf,W-200))
    bh=80+len(rows)*64
    rr(d,[90,y,W-90,y+bh],26,fill=CELL,outline=CELL_LN,width=2)
    iy=y+40
    for r in rows:
        ct(d,W/2,iy,r,bf,BODY); iy+=64
    img.save(f"{OUT}/f{idx}.png")

def tools():
    img,d=base()
    y=chip(d,180,"招 2"); y+=70
    y=ct(d,W/2,y,"先搞懂工具的守備範圍",F(56,True),INK); y+=110
    rows=[("八字","看大格局、一生方向"),("紫微","看細節、十二宮位"),("塔羅","看當下、近期心境"),("星座","看性格、傾向")]
    by=y; bh=150; gap=24
    for name,desc in rows:
        rr(d,[90,by,W-90,by+bh],24,fill=CELL,outline=CELL_LN,width=2)
        d.text((140,by+44),name,font=F(56,True),fill=GOLD)
        d.text((340,by+52),desc,font=F(40),fill=BODY)
        by+=bh+gap
    ct(d,W/2,by+24,"用對工具，才問得到對的答案",F(40,True),GOLDT)
    img.save(f"{OUT}/f2.png")

def closing():
    img,d=base()
    y=460
    y=ct(d,W/2,y,"質疑，不是找碴",F(64,True),INK); y+=110
    for ln in ["是為了找到","真正能幫你的人。"]:
        y=ct(d,W/2,y,ln,F(50,True),BODY); y+=70
    y+=80
    bx=90; bw=W-180; lines=["命盤是地圖，","不是算命。"]
    boxh=70+len(lines)*78
    rr(d,[bx,y,bx+bw,y+boxh],26,fill=CELL,outline=FRAME,width=3)
    iy=y+40
    for i,ln in enumerate(lines):
        iy=ct(d,W/2,iy,ln,F(58,True),GOLD if i==1 else INK); iy+=78
    img.save(f"{OUT}/f4.png")

hook()
method(1,"招 1","拿「你已知答案的事」去問",
       ["把過去發生過、結果你很清楚","的事，套進問題裡。","","說得出來＝真看得到；","說不出來＝你心裡就有數了。"])
tools()
method(3,"招 3","追問「影響的因素是什麼」",
       ["別只聽「什麼時候好、不好」。","要問：影響的因素是什麼？","我可以做什麼？","","要能動手的變因，不是宿命結論。"])
closing()
print("ok",sorted(os.listdir(OUT)))
