# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import img2pdf
FONT="/etc/alternatives/fonts-japanese-gothic.ttf"
W,H=1450,2050
BG=(13,10,7); CREAM=(231,221,204); GOLD=(224,162,78); MUT=(165,154,133); WHITE=(245,239,230)
MX=120; TOP=150; BOT=H-150
def F(sz): return ImageFont.truetype(FONT,sz)
_d=ImageDraw.Draw(Image.new("RGB",(10,10)))
def tw(t,f): return _d.textlength(t,font=f)
def wrap(text,font,maxw):
    lines=[]; line=""
    for ch in text:
        if ch=="\n": lines.append(line); line=""; continue
        if tw(line+ch,font)>maxw: lines.append(line); line=ch
        else: line+=ch
    if line or not lines: lines.append(line)
    return lines
records=[]  # (section, path)
counter=[0]
class Pg:
    def __init__(s,section):
        s.section=section; s.img=Image.new("RGB",(W,H),BG); s.d=ImageDraw.Draw(s.img); s.y=TOP
        s.d.text((MX,70),section,font=F(28),fill=MUT); s.d.line((MX,118,W-MX,118),fill=(60,50,36),width=2)
    def finish(s):
        counter[0]+=1; n=counter[0]
        s.d.line((MX,BOT+40,W-MX,BOT+40),fill=(50,42,30),width=2)
        s.d.text((MX,BOT+58),"進階紫微筆記 · 第1部",font=F(24),fill=MUT)
        s.d.text((W-MX-30,BOT+58),str(n),font=F(26),fill=MUT)
        p="/tmp/book_%02d.png"%n; s.img.save(p); records.append((s.section,p))
cur=[None]; section=[""]
def newpage():
    if cur[0] is not None: cur[0].finish()
    cur[0]=Pg(section[0])
def ensure(extra):
    if cur[0] is None or cur[0].y+extra>BOT: newpage()
def H1(t):
    ensure(120); p=cur[0]; p.d.text((MX,p.y),t,font=F(60),fill=GOLD); p.y+=106
def H2(t):
    ensure(86); p=cur[0]; p.d.rectangle((MX,p.y+6,MX+10,p.y+50),fill=GOLD); p.d.text((MX+28,p.y),t,font=F(42),fill=WHITE); p.y+=82
def P(t):
    f=F(34)
    for ln in wrap(t,f,W-2*MX):
        ensure(54); cur[0].d.text((MX,cur[0].y),ln,font=f,fill=CREAM); cur[0].y+=54
    cur[0].y+=10
def B(t):
    f=F(34); ls=wrap(t,f,W-2*MX-44)
    for i,ln in enumerate(ls):
        ensure(54); p=cur[0]
        if i==0: p.d.ellipse((MX+4,p.y+18,MX+18,p.y+32),fill=GOLD)
        p.d.text((MX+44,p.y),ln,font=f,fill=CREAM); p.y+=54
    cur[0].y+=6
def KV(k,v):
    f=F(33); kf=F(34); vx=MX+330; vw=W-MX-vx; vls=wrap(v,f,vw); need=max(1,len(vls))*52
    ensure(need+14); p=cur[0]; p.d.text((MX,p.y),k,font=kf,fill=GOLD)
    for ln in vls: p.d.text((vx,p.y),ln,font=f,fill=CREAM); p.y+=52
    p.d.line((MX,p.y+4,W-MX,p.y+4),fill=(40,34,24),width=1); p.y+=16
def NOTE(t):
    f=F(32); ls=wrap(t,f,W-2*MX-60); hgt=24+len(ls)*46+24
    ensure(hgt); p=cur[0]; p.d.rounded_rectangle((MX,p.y,W-MX,p.y+hgt),14,fill=(30,24,14),outline=GOLD)
    yy=p.y+24
    for ln in ls: p.d.text((MX+30,yy),ln,font=f,fill=GOLD); yy+=46
    p.y=yy+24
def SECTION(name): section[0]=name; newpage()

SECTION("使用說明")
H1("怎麼用這份筆記")
B("先找出命盤的 命宮、財帛宮、官祿宮 三宮主星。")
B("先看「這宮在看什麼」抓方向，再看主星與四化細節。")
B("命財官是「三合宮」（互相影響），三宮一起看，別單看一宮下定論。")
B("看到「煞」「忌」先別緊張——那是要注意/要練習的地方，不是判決。")
NOTE("命盤不是算命，是一張地圖。我不斷你的命，是陪你看懂自己、把主導權拿回來。")

SECTION("命宮")
H1("命宮 — 你的人生主場")
P("命宮＝天生個性底色與人生大方向；身宮＝35~40歲後顯現的後天性格。兩者一起看，才看得出先天與後天、年輕與中晚年的強弱。")
H2("格局速看")
KV("機月同梁","人生平順、安穩，適合規律安定型工作。")
KV("殺破狼·公家格","不宜一成不變，適合刑警、消防等變動挑戰型。")
P("命格高（擎羊/七殺/武曲坐命）→高官將士；命格低→保全、屠宰。")
P("醫學命格：命宮（三方 or 身宮）有左輔右弼（怕見血）；擎羊、天刑→可進行手術。")
H2("換工作怎麼看")
B("大限夫官線有化忌 → 這10年大限會換工作或改行。")
B("流年夫官線煞忌引動，或流年走入夫官線。")
B("運走夫官線時，小限、太歲進官祿宮＋四化或煞吉引動 → 升遷或調動。")
B("官祿宮有祿、權 → 工作忙碌、兼差雙職、變動。")
H2("命宮 × 身宮（一生強弱）")
KV("命強身強","命好，運勢低潮也能待好轉再起。")
KV("命強身弱","年輕運勢佳，老來辛、難享清福。")
KV("命弱身強","少年辛苦磨練，中晚年有一片天。")
KV("命弱身弱","命格不佳，易大起大落、一生不得志。")

SECTION("財帛宮")
H1("財帛宮 — 你怎麼來錢、留不留得住")
P("財帛宮＝賺錢方式與態度。能不能留住錢看田宅宮（財庫），財源從哪來看福德宮。三者一起看才完整。")
H2("田宅宮 ＝ 祖產 & 財庫")
P("祖產：天同/天梁坐命→承祖業；巨門化忌在田宅、子女化忌→無祖產靠自己；煞坐命/殺破狼→白手起家；天姚、地空入田宅→祖產無緣。")
P("財庫（有財無庫解法：買房地產、親友代管）：財帛>田宅→現金多、表面風光；財帛<田宅→現金少但有土地房產、口袋深。")
H2("賺錢管道（主星）")
KV("巨門","靠口才；化祿→業務、律師、主持、仲介。")
KV("貪狼","吃喝玩樂、旅遊娛樂、夜店；女性商品如化妝品。")
KV("天機","批發盤商；特殊專業技術。")
KV("太陽","旺地富貴；陷地偏財；旺地辛勞累積之財。")
KV("天同","輕鬆得財；繼承家產或晚發財。")
KV("廉貞","旺地富足；公門之財或加工技術財。")
KV("天相","服務/公家政府之財；銀行交易之財。")
KV("天梁","賭博、長輩處得財；理論之財或宗教財。")
KV("七殺","一夜致富，也可能因不慎毀於一旦。")
KV("破軍","廟旺富足；變賣家產、典當、討回欠債之財。")
KV("擎羊","屬金主財；會武曲七殺得紫府廟合→暴富暴落。")
H2("財運組合（財 × 福 × 田）")
KV("財旺＋福旺","有錢人。")
KV("財旺＋福弱","中產階級，有穩定收入，財源不旺。")
KV("財旺＋福弱＋田旺","原生條件不佳，靠自己打拼得財。")
KV("財弱＋福旺","經手很多錢但左進右出、沒留住。")
KV("財弱＋福弱","不以賺錢為目的，條件不佳但內心富足。")
KV("財弱＋福弱＋田旺","賺錢不易但守得住、會累積不少財富。")
H2("各主星理財風格（摘）")
KV("紫微","工作穩定、消費檔次高；+煞→橫財暴起暴落。")
KV("武曲","入廟不缺錢、善資金調度；遇空劫→買不動產。")
KV("天府","財庫、家境富裕、擅理財。")
KV("太陰","旺地逢祿→富足、重資產適合不動產；遇煞忌→當心詐騙。")
KV("天機","喜投機（股票期貨）；逢煞→財來財去。")

SECTION("官祿宮")
H1("官祿宮 — 你怎麼工作、適合什麼")
P("官祿宮＝事業、工作狀態、與上司關係，也牽動夫妻感情。主星定適合行業，四化定工作怎麼變。")
H2("四化入官祿")
KV("化祿","工作量變大、忙碌，或業務範圍擴大。")
KV("化權","兼副業或半工半讀。")
KV("化科","行銷推廣事業、建立品牌形象。")
KV("化忌","轉換跑道或工作挫折（參考大限是否變動）。")
H2("看官祿宮步驟")
B("官祿宮&夾宮看工作運：吉星夾加分；羊陀火鈴空劫夾→吉宮轉凶。")
B("命、身、財、官一起看 → 判斷行業。")
B("行運四化入官祿＝工作變動；大限行至殺破狼 → 事業變動大。")
H2("主星 × 適合行業")
KV("紫微","老闆高層、政界、教授、學者。")
KV("天機","設計、物流、藝術、印刷、宗教；落陷→代工、批發盤商。")
KV("太陽","獨資事業、進出口；落陷→化工、貨運。")
KV("武曲","金融、軍警武職、機械五金；落陷→汽機車技職。")
KV("天同","飯店百貨、財經、美妝；落陷→門市、超商。")
KV("廉貞","業務行銷、電子硬體、消防、司法、公關、旅遊。")
KV("天府","銀行、寶石、政商、房地產、農畜、餐飲。")
KV("太陰","不動產、服飾化妝品、女性相關、夜生活服務。")
KV("貪狼","娛樂夜店、餐飲、裝潢、商界、外務推銷。")
KV("巨門","口才、律師、醫生、教育、仲介。")
KV("天相","保險、政治律師、外交、醫藥、餐旅、進出口。")
KV("天梁","法官、顧問、出版傳播、企管、慈善、心理。")
KV("七殺","軍警、農林水產加工（文職不適合）。")
KV("破軍","盤商批發、高風險、外務推銷、化工、食品、二手貨。")
KV("輔星","火鈴→重工/技術；羊陀→軍警/外科；昌曲→公教/文書；化忌→自由業/是非業。")

SECTION("結語")
H1("命盤是地圖，不是宿命")
P("同一顆星，在不同人手上會長出不同的人生。這份筆記是讓你看懂傾向、拿回選擇，不是替你決定。")
P("先看懂自己的命財官——你是誰、你怎麼賺、你怎麼工作——再慢慢練、慢慢調整。")
NOTE("潔米爸陪你慢慢看。如果你願意，留言或加 LINE，我陪你一起把自己看懂。")
newpage()  # flush last

# 依 section 分組
from collections import OrderedDict, defaultdict
grp=OrderedDict()
for sec,path in records: grp.setdefault(sec,[]).append(path)
def chartpage(chart,out):
    p=Image.new("RGB",(W,H),BG); c=Image.open(chart).convert("RGB"); p.paste(c,((W-c.width)//2,(H-c.height)//2)); p.save(out); return out
order=["/tmp/hfdemo/cover.png"]
order+=grp["使用說明"]
order+=[chartpage("/tmp/hfdemo/chart_mingong.png","/tmp/cp_m.png")]+grp["命宮"]
order+=[chartpage("/tmp/hfdemo/chart_caibo.png","/tmp/cp_c.png")]+grp["財帛宮"]
order+=[chartpage("/tmp/hfdemo/chart_guanlu_final.png","/tmp/cp_g.png")]+grp["官祿宮"]
order+=grp["結語"]
out="/tmp/hfdemo/進階紫微筆記_第1部.pdf"
open(out,"wb").write(img2pdf.convert(order))
import os; print("PDF頁數:",len(order),"大小KB:",os.path.getsize(out)//1024)
