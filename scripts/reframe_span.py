# -*- coding: utf-8 -*-
"""Contiguous tracked spans: YOLO-reframe ONCE over the span, split into per-slice keys (seamless)."""
import os, sys, json, subprocess, importlib.util
BUILD=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(BUILD)
SRC=os.path.join(ROOT,"source"); REF=os.path.join(BUILD,"reframed"); os.makedirs(REF,exist_ok=True)
SKILL=os.path.expanduser("~/.claude/skills/video-autoreframe"); PY=os.path.join(SKILL,"venv","bin","python")
spec=importlib.util.spec_from_file_location("scenes",os.path.join(BUILD,"scenes.py"))
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
DUR={d["id"]:d["dur"] for d in json.load(open(os.path.join(BUILD,"durations.json")))}
def is_vert(stem):
    if stem.startswith("ig"): return True
    r=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",os.path.join(SRC,stem+".mp4")],capture_output=True,text=True)
    try: w,h=map(int,r.stdout.strip().split(",")); return h>=w
    except: return False
def groups():
    for sc in S.SCENES:
        if sc["treat"].startswith("card:"): continue
        sid=sc["id"]; D=DUR[sid]; clips=sc.get("clips")
        if not clips: 
            yield (sc["src"],float(sc["tin"]),D,1); continue
        seg=D/len(clips); i=0
        while i<len(clips):
            stem,t=clips[i][0],float(clips[i][1]); k=1
            while i+k<len(clips) and clips[i+k][0]==stem and abs(float(clips[i+k][1])-(t+k*seg))<0.02: k+=1
            yield (stem,t,seg,k); i+=k
def reframe_span(stem,t,seg,k):
    span=seg*k
    keys=[os.path.join(REF,f"{stem}_{t+j*seg:.3f}_{seg:.3f}.mp4") for j in range(k)]
    if all(os.path.exists(x) for x in keys): print("skip",stem,t,k); return
    work=f"/tmp/rfs_{stem}_{t:.0f}"; os.makedirs(work,exist_ok=True)
    win=os.path.join(work,"win.mp4")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{t:.3f}","-t",f"{span:.3f}","-i",os.path.join(SRC,stem+".mp4"),"-an","-c:v","libx264","-preset","fast","-crf","14","-pix_fmt","yuv420p",win],check=True)
    full=os.path.join(work,"full.mp4")
    subprocess.run([PY,os.path.join(SKILL,"scripts","1_detect.py"),win,os.path.join(work,"det.json")],check=True)
    subprocess.run([PY,os.path.join(SKILL,"scripts","2_solve_path.py"),"--detections",os.path.join(work,"det.json"),"--target-aspect","9:16","--out-cmds",os.path.join(work,"cmds.txt")],check=True)
    subprocess.run([PY,os.path.join(SKILL,"scripts","3_encode.py"),"--src",win,"--cmds",os.path.join(work,"cmds.txt"),"--out",full,"--target-aspect","9:16","--crf","12"],check=True)
    for j in range(k):
        subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{j*seg:.3f}","-t",f"{seg:.3f}","-i",full,"-an","-c:v","libx264","-preset","slow","-crf","13","-pix_fmt","yuv420p",keys[j]],check=True)
    print("built-span",stem,t,k,flush=True)
if __name__=="__main__":
    FIT=set((a,round(b,2)) for a,b in getattr(S,"FIT_WINDOWS",[]))
    for stem,t,seg,k in groups():
        if is_vert(stem): continue  # build_ig covers verticals seamlessly
        if (stem,round(t,2)) in FIT: print("FIT-skip",stem,t); continue
        reframe_span(stem,t,seg,k)
    print("SPANS DONE")
