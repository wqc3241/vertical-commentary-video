# -*- coding: utf-8 -*-
"""五段预览: 每段(A/B/C/D/E)拼场景视频+该段TTS配音+该段原声(gain 0.30)。
输出 <project>/预览_A.mp4 ... 预览_E.mp4。Usage: python build/preview_parts.py [gain] [parts]"""
import json, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenes import SCENES

BUILD=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(BUILD)
SRC=os.path.join(ROOT,"source"); SCN=os.path.join(BUILD,"scene"); AUD=os.path.join(BUILD,"audio")
AMB=os.path.join(BUILD,"amb"); os.makedirs(AMB,exist_ok=True)
GAIN=float(sys.argv[1]) if len(sys.argv)>1 else 0.30
ONLY=sys.argv[2] if len(sys.argv)>2 else "ABCDE"
DUR={d["id"]:d["dur"] for d in json.load(open(os.path.join(BUILD,"durations.json")))}
def run(c): subprocess.run(c,check=True)
def has_audio(path):
    import subprocess
    r=subprocess.run(["ffprobe","-v","error","-select_streams","a","-show_entries","stream=index","-of","csv=p=0",path],capture_output=True,text=True)
    return bool(r.stdout.strip())

def seg_audio(stem,tin,dur,out):
    src=os.path.join(SRC,stem+".mp4")
    if has_audio(src):
        run(["ffmpeg","-y","-loglevel","error","-ss",f"{tin:.3f}","-t",f"{dur:.3f}",
             "-i",src,
             "-af","aresample=48000,highpass=f=90,alimiter=limit=0.9","-ac","2","-ar","48000","-vn",out])
    else:
        run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-t",f"{dur:.3f}",
             "-i","anullsrc=r=48000:cl=stereo",out])

def concat(files,out,copy=True):
    lst=out+".txt"; open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst]+(["-c","copy"] if copy else [])+[out])
for part in "ABCDE":
    if part not in ONLY: continue
    scs=[s for s in SCENES if s["id"].startswith(part)]
    # ambient per scene
    ambs=[]
    for sc in scs:
        sid=sc["id"]; D=DUR[sid]; clips=sc.get("clips")
        out=os.path.join(AMB,f"{sid}.wav")
        if not os.path.exists(out):
            if clips:
                n=len(clips); seg=D/n; parts=[]
                for i,(stem,t) in enumerate(clips):
                    f=os.path.join(AMB,f"_{sid}_{i}.wav"); seg_audio(stem,t,seg,f); parts.append(f)
                concat(parts,out)
            else:
                seg_audio(sc["src"],sc["tin"],D,out)
        ambs.append(out)
    vm=os.path.join(BUILD,f"pv_{part}_v.mp4"); concat([os.path.join(SCN,s["id"]+".mp4") for s in scs],vm)
    am=os.path.join(BUILD,f"pv_{part}_voice.wav"); concat([os.path.join(AUD,s["id"]+".wav") for s in scs],am)
    ab=os.path.join(BUILD,f"pv_{part}_amb.wav"); concat(ambs,ab)
    total=sum(DUR[s["id"]] for s in scs); fo=max(total-0.5,0)
    OUT=os.path.join(ROOT,f"预览_{part}.mp4")
    run(["ffmpeg","-y","-loglevel","error","-i",vm,"-i",am,"-i",ab,"-filter_complex",
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[vo];[2:a]volume={GAIN}[amb];"
        f"[vo][amb]amix=inputs=2:normalize=0:duration=first[a]",
        "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",OUT])
    print("PREVIEW",part,f"{total:.1f}s ->",OUT)
print("PREVIEWS DONE")
