# -*- coding: utf-8 -*-
"""Reframe each scene window (and each montage clip) from landscape source to a
full-bleed 9:16 vertical clip that tracks the main player, using the
video-autoreframe skill pipeline. Output -> build/reframed/<stem>_<tin>_<dur>.mp4

Keying matches render.py._render_base: stem = source basename, tin/dur formatted
%.3f. Single scenes use (tin, DUR[id]); montage clips use (clip_tin, DUR[id]/n).
Re-run safe: skips windows whose output already exists (delete to redo)."""
import os, sys, json, subprocess, importlib.util

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(BUILD)
SRC   = os.path.join(ROOT, "source")
REF   = os.path.join(BUILD, "reframed"); os.makedirs(REF, exist_ok=True)
SKILL = os.path.expanduser("~/.claude/skills/video-autoreframe")
PY    = os.path.join(SKILL, "venv", "bin", "python")

spec = importlib.util.spec_from_file_location("scenes", os.path.join(BUILD, "scenes.py"))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
DUR = {d["id"]: d["dur"] for d in json.load(open(os.path.join(BUILD, "durations.json")))}

def window_clip(stem, tin, dur, out):
    """Cut exact landscape window [tin, tin+dur] from source -> out (re-encoded, clean GOP)."""
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{tin:.3f}","-t",f"{dur:.3f}",
        "-i",os.path.join(SRC,stem+".mp4"),"-an","-c:v","libx264","-preset","fast","-crf","14",
        "-pix_fmt","yuv420p",out],check=True)

def reframe(stem, tin, dur):
    key = f"{stem}_{tin:.3f}_{dur:.3f}"
    out = os.path.join(REF, key+".mp4")
    if os.path.exists(out):
        print(f"  skip {key} (exists)"); return out
    work = f"/tmp/rf_{key}"; os.makedirs(work, exist_ok=True)
    win = os.path.join(work, "win.mp4")
    print(f"  window {key} ...", flush=True)
    window_clip(stem, tin, dur, win)
    subprocess.run([PY, os.path.join(SKILL,"scripts","1_detect.py"), win, os.path.join(work,"det.json")], check=True)
    subprocess.run([PY, os.path.join(SKILL,"scripts","2_solve_path.py"),
        "--detections",os.path.join(work,"det.json"),"--target-aspect","9:16",
        "--out-cmds",os.path.join(work,"cmds.txt")], check=True)
    subprocess.run([PY, os.path.join(SKILL,"scripts","3_encode.py"),
        "--src",win,"--cmds",os.path.join(work,"cmds.txt"),
        "--out",out,"--target-aspect","9:16","--crf","12"], check=True)
    print(f"  -> {out}", flush=True)
    return out

def windows():
    """Yield (stem, tin, dur) for every render window, matching render.py keys."""
    for sc in S.SCENES:
        if sc["treat"].startswith("card:"): continue
        sid = sc["id"]; D = DUR[sid]; clips = sc.get("clips")
        if clips:
            seg = D/len(clips)
            for cs, ct in clips:
                yield (cs, float(ct), seg)
        else:
            yield (sc["src"], float(sc["tin"]), D)

if __name__ == "__main__":
    only = sys.argv[1:] if len(sys.argv) > 1 else None  # optional stems/keys filter
    seen = set()
    for stem, tin, dur in windows():
        key = f"{stem}_{tin:.3f}_{dur:.3f}"
        if key in seen: continue
        seen.add(key)
        if only and not any(o in key for o in only): continue
        reframe(stem, tin, dur)
    print("ALL REFRAMES DONE")
