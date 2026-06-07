# -*- coding: utf-8 -*-
"""FALLBACK quick-draft voiceover with macOS `say` (robotic). Prefer the cloned voice
(clone.py scenes) for anything real. Writes build/audio/<id>.wav + build/durations.json."""
import subprocess, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenes import SCENES

BUILD = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(BUILD,"audio"); os.makedirs(AUD, exist_ok=True)
VOICE, RATE = os.environ.get("SAY_VOICE","Tingting"), os.environ.get("SAY_RATE","175")

def dur(p): return float(subprocess.check_output(
    ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())

man = []
for sc in SCENES:
    aiff = os.path.join(AUD, sc["id"]+".aiff"); wav = os.path.join(AUD, sc["id"]+".wav")
    subprocess.run(["say","-v",VOICE,"-r",RATE,"-o",aiff,sc["vo"]], check=True)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",aiff,
                    "-af","apad=pad_dur=0.22","-ar","48000","-ac","2",wav], check=True)
    os.remove(aiff); d = dur(wav); man.append({"id": sc["id"], "dur": round(d,3)})
    print(f"{sc['id']}: {d:5.2f}s")
json.dump(man, open(os.path.join(BUILD,"durations.json"),"w"), ensure_ascii=False, indent=2)
print(f"TOTAL {sum(m['dur'] for m in man):.1f}s -> durations.json")
