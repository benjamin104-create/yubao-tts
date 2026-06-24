# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont
FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/quiz"; os.makedirs(OUT,exist_ok=True)
W,H=1080,1350
CBG=(245,240,231); INK=(40,36,30); BODY=(78,70,60); MUT=(150,140,124)
GOLD=(198,150,60); GOLDT=(176,132,56); FRAME=(208,184,142)
CELL=(250,247,240); CELL_LN=(214,200,172)
def F(s,b=False):
    f=ImageFont.truetype(FONT,s)
    try: f.set_variation_by_axes([700 if b else 400])
    except: pass
    return f
def tw(d,t,f):
    bb=d.textbbox((0,0),t,font=f); return bb[2]-bb[0],bb[3]-bb[1]
def ct(d,cx,y,t,f,fl):
    w,h=tw(d,t,f); d.text((cx-w/2,y),t,font=f,fill=fl); return y+h
def wrap(d,t,f,mw):
    L,c=[],""
    for ch in t:
        if ch=="\n": L.append(c);c="";continue
        if tw(d,c+ch,f)[0]>mw and c: L.append(c);c=ch
        else: c+=ch
    if c:L.append(c)
    return L
def rr(d,b,r,**k): d.rounded_rectangle(b,radius=r,**k)
def base(tag):
    img=Image.new("RGB",(W,H),CBG); d=ImageDraw.Draw(img)
    rr(d,[26,26,W-26,H-26],28,outline=FRAME,width=3)
    ct(d,W/2,64,"# 潔米爸的書房筆記",F(28),MUT)
    ct(d,W/2,104,tag,F(28,True),GOLDT)
    return img,d

# ---- S6 測驗頁
img,d=base("直覺小測驗")
y=210
for ln in ["最近，你的能量","卡在哪一塊？"]:
    y=ct(d,W/2,y,ln,F(64,True),INK); y+=20
y+=40
y=ct(d,W/2,y,"憑直覺，選一個數字",F(40),BODY); y+=80
# number panel
nums=["13","27","38","46"]
pw=W-160; px=80; ph=150
rr(d,[px,y,px+pw,y+ph],28,fill=(60,46,20))
step=pw/len(nums)
for i,n in enumerate(nums):
    cx=px+step*i+step/2
    nw,nh=tw(d,n,F(76,True))
    d.text((cx-nw/2,y+ph/2-nh/2-6),n,font=F(76,True),fill=(255,238,205))
y+=ph+70
# CTA
rr(d,[120,y,W-120,y+128],26,fill=CELL,outline=GOLD,width=3)
ct(d,W/2,y+24,"底下留言「能量」",F(46,True),INK)
ct(d,W/2,y+78,"我把你的狀態私訊給你",F(34),BODY)
y+=128+40
ct(d,W/2,y,"※ 測的不是命，是你現在最在意的事",F(28),MUT)
ct(d,W/2,H-86,"命盤是地圖，不是算命 · @jamine_pa",F(28),MUT)
img.save(f"{OUT}/s6_test.png")

# ---- 答案卡
TYPES=[
    ("13","蓄力型","你不是沒動力，是身體在叫你先充電。","休息 · 囤積 · 等時機"),
    ("27","卡關型","卡住你的不是事情，是還沒鬆開的情緒。","內耗 · 糾結 · 放下"),
    ("38","轉運型","你正在一個悄悄上升的節點，別急著否定自己。","轉機 · 貴人 · 開始"),
    ("46","擴張型","能量很滿，但小心別過度燃燒。","行動 · 機會 · 節制"),
]
img,d=base("你的能量狀態")
ct(d,W/2,168,"憑直覺選的數字，藏著你現在的狀態",F(34),BODY)
y=240; bh=235; gap=20; PAD=70
for n,name,desc,kw in TYPES:
    rr(d,[PAD,y,W-PAD,y+bh],22,fill=CELL,outline=CELL_LN,width=2)
    d.text((PAD+34,y+30),n,font=F(64,True),fill=GOLD)
    d.text((PAD+150,y+44),name,font=F(46,True),fill=INK)
    dy=y+118
    for ln in wrap(d,desc,F(34),W-2*PAD-70):
        d.text((PAD+34,dy),ln,font=F(34),fill=BODY); dy+=46
    d.text((PAD+34,y+bh-50),"關鍵字："+kw,font=F(31,True),fill=GOLDT)
    y+=bh+gap
ct(d,W/2,H-78,"想真的看懂為什麼？命盤是地圖 · @jamine_pa",F(28),MUT)
img.save(f"{OUT}/answer.png")
print("ok",sorted(os.listdir(OUT)))
