# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont
FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/contrast"; os.makedirs(OUT,exist_ok=True)
W,H=1080,1920
CBG=(245,240,231); INK=(40,36,30); BODY=(78,70,60); MUT=(150,140,124)
GOLD=(198,150,60); GOLDT=(176,132,56); FRAME=(208,184,142)
RED=(196,86,71); RED_BG=(244,228,222); RED_LN=(224,184,172)
GBG=(247,235,206); GLN=(224,200,150)

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
def xmark(d,cx,cy,r,col):
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=col)
    o=r*0.42
    d.line([cx-o,cy-o,cx+o,cy+o],fill=(255,255,255),width=8)
    d.line([cx-o,cy+o,cx+o,cy-o],fill=(255,255,255),width=8)
def vmark(d,cx,cy,r,col):
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=col)
    d.line([cx-r*0.45,cy+r*0.02,cx-r*0.08,cy+r*0.38],fill=(255,255,255),width=8)
    d.line([cx-r*0.08,cy+r*0.38,cx+r*0.5,cy-r*0.34],fill=(255,255,255),width=8)

def half(d,top,bot,kind,who,lines):
    # kind 'x' or 'v'
    bg=RED_BG if kind=='x' else GBG
    ln=RED_LN if kind=='x' else GLN
    acc=RED if kind=='x' else GOLD
    rr(d,[60,top,W-60,bot],28,fill=bg,outline=ln,width=2)
    cy=top+78
    if kind=='x': xmark(d,140,cy,42,acc)
    else: vmark(d,140,cy,42,acc)
    d.text((205,top+44),who,font=F(54,True),fill=acc)
    # vertically center quote block in lower region
    qf=F(40,True)
    rows=[]
    for L in lines:
        rows.extend(wrap(d,L,qf,W-200))
    blockh=len(rows)*56
    region_top=top+170; region_bot=bot-40
    ty=region_top+max(0,(region_bot-region_top-blockh)//2)
    for wl in rows:
        ct(d,W/2,ty,wl,qf,INK); ty+=56

def frame_dim(idx,num,dim,xlines,vlines):
    img,d=base()
    # dimension chip
    chip=f"{num}　{dim}"
    cf=F(58,True); cw=tw(d,chip,cf)[0]
    rr(d,[(W-cw)/2-46,128,(W+cw)/2+46,210],24,fill=(60,46,20))
    ct(d,W/2,142,chip,cf,(255,238,205))
    half(d,268,1000,'x',"菜鳥",xlines)
    ct(d,W/2,1012,"vs",F(40,True),MUT)
    half(d,1078,1810,'v',"踩坑老手",vlines)
    img.save(f"{OUT}/f{idx}.png")

def hook():
    img,d=base()
    y=ct(d,W/2,430,"一樣去算命",F(60,True),BODY); y+=40
    ct(d,W/2,y,"菜鳥",F(150,True),RED)
    ct(d,W/2,y+170,"vs",F(70,True),MUT)
    ct(d,W/2,y+270,"踩坑老手",F(150,True),GOLD)
    y2=y+480
    rr(d,[180,y2,W-180,y2+150],28,fill=(60,46,20))
    ct(d,W/2,y2+28,"帶走的東西，差 10 倍",F(50,True),(255,238,205))
    ct(d,W/2,y2+250,"差在 3 件事 👇",F(46,True),GOLDT) if False else ct(d,W/2,y2+250,"差在 3 件事",F(48,True),GOLDT)
    img.save(f"{OUT}/f0.png")

def closing():
    img,d=base()
    y=420
    y=ct(d,W/2,y,"差別不是誰聰明",F(56,True),BODY); y+=30
    y=ct(d,W/2,y,"是你把算命當",F(56,True),BODY); y+=80
    ct(d,W/2,y,"預言",F(130,True),RED)
    ct(d,W/2,y+170,"還是",F(48,True),MUT)
    ct(d,W/2,y+260,"地圖",F(130,True),GOLD)
    y2=y+470
    ct(d,W/2,y2,"命盤是地圖，不是算命。",F(46,True),INK)
    img.save(f"{OUT}/f4.png")

def slogan(name):
    img,d=base()
    try:
        av=Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw=360; sc=aw/av.width; av=av.resize((aw,int(av.height*sc)))
        img.paste(av,(int((W-aw)/2),470),av)
    except Exception as e: print(e)
    y=920
    ct(d,W/2,y,"潔米爸的書房筆記",F(46,True),MUT); y+=90
    ct(d,W/2,y,"陪你，看懂",F(86,True),INK); y+=110
    ct(d,W/2,y,"人生的方法",F(86,True),GOLD); y+=170
    # follow pill
    bw,bh=520,128; bx=(W-bw)/2
    rr(d,[bx,y,bx+bw,y+bh],30,fill=(60,46,20))
    ct(d,W/2,y+30,"追蹤 @jamine_pa",F(50,True),(255,238,205))
    y+=bh+50
    ct(d,W/2,y,"心理學 × 紫微 × 心流",F(38),MUT)
    img.save(f"{OUT}/{name}.png")

hook()
frame_dim(1,"①","問法",
          ["「我會不會發財？」","「他會不會回來？」","——要一個「預言」"],
          ["「我的狀況，哪個方向有機會？","要注意什麼？」","——要方向，還會先測老師"])
frame_dim(2,"②","切入角度",
          ["想知道「結局」","求一個保證","怕聽到壞的"],
          ["想要一張「地圖」","我強在哪、弱在哪","什麼時候適合做什麼"])
frame_dim(3,"③","後續應用",
          ["當下超準 → 過幾天忘","問題還在 → 又回去算","（越算越迷）"],
          ["當場變「行動清單」","回去驗證、調整","（越用越懂自己）"])
closing()
slogan("slogan")        # 片尾卡（也單獨當 deliverable）
print("ok",sorted(os.listdir(OUT)))
