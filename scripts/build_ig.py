# Build full-bleed 1080x1920 reframed clips for native-vertical IG sources (no YOLO; just scale).
# Cover-crop scale (force_original_aspect_ratio=increase + crop): a 3:4 / non-9:16 source is
# center-cropped, NEVER stretched (2026-07: 3:4 clips got distorted by plain scale=1080:1920).
# scenes.py optional IG_EXCLUDE=("igx_e",...): stem prefixes to SKIP here so they fall back to the
# blur-letterbox path instead (use for ig-prefixed sources whose center-crop would cut the subject).
import os, json, subprocess, importlib.util
BUILD=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(BUILD)
SRC=os.path.join(ROOT,"source"); REF=os.path.join(BUILD,"reframed"); os.makedirs(REF,exist_ok=True)
spec=importlib.util.spec_from_file_location("scenes",os.path.join(BUILD,"scenes.py"))
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
DUR={d["id"]:d["dur"] for d in json.load(open(os.path.join(BUILD,"durations.json")))}
EXCL=tuple(getattr(S,"IG_EXCLUDE",()))
def is_ig(stem):
    stem=str(stem)
    return stem.startswith("ig") and not (EXCL and stem.startswith(EXCL))
def build(stem,tin,dur):
    key=f"{stem}_{tin:.3f}_{dur:.3f}"; out=os.path.join(REF,key+".mp4")
    src=os.path.join(SRC,stem+".mp4")
    if not os.path.exists(src):
        print("MISSING SRC",src); return
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{tin:.3f}","-t",f"{dur:.3f}","-i",src,
        "-vf","scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps=30,eq=brightness=0.0:saturation=1.05","-an",
        "-c:v","libx264","-preset","slow","-crf","14","-pix_fmt","yuv420p",out],check=True)
    print("built",key)
for sc in S.SCENES:
    if sc["treat"].startswith("card:"): continue
    sid=sc["id"]; D=DUR.get(sid)
    if D is None: continue
    clips=sc.get("clips")
    if clips:
        seg=D/len(clips)
        for cs,ct in clips:
            if is_ig(cs): build(cs,float(ct),seg)
    else:
        if is_ig(sc["src"]): build(sc["src"],float(sc["tin"]),D)
print("DONE")
