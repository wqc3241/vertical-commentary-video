# -*- coding: utf-8 -*-
"""Assemble the 16:9 video: concat scene16/*.mp4, mux USER voice + reuse ambient_master.wav.
Usage: python build/assemble16.py build/voice/full48k.wav [ambient_gain]"""
import json, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenes import SCENES
BUILD=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(BUILD)
SCN=os.path.join(BUILD,"scene16"); OUT=os.path.join(ROOT,"rafa_doc_16x9.mp4")
VOICE=sys.argv[1] if len(sys.argv)>1 else os.path.join(BUILD,"voice","full48k.wav")
GAIN=float(sys.argv[2]) if len(sys.argv)>2 else 0.14
AMB=os.path.join(BUILD,"ambient_master.wav")

def concat(files,out):
    lst=out+".txt"; open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,"-c","copy",out],check=True)

vm=os.path.join(BUILD,"video_master16.mp4")
concat([os.path.join(SCN,s["id"]+".mp4") for s in SCENES], vm)
total=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",vm]).strip())
fo=max(total-0.7,0)
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",vm,"-i",VOICE,"-i",AMB,
    "-filter_complex",
    f"[0:v]fade=t=in:st=0:d=0.4,fade=t=out:st={fo:.2f}:d=0.7[v];"
    f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={fo:.2f}:d=0.7[vo];"
    f"[2:a]volume={GAIN},afade=t=in:st=0:d=0.6,afade=t=out:st={fo:.2f}:d=0.7[amb];"
    f"[vo][amb]amix=inputs=2:normalize=0:duration=first[a]",
    "-map","[v]","-map","[a]","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
    "-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",OUT],check=True)
print(f"FINAL 16:9: {OUT}  ({total:.1f}s)")
