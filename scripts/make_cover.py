# -*- coding: utf-8 -*-
"""小红书竖版封面 v2:ChatGPT底图 + 本地统一排版(账号风格一致性的唯一来源,勿改模板参数)。
用法: python build/make_cover.py <底图> <输出.jpg> "主标题" ["副标题"] ["人名"] ["角标,默认:网球故事"]
模板: 3:4 1242x1656 · 背景=底图放大模糊26+压暗 · 清晰主体层=画幅86%宽、底部对齐(人物不顶到标题) ·
主标题 Songti SC Black 白字黑描边 · 副标题 Songti SC Bold 金色#F2C94C · 底部人名 白字+金色圆点 ·
左上角系列角标 #C4563A 圆角胶囊(Hiragino W6,与视频chip同族) · 标题块起始y=175(避开角标)。"""
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1242,1656
SONG="/System/Library/Fonts/Supplemental/Songti.ttc"
HEI="/System/Library/Fonts/Hiragino Sans GB.ttc"
fBlack=lambda sz: ImageFont.truetype(SONG,sz,index=0)   # Songti SC Black
fBold =lambda sz: ImageFont.truetype(SONG,sz,index=1)   # Songti SC Bold
fHei  =lambda sz: ImageFont.truetype(HEI,sz,index=2)    # Hiragino W6 (角标)

def compose_bg(base):
    im=Image.open(base).convert("RGB"); w,h=im.size
    s=max(W/w,H/h); big=im.resize((int(w*s+0.5),int(h*s+0.5)),Image.LANCZOS)
    l=(big.width-W)//2; t=(big.height-H)//2
    bg=big.crop((l,t,l+W,t+H)).filter(ImageFilter.GaussianBlur(26)).point(lambda p:int(p*0.52))
    fw=int(W*0.86); s2=fw/w; fg=im.resize((fw,int(h*s2+0.5)),Image.LANCZOS)
    x=(W-fw)//2; y=H-fg.height           # 底部对齐:主体下沉、顶部让给标题
    bg.paste(fg,(x,y))
    grad=Image.new("L",(1,300))          # 底部渐暗,给人名垫底
    for i in range(300): grad.putpixel((0,i),int(120*i/300))
    bg.paste(Image.new("RGB",(W,300),(0,0,0)),(0,H-300),grad.resize((W,300)))
    return bg

def title_block(im, main, sub):
    d=ImageDraw.Draw(im); y=175
    if main:
        sz=148 if len(main)<=6 else int(148*6/len(main))
        f=fBlack(sz); x=(W-d.textlength(main,font=f))//2
        d.text((x,y),main,font=f,fill=(255,255,255),stroke_width=8,stroke_fill=(18,14,10))
        y+=int(sz*1.28)
    if sub:
        sz=92 if len(sub)<=10 else int(92*10/len(sub))
        f=fBold(sz); x=(W-d.textlength(sub,font=f))//2
        d.text((x,y),sub,font=f,fill=(242,201,76),stroke_width=5,stroke_fill=(24,18,8))

def name_line(im, name):
    if not name: return
    d=ImageDraw.Draw(im); txt=" ".join(name)   # 字间距
    f=fBold(64); wpx=d.textlength(txt,font=f); x=(W-wpx)//2; y=H-168
    r=7; cy=y+40
    d.ellipse([x-56-r,cy-r,x-56+r,cy+r],fill=(242,201,76))
    d.ellipse([x+wpx+56-r,cy-r,x+wpx+56+r,cy+r],fill=(242,201,76))
    d.text((x,y),txt,font=f,fill=(255,255,255),stroke_width=4,stroke_fill=(18,14,10))

def tag(im, txt):
    d=ImageDraw.Draw(im); f=fHei(46)
    pw=int(d.textlength(txt,font=f))+56; ph=78; x,y=42,42
    d.rounded_rectangle([x,y,x+pw,y+ph],radius=39,fill=(196,86,58))
    d.text((x+28,y+(ph-52)//2),txt,font=f,fill=(255,255,255))

if __name__=="__main__":
    base,out,main=sys.argv[1],sys.argv[2],sys.argv[3]
    sub =sys.argv[4] if len(sys.argv)>4 else ""
    name=sys.argv[5] if len(sys.argv)>5 else ""
    series=sys.argv[6] if len(sys.argv)>6 else "网球故事"
    im=compose_bg(base)
    tag(im,series); title_block(im,main,sub); name_line(im,name)
    im.save(out,quality=93); print("cover ->",out,im.size)
