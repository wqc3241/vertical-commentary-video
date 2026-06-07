# -*- coding: utf-8 -*-
"""Detect camera-cut boundaries in every source/*.mp4 (each continuous shot ~= one point/rally).
Writes build/shots.json: { "<stem>": [ [start,end,dur], ... ] }
A higher threshold merges shots; lower splits more. 0.4 is a good default for broadcast cuts.
"""
import subprocess, re, json, os, glob, sys

BUILD = os.path.dirname(os.path.abspath(__file__))
SRC   = os.path.join(os.path.dirname(BUILD), "source")
THRESH = float(os.environ.get("SHOT_THRESH", "0.4"))

def dur(p):
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())

def cuts(p):
    r = subprocess.run(["ffmpeg","-hide_banner","-i",p,"-filter:v",
        f"select='gt(scene,{THRESH})',showinfo","-an","-f","null","-"], capture_output=True, text=True)
    return sorted(set(float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)))

shots = {}
for p in sorted(glob.glob(os.path.join(SRC, "*.mp4"))):
    stem = os.path.splitext(os.path.basename(p))[0]
    D = dur(p); cs = [c for c in cuts(p) if 0.3 < c < D-0.2]
    b = [0.0] + cs + [round(D,2)]
    shots[stem] = [[round(a,2), round(e,2), round(e-a,2)] for a,e in zip(b[:-1], b[1:])]
    longs = sum(1 for s in shots[stem] if s[2] >= 4)
    print(f"{stem:24s} dur {D:6.1f}  shots {len(shots[stem]):3d}  (>=4s: {longs})")

json.dump(shots, open(os.path.join(BUILD,"shots.json"),"w"), indent=1)
print("\n-> build/shots.json")
