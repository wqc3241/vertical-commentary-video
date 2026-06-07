# -*- coding: utf-8 -*-
"""Align a user's single-take recording to the script so cuts follow THEIR pacing.
Prereq: a recording at build/voice/full.m4a, transcribed with Whisper word timestamps:

  ffmpeg -y -i build/voice/full.m4a -ar 16000 -ac 1 build/voice/full16k.wav
  ffmpeg -y -i build/voice/full.m4a -ar 48000 -ac 2 build/voice/full48k.wav
  whisper build/voice/full16k.wav --language Chinese --model small --word_timestamps True \
          --output_format json --output_dir build/voice --fp16 False

Then run this -> overwrites build/durations.json with REAL per-scene durations.
Render normally, then: python build/render.py assemble-voice build/voice/full48k.wav
"""
import json, os, sys, re, bisect, subprocess, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenes import SCENES

BUILD = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(os.path.join(BUILD,"voice","full16k.json")))
AUDIO = os.path.join(BUILD,"voice","full48k.wav")
AUDIO_DUR = float(subprocess.check_output(
    ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",AUDIO]).strip())
clean = lambda s: re.sub(r'[^0-9A-Za-z一-鿿]', '', s)

ac, at = [], []
for seg in J["segments"]:
    for w in seg.get("words", []):
        t = clean(w["word"])
        if not t: continue
        a,b,n = w["start"], w["end"], len(t)
        for i,ch in enumerate(t): ac.append(ch); at.append(a+(b-a)*(i+0.5)/max(n,1))
asr = "".join(ac)
script, sstart = "", []
for sc in SCENES: sstart.append(len(script)); script += clean(sc["vo"])

sm = difflib.SequenceMatcher(None, asr, script, autojunk=False)
ax, ay = [], []
for tag,i1,i2,j1,j2 in sm.get_opcodes():
    if tag == "equal":
        for k in range(i2-i1): ax.append(j1+k); ay.append(at[i1+k])

def time_at(j):
    if j <= ax[0]: return ay[0]
    if j >= ax[-1]: return ay[-1]
    p = bisect.bisect_left(ax, j)
    if ax[p] == j: return ay[p]
    x0,x1,y0,y1 = ax[p-1],ax[p],ay[p-1],ay[p]
    return y0+(y1-y0)*(j-x0)/(x1-x0)

starts = [time_at(s) for s in sstart]; starts[0] = 0.0
for i in range(1,len(starts)):
    if starts[i] < starts[i-1]+1.2: starts[i] = starts[i-1]+1.2
man = []
print(f"align ratio={sm.ratio():.3f}  audio={AUDIO_DUR:.1f}s")
for i,sc in enumerate(SCENES):
    end = starts[i+1] if i+1 < len(starts) else AUDIO_DUR
    man.append({"id": sc["id"], "dur": round(end-starts[i],3)})
    print(f"  {sc['id']:4s} {starts[i]:6.1f} {man[-1]['dur']:6.2f}")
json.dump(man, open(os.path.join(BUILD,"durations.json"),"w"), ensure_ascii=False, indent=2)
print(f"\ntotal {sum(m['dur'] for m in man):.1f}s -> durations.json (real-voice pacing)")
