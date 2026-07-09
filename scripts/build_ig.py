# Build full-bleed 1080x1920 reframed clips for native-vertical IG sources (no YOLO; just scale).
import os, json, subprocess, importlib.util
BUILD=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(BUILD)
SRC=os.path.join(ROOT,"source"); REF=os.path.join(BUILD,"reframed"); os.makedirs(REF,exist_ok=True)
spec=importlib.util.spec_from_file_location("scenes",os.path.join(BUILD,"scenes.py"))
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
DUR={d["id"]:d["dur"] for d in json.load(open(os.path.join(BUILD,"durations.json")))}
def build(stem,tin,dur):
    key=f"{stem}_{tin:.3f}_{dur:.3f}"; out=os.path.join(REF,key+".mp4")
    src=os.path.join(SRC,stem+".mp4")
    if not os.path.exists(src):
        print("MISSING SRC",src); return
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{tin:.3f}","-t",f"{dur:.3f}","-i",src,
        "-vf","scale=1080:1920:flags=lanczos,fps=30,eq=brightness=0.0:saturation=1.05","-an",
        "-c:v","libx264","-preset","slow","-crf","14","-pix_fmt","yuv420p",out],check=True)
    print("built",key)
for sc in S.SCENES:
    if not str(sc["src"]).startswith("ig_"): continue
    sid=sc["id"]; D=DUR[sid]; clips=sc.get("clips")
    if clips:
        seg=D/len(clips)
        for cs,ct in clips:
            if str(cs).startswith("ig_"): build(cs,float(ct),seg)
    else:
        build(sc["src"],float(sc["tin"]),D)
print("DONE")
