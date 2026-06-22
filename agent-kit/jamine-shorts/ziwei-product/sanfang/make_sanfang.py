# -*- coding: utf-8 -*-
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT="/tmp/NotoSansTC.ttf"; OUT="/tmp/hfdemo/sanfang"; os.makedirs(OUT,exist_ok=True)
W,H=1080,1350
CBG=(244,239,228); FRAME=(201,170,112); INK=(40,36,30); GOLDT=(176,132,56)
BODY=(78,70,60); MUT=(150,140,124)
CELL=(250,247,240); CELL_LINE=(210,198,172); CENTER=(238,231,216)
H_BEN=(224,162,78); H_SAN=(242,214,160); H_DUI=(226,219,200)
LINE_SAN=(196,148,66); LINE_DUI=(150,120,72)

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
def base(header2="紫微斗數筆記"):
    img=Image.new("RGB",(W,H),CBG); d=ImageDraw.Draw(img)
    rr(d,[26,26,W-26,H-26],28,outline=FRAME,width=3)
    rr(d,[40,40,W-40,H-40],22,outline=(220,200,160),width=1)
    ct(d,W/2,86,"# 潔米爸的書房筆記",F(30),MUT)
    ct(d,W/2,128,header2,F(30,True),GOLDT)
    return img,d
def dash(d,p1,p2,col,w=5,da=22,gap=14):
    x1,y1=p1;x2,y2=p2;dx=x2-x1;dy=y2-y1;dist=math.hypot(dx,dy)
    if dist==0:return
    ux,uy=dx/dist,dy/dist;s=0
    while s<dist:
        e=min(s+da,dist);d.line([x1+ux*s,y1+uy*s,x1+ux*e,y1+uy*e],fill=col,width=w);s+=da+gap

def diagram():
    img,d=base()
    ct(d,W/2,188,"一張圖看懂",F(36,True),BODY)
    ct(d,W/2,232,"三方四正",F(76,True),INK)
    ct(d,W/2,338,"一宮不單看，要連著相關的宮一起看",F(31),GOLDT)
    ct(d,W/2,388,"三方＝兩個三合宮　｜　四正＝再加對宮",F(28,True),(150,118,52))

    # grid
    cell=166; gx=(W-cell*4)//2; gy=452
    ring=[(0,0),(0,1),(0,2),(0,3),(1,3),(2,3),(3,3),(3,2),(3,1),(3,0),(2,0),(1,0)]
    palaces=['命宮','兄弟','夫妻','子女','財帛','疾厄','遷移','交友','官祿','田宅','福德','父母']
    pos2pal={}
    for k in range(12): pos2pal[ring[(6+k)%12]]=palaces[k]
    hi={(3,3):('本宮',H_BEN),(2,0):('三合',H_SAN),(0,2):('三合',H_SAN),(0,0):('對宮',H_DUI)}
    def cen(r,c): return (gx+c*cell+cell//2, gy+r*cell+cell//2)
    cb=[gx+cell,gy+cell,gx+3*cell,gy+3*cell]
    # pass1: cell fills
    for (r,c),pal in pos2pal.items():
        x0,y0=gx+c*cell,gy+r*cell
        fill=CELL
        if (r,c) in hi: fill=hi[(r,c)][1]
        rr(d,[x0+4,y0+4,x0+cell-4,y0+cell-4],14,fill=fill,outline=CELL_LINE,width=2)
    # center: empty light panel (no text, so lines stay clear)
    rr(d,cb,18,fill=CENTER,outline=FRAME,width=2)
    # pass2: non-highlighted labels (drawn before lines; lines barely touch them)
    for (r,c),pal in pos2pal.items():
        if (r,c) in hi: continue
        cx,cy=cen(r,c); ct(d,cx,cy-24,pal,F(44,True),(120,110,96))
    # pass3: connecting lines ON TOP (always visible over the empty center)
    A=cen(3,3); Bp=cen(2,0); Cp=cen(0,2); Dp=cen(0,0)
    for p,q in [(A,Bp),(Bp,Cp),(Cp,A)]:
        d.line([p[0],p[1],q[0],q[1]],fill=LINE_SAN,width=7)
    dash(d,A,Dp,LINE_DUI,w=7,da=24,gap=14)
    # pass4: highlighted role chips + names (on top of lines, stay readable)
    for (r,c),(role,col) in hi.items():
        x0,y0=gx+c*cell,gy+r*cell; cx,cy=cen(r,c); ben=(role=='本宮'); pal=pos2pal[(r,c)]
        rw,_=tw(d,role,F(24,True))
        rr(d,[cx-rw/2-13,y0+16,cx+rw/2+13,y0+16+36],11,fill=(60,42,16) if ben else (255,255,255))
        ct(d,cx,y0+19,role,F(24,True),(255,238,205) if ben else GOLDT)
        ct(d,cx,cy+4,pal,F(48,True),(54,36,12) if ben else INK)
    # legend: left = color swatches, right = line styles
    ly0=gy+cell*4+32; lf=F(28,True)
    lx=gx+6; ly=ly0
    for txt,col in [("本宮 你要看的那件事",H_BEN),("三方 兩個三合宮",H_SAN),("對宮 正對面那一宮",H_DUI)]:
        rr(d,[lx,ly,lx+32,ly+32],8,fill=col,outline=CELL_LINE,width=2)
        d.text((lx+44,ly-1),txt,font=lf,fill=BODY); ly+=52
    rx=gx+cell*2+40; ry=ly0+8
    d.line([rx,ry+16,rx+58,ry+16],fill=LINE_SAN,width=7); d.text((rx+72,ry),"三合連線",font=lf,fill=BODY)
    dash(d,(rx,ry+90),(rx+58,ry+90),LINE_DUI,w=7,da=16,gap=10); d.text((rx+72,ry+74),"對宮連線",font=lf,fill=BODY)
    img.save(f"{OUT}/p1.png")

def cover():
    img,d=base()
    y=ct(d,W/2,300,"三方四正",F(118,True),INK); y+=20
    d.line([W/2-170,y+8,W/2+170,y+8],fill=FRAME,width=4); y+=44
    y=ct(d,W/2,y,"一張圖，看懂這個紫微名詞",F(44,True),GOLDT); y+=70
    for ln in ["不是把某一宮","孤零零拿出來判斷，","而是連著相關的宮，","一起看「牽動」。"]:
        y=ct(d,W/2,y,ln,F(40),BODY); y+=18
    try:
        av=Image.open("/tmp/hfdemo/demo/ip_avatar_clean.png").convert("RGBA")
        aw=300; sc=aw/av.width; av=av.resize((aw,int(av.height*sc)))
        img.paste(av,(int((W-aw)/2),H-av.height-150),av)
    except Exception as e: print(e)
    ct(d,W/2,H-110,"向右滑，一張圖看懂 →",F(32,True),GOLDT)
    img.save(f"{OUT}/p0.png")

def example():
    img,d=base()
    ct(d,W/2,200,"用「命宮」當例子",F(64,True),INK)
    ct(d,W/2,300,"看「你這個人」，要連著這四宮一起看",F(33),GOLDT)
    rows=[("本宮","命宮","你這個人、你的個性",H_BEN,True),
          ("三合","財帛宮","你怎麼賺錢、怎麼用錢",H_SAN,False),
          ("三合","官祿宮","你的工作、事業、定位",H_SAN,False),
          ("對宮","遷移宮","你在外面、別人眼中的你",H_DUI,False)]
    PAD=92; y=400; bh=178; gap=26; bf=F(38)
    for role,pal,desc,col,ben in rows:
        rr(d,[PAD,y,W-PAD,y+bh],22,fill=(250,247,240),outline=CELL_LINE,width=2)
        # role chip
        rr(d,[PAD+34,y+34,PAD+34+118,y+34+50],14,fill=(60,42,16) if ben else col)
        ct(d,PAD+34+59,y+40,role,F(30,True),(255,238,205) if ben else (90,66,24))
        d.text((PAD+180,y+32),pal,font=F(46,True),fill=INK)
        d.text((PAD+34,y+104),desc,font=bf,fill=BODY)
        y+=bh+gap
    ct(d,W/2,y+10,"這四宮會互相影響，一起看才準。",F(34,True),GOLDT)
    img.save(f"{OUT}/p2.png")

def takeaway():
    img,d=base()
    ct(d,W/2,196,"潔米爸怎麼看",F(38,True),BODY)
    ct(d,W/2,250,"它更像「磁場關係學」",F(58,True),INK)
    y=358
    for ln in ["紫微斗數，","不是單一宮位就能看出全貌。","它講的是「關係」──","相關的宮，怎麼互相影響一件事。"]:
        y=ct(d,W/2,y,ln,F(38),BODY); y+=14
    y+=34
    # three points
    pts=[("看得到「助力」與要「小心」的地方","哪邊有人事物在幫你，哪邊要多留意。"),
         ("看得到你心裡更在乎什麼","同一件事，你真正放不下的，往往會浮出來。"),
         ("看得到事情可能怎麼發展","不是定死的結局，是幾種走向與機會。")]
    PAD=84; bh=148; gap=22; bf=F(32)
    for t,s in pts:
        rr(d,[PAD,y,W-PAD,y+bh],20,fill=(250,247,240),outline=CELL_LINE,width=2)
        d.text((PAD+34,y+28),"｜ "+t,font=F(35,True),fill=INK)
        for i,ln in enumerate(wrap(d,s,bf,W-2*PAD-68)):
            d.text((PAD+34,y+86+i*42),ln,font=bf,fill=BODY)
        y+=bh+gap
    y+=10
    ct(d,W/2,y,"所以別用一格定生死──",F(36,True),GOLDT)
    ct(d,W/2,y+50,"看「關係」，才看得到全貌。",F(36,True),GOLDT)
    ct(d,W/2,H-150,"用更明亮的方式看命盤",F(32,True),BODY)
    ct(d,W/2,H-106,"@jamine_pa",F(34,True),GOLDT)
    img.save(f"{OUT}/p3.png")

cover()
diagram()
example()
takeaway()
print("ok",sorted(os.listdir(OUT)))
