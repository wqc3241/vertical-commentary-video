# -*- coding: utf-8 -*-
"""小红书竖版封面:ChatGPT底图 + 本地统一排版(字体/描边/角标固定,保证账号封面风格一致)。
用法: python build/make_cover.py <底图> <输出.jpg> "主标题" ["副标题(金色)"] ["角标(默认:网球故事)"]
模板(勿改,风格一致性来源):3:4 1242x1656;Hiragino Sans GB W6;主标题白+黑描边;
副标题金色#F2C94C;标题块置顶部负空间;左上角红棕圆角角标#C4563A。"""
import sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1242,1656
FONT="/System/Library/Fonts/Hiragino Sans GB.ttc"   # index=2 = W6,与视频字幕同款
def font(sz): return ImageFont.truetype(FONT, sz, index=2)

def fit(base):
    im=Image.open(base).convert("RGB"); w,h=im.size
    s=max(W/w,H/h); im=im.resize((int(w*s+0.5),int(h*s+0.5)),Image.LANCZOS)
    l=(im.width-W)//2; t=max(0,(im.height-H)//3)   # 偏上裁,保住顶部负空间
    return im.crop((l,t,l+W,t+H))

def draw_text(im, lines):
    d=ImageDraw.Draw(im); y=96
    for i,txt in enumerate(lines):
        if not txt: continue
        big = (i==0)
        sz = 132 if big else 88
        if len(txt)>7: sz=int(sz*7/len(txt))
        f=font(sz)
        wpx=d.textlength(txt,font=f); x=(W-wpx)//2
        # soft shadow
        sh=Image.new("RGBA",im.size,(0,0,0,0)); ds=ImageDraw.Draw(sh)
        ds.text((x,y+6),txt,font=f,fill=(0,0,0,160),stroke_width=8,stroke_fill=(0,0,0,160))
        im.paste(Image.composite(sh,Image.new("RGBA",im.size,(0,0,0,0)),sh).filter(ImageFilter.GaussianBlur(6)).convert("RGB"),(0,0),sh.filter(ImageFilter.GaussianBlur(6)))
        d.text((x,y),txt,font=f,fill=(255,255,255) if big else (242,201,76),
               stroke_width=8 if big else 6, stroke_fill=(20,16,12))
        y+=int(sz*1.32)
    return y

def tag(im, txt):
    d=ImageDraw.Draw(im); f=font(46)
    pw=int(d.textlength(txt,font=f))+56; ph=78; x,y=42,42
    d.rounded_rectangle([x,y,x+pw,y+ph],radius=39,fill=(196,86,58))
    d.text((x+28,y+(ph-52)//2),txt,font=f,fill=(255,255,255))

if __name__=="__main__":
    base,out=sys.argv[1],sys.argv[2]
    main=sys.argv[3]; sub=sys.argv[4] if len(sys.argv)>4 else ""
    series=sys.argv[5] if len(sys.argv)>5 else "网球故事"
    im=fit(base)
    tag(im,series)
    draw_text(im,[main,sub])
    im.save(out,quality=93)
    print("cover ->",out,im.size)
