# -*- coding: utf-8 -*-
"""Contact sheet of shot-END frames for one reel — to pick complete points the player WINS.
  python build/shotsheet.py 06_SF_Shnaider [min_shot_seconds=3.5]
Writes build/sheet_<stem>.png. Read it: look for endings that show YOUR player reacting/winning
(know their kit colour), and note times to avoid (opponent celebrating, replays, graphics)."""
import subprocess, json, os, sys
from PIL import Image, ImageDraw, ImageFont
BUILD = os.path.dirname(os.path.abspath(__file__))
SRC   = os.path.join(os.path.dirname(BUILD), "source")
reel  = sys.argv[1]; mind = float(sys.argv[2]) if len(sys.argv) > 2 else 3.5
cand  = [s for s in json.load(open(os.path.join(BUILD,"shots.json")))[reel] if s[2] >= mind]
F = ImageFont.truetype("/Library/Fonts/Arial Unicode.ttf", 24)
TW, TH, cols = 320, 180, 6; rows = (len(cand)+cols-1)//cols
sheet = Image.new("RGB", (cols*TW, rows*TH), (12,12,12)); d = ImageDraw.Draw(sheet)
for i,(s,e,du) in enumerate(cand):
    o = f"/tmp/ss_{i}.jpg"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(max(e-0.5,0)),
        "-i",os.path.join(SRC,reel+".mp4"),"-frames:v","1","-vf",f"scale={TW}:{TH}",o], check=True)
    im = Image.open(o); x,y = (i%cols)*TW,(i//cols)*TH; sheet.paste(im,(x,y))
    d.rectangle([x,y,x+TW,y+30], fill=(0,0,0)); d.text((x+5,y+3), f"#{i} end={e:.0f} d={du:.0f}", font=F, fill=(0,255,150))
out = os.path.join(BUILD,f"sheet_{reel}.png"); sheet.save(out); print("->", out, "cands", len(cand))
