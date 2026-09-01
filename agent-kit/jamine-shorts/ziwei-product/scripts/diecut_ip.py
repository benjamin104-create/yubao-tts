# IP 貼圖去背：AI 抓人物(保留白衣)+ 平滑白邊(die-cut)。需 rembg + Pillow。
# 用法: python3 diecut_ip.py 來源.png 輸出.png
from rembg import remove
from PIL import Image, ImageFilter
import sys
def diecut(src,out,ow=30,pad=140):
    im0=Image.open(src).convert("RGBA")
    im=Image.new("RGBA",(im0.width+2*pad,im0.height+2*pad),(255,255,255,255)); im.paste(im0,(pad,pad))
    cut=remove(im); a=cut.split()[3]
    a=a.point(lambda p:255 if p>170 else 0).filter(ImageFilter.GaussianBlur(1.5)).point(lambda p:255 if p>110 else 0)
    cut.putalpha(a)
    dil=a.filter(ImageFilter.MaxFilter(ow|1)).filter(ImageFilter.GaussianBlur(2.5)).point(lambda p:255 if p>90 else 0)
    base=Image.new("RGBA",im.size,(0,0,0,0)); white=Image.new("RGBA",im.size,(255,255,255,255))
    base.paste(white,(0,0),dil); base.alpha_composite(cut); base.save(out)
if __name__=="__main__": diecut(sys.argv[1],sys.argv[2])
