# -*- coding: utf-8 -*-
"""Targeted regen for pause-flagged scenes; mirrors regen_tts flow (synth first)."""
import os, sys, json, re, subprocess, shutil
BUILD=os.path.dirname(os.path.abspath(__file__))
HOME="/Volumes/Storage/voice-clone"
sys.path.insert(0,HOME)
os.environ["VOICE_REF"]=os.path.join(HOME,"voice_ref_tennis_backup.wav")
os.environ["VOICE_REF_TEXT"]=os.path.join(HOME,"voice_ref_text_tennis_backup.txt")
import clone  # load F5 first, like regen_tts
sys.path.insert(0,BUILD)
from scenes import SCENES, CAPTIONS
import importlib.util
spec=importlib.util.spec_from_file_location("fp",os.path.join(BUILD,"fix_pauses_lib.py"))
AUD=os.path.join(BUILD,"audio")
# lazy import of badgaps from fix_pauses (no clone import inside)
import fix_pauses_lib as FP
TARGETS=sys.argv[1].split(",")
for sc in SCENES:
    sid=sc["id"]
    if sid not in TARGETS: continue
    cur=FP.badgaps(os.path.join(AUD,sid+".wav"),CAPTIONS[sid])
    best=(len(cur),os.path.join(AUD,sid+".wav"))
    print(f"{sid} current bad={len(cur)} {cur}",flush=True)
    for t in range(1,5):
        raw=os.path.join(AUD,f"{sid}_p{t}_raw.wav"); fin=os.path.join(AUD,f"{sid}_p{t}.wav")
        clone.synth(sc["vo"],raw)
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",raw,"-af","loudnorm=I=-16:TP=-1.5,apad=pad_dur=0.18","-ar","48000","-ac","2",fin],check=True)
        b=FP.badgaps(fin,CAPTIONS[sid])
        print(f"{sid} try{t}: bad={len(b)} {b}",flush=True)
        if len(b)<best[0]: best=(len(b),fin)
        if len(b)==0: break
    if best[1]!=os.path.join(AUD,sid+".wav"):
        shutil.copy(best[1],os.path.join(AUD,sid+".wav")); print(f"{sid}: REPLACED bad={best[0]}",flush=True)
    else:
        print(f"{sid}: KEPT ORIGINAL bad={best[0]}",flush=True)
print("REGEN FIX DONE")
