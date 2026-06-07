# -*- coding: utf-8 -*-
"""Snap each footage scene's END to a real shot boundary so cuts never land mid-rally.
Writes build/proposed_tins.json and a verification contact sheet build/verify_ends.png.

ANTI-FLASH (why EDGE_MARGIN): a detected boundary `e` is the FIRST frame of the NEXT shot. Ending a
scene exactly at `e` makes that next-shot frame your LAST frame -> a 1-frame flash of crowd / reaction
close-up / handshake / graphic board at the cut (the user WILL notice this). So we back the end off by
EDGE_MARGIN (~5 frames) to keep the last frame inside the rally. If you hand-set tins (lock / _MANUAL),
subtract the margin yourself: tin = (winning-shot boundary) - EDGE_MARGIN - dur.

scenes.py may guide this:
  - a scene with "lock": True keeps its hand-set tin (use for user-specified exact windows; YOU apply margin)
  - END_OVERRIDES = {"S1": 168.5}   -> force that scene to end exactly there (margin still applied)
  - AVOID_ENDS    = {"<stem>": [242.0, 483.0]}  -> never end near these (opponent celebration, graphics)
The scenes.py tail must apply proposed_tins.json (+ any MANUAL/lock tins) on import — see scenes_template.py.
"""
import subprocess, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as S
from scenes import SCENES
from PIL import Image, ImageDraw, ImageFont

BUILD = os.path.dirname(os.path.abspath(__file__))
SRC   = os.path.join(os.path.dirname(BUILD), "source")
shots = json.load(open(os.path.join(BUILD, "shots.json")))
DUR   = {d["id"]: d["dur"] for d in json.load(open(os.path.join(BUILD,"durations.json")))}
clipdur = {k: max(e for _,e,_ in v) for k,v in shots.items()}
OVERRIDE = getattr(S, "END_OVERRIDES", {})
AVOID    = getattr(S, "AVOID_ENDS", {})
EDGE_MARGIN = float(os.environ.get("EDGE_MARGIN", "0.17"))  # end this many secs BEFORE the cut (anti-flash)

def snap(reel, target, D, used):
    cands = [e for s,e,du in shots.get(reel,[]) if du >= 4 and e-0.3 >= D and e <= clipdur[reel]-0.1]
    def ok(e):
        if any(abs(e-b) < 1.2 for b in AVOID.get(reel, [])): return False
        if any(abs(e-u) < 2.0 for u in used): return False
        return True
    cands = [e for e in cands if ok(e)]
    return min(cands, key=lambda e: abs(e-target)) if cands else None

proposed, used = {}, {}
for sc in SCENES:
    sid = sc["id"]
    if sc["treat"] != "blur" or sc.get("lock"):       # cards + locked manual windows keep their tin
        proposed[sid] = sc["tin"]; continue
    D, reel = DUR[sid], sc["src"]; used.setdefault(reel, [])
    E = OVERRIDE.get(sid) or snap(reel, sc["tin"]+D, D, used[reel])
    if E is None:
        proposed[sid] = sc["tin"]; print(f"{sid}: no boundary, keep {sc['tin']}"); continue
    used[reel].append(E); end = E - EDGE_MARGIN; proposed[sid] = round(end - D, 2)
    print(f"{sid} {reel:20s} D={D:5.1f}  cut@{E:6.1f} end->{end:6.1f}  tin {sc['tin']:6.1f} -> {proposed[sid]:6.1f}")

json.dump(proposed, open(os.path.join(BUILD,"proposed_tins.json"),"w"), indent=1)

# verification sheet: the final frame of each scene
F = ImageFont.truetype("/Library/Fonts/Arial Unicode.ttf", 24)
TW, TH, cols = 300, 169, 6; rows = (len(SCENES)+cols-1)//cols
sheet = Image.new("RGB", (cols*TW, rows*TH), (12,12,12)); d = ImageDraw.Draw(sheet)
for i,sc in enumerate(SCENES):
    sid = sc["id"]; D = DUR[sid]; tin = proposed[sid]
    t = tin+D*0.5 if sc["treat"].startswith("card") else tin+D-0.06   # the TRUE last frame: must be rally, not a stray next-shot frame
    o = f"/tmp/ve_{i}.jpg"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(max(t,0)),
        "-i",os.path.join(SRC,sc["src"]+".mp4"),"-frames:v","1","-vf",f"scale={TW}:{TH}",o], check=True)
    im = Image.open(o); x,y = (i%cols)*TW,(i//cols)*TH; sheet.paste(im,(x,y))
    d.rectangle([x,y,x+TW,y+28], fill=(0,0,0)); d.text((x+5,y+3), f"{sid} end {tin+D:.0f}s", font=F, fill=(0,255,150))
sheet.save(os.path.join(BUILD,"verify_ends.png"))
print(f"\n-> build/proposed_tins.json + build/verify_ends.png  (EDGE_MARGIN={EDGE_MARGIN}s before each cut)")
print("   inspect verify_ends.png: every last frame is RALLY (no crowd / reaction close-up / handshake / logo / opponent).")
