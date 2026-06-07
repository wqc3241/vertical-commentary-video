# -*- coding: utf-8 -*-
"""Inspect footage: grab frames at (clip,time) points into one labelled image, then Read it.
Two ways to call:

  # explicit grabs:  stem,seconds[,label] ...
  python build/contact_sheet.py source 06_SF,130 06_SF,208,net 07_AND,44

  # even sampling of a final video across the timeline:
  python build/contact_sheet.py video /path/out.mp4 12     # 12 frames evenly spaced

Writes build/contact.png. Then Read that file to look at it.
"""
import subprocess, os, sys
from PIL import Image, ImageDraw, ImageFont

BUILD = os.path.dirname(os.path.abspath(__file__))
SRC   = os.path.join(os.path.dirname(BUILD), "source")
F = ImageFont.truetype("/Library/Fonts/Arial Unicode.ttf", 24)
TW, TH = 320, 180

def grab(path, t, scale=(TW,TH)):
    o = f"/tmp/cs_{abs(hash((path,t)))%99999}.jpg"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(max(t,0)),"-i",path,
                    "-frames:v","1","-vf",f"scale={scale[0]}:{scale[1]}",o], check=True)
    return Image.open(o)

def sheet(items):  # items: list of (image, label)
    cols = min(6, len(items)); rows = (len(items)+cols-1)//cols
    s = Image.new("RGB", (cols*TW, rows*TH), (12,12,12)); d = ImageDraw.Draw(s)
    for i,(im,lab) in enumerate(items):
        x,y = (i%cols)*TW,(i//cols)*TH; s.paste(im.resize((TW,TH)),(x,y))
        d.rectangle([x,y,x+min(TW,8+int(F.getlength(lab))),y+28], fill=(0,0,0))
        d.text((x+5,y+3), lab, font=F, fill=(0,255,150))
    out = os.path.join(BUILD,"contact.png"); s.save(out); print("->", out, s.size)

mode = sys.argv[1]
if mode == "video":
    v = sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 9
    D = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",v]).strip())
    items = [(grab(v, D*(k+0.5)/n), f"{D*(k+0.5)/n:.0f}s") for k in range(n)]
    sheet(items)
else:  # explicit grabs from source/
    items = []
    for a in sys.argv[2:]:
        p = a.split(","); stem, t = p[0], float(p[1]); lab = p[2] if len(p) > 2 else f"{stem} {t:.0f}"
        items.append((grab(os.path.join(SRC, stem+".mp4"), t), f"{lab} {t:.0f}"))
    sheet(items)
