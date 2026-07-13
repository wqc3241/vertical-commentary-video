# -*- coding: utf-8 -*-
"""Transcript-check every cloned-voice clip against its vo text (F5-TTS can leak the
reference clip or hallucinate — duration alone is NOT enough). Uses the whisper JSONs
caption_times.py wrote to build/capjson/<id>.json."""
import json, os, re, sys, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenes import SCENES

BUILD = os.path.dirname(os.path.abspath(__file__))
_D = {'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
clean = lambda s: re.sub(r'[^0-9A-Za-z一-鿿]', '', s)
d2c = lambda s: "".join(_D.get(ch, ch) for ch in s)

bad = 0
for sc in SCENES:
    sid = sc["id"]
    j = os.path.join(BUILD, "capjson", sid + ".json")
    if not os.path.exists(j):
        print(f"{sid}: NO TRANSCRIPT"); bad += 1; continue
    heard = clean(d2c(json.load(open(j))["text"]))
    want = clean(d2c(sc["vo"]))
    r = difflib.SequenceMatcher(None, heard, want).ratio()
    flag = "OK " if r >= 0.85 else "BAD"
    if r < 0.85: bad += 1
    print(f"{sid}: {flag} sim={r:.3f} len_heard={len(heard)} len_want={len(want)}")
    if r < 0.85:
        print(f"   want: {want[:80]}")
        print(f"  heard: {heard[:80]}")
print("ALL OK" if bad == 0 else f"{bad} SCENES NEED RE-TTS")
