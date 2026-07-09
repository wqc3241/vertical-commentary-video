# -*- coding: utf-8 -*-
"""Assemble final video with the USER's recording as the main voice + each clip's ORIGINAL
audio mixed in quietly underneath (crowd / ball / atmosphere).
Prereq: scene mp4s rendered (render.py all) and durations.json from align.py (real pacing).
Usage:  python build/assemble_ambient.py build/voice/full48k.wav [ambient_gain]
Default ambient_gain = 0.14 (voice stays clearly dominant)."""
import json, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as S
from scenes import SCENES

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(BUILD)
SRC   = os.path.join(ROOT, "source")
SCN   = os.path.join(BUILD, "scene")
AMB   = os.path.join(BUILD, "amb"); os.makedirs(AMB, exist_ok=True)
OUT   = os.path.join(ROOT, getattr(S, "OUTPUT_NAME", "output_9x16.mp4"))
VOICE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BUILD, "voice", "full48k.wav")
GAIN  = float(sys.argv[2]) if len(sys.argv) > 2 else 0.14
DUR   = {d["id"]: d["dur"] for d in json.load(open(os.path.join(BUILD, "durations.json")))}

def run(c): subprocess.run(c, check=True)

def seg_audio(stem, tin, dur, out):
    """Extract source audio [tin, tin+dur] -> 48k stereo wav (silence-padded if source has none)."""
    run(["ffmpeg","-y","-loglevel","error","-ss",f"{tin:.3f}","-t",f"{dur:.3f}",
         "-i",os.path.join(SRC,stem+".mp4"),
         "-af","aresample=48000,highpass=f=90,alimiter=limit=0.9",
         "-ac","2","-ar","48000","-vn",out])

def concat(files, out):
    lst = out + ".txt"; open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,"-c","copy",out])

# 1) per-scene ambient (montage-aware), each exactly the scene's duration
amb_files = []
for sc in SCENES:
    sid = sc["id"]; D = DUR[sid]
    clips = sc.get("clips")
    if clips:
        n = len(clips); seg = D/n; parts = []
        for i,(stem,t) in enumerate(clips):
            f = os.path.join(AMB, f"_{sid}_{i}.wav"); seg_audio(stem, t, seg, f); parts.append(f)
        out = os.path.join(AMB, f"{sid}.wav"); concat(parts, out)
    else:
        out = os.path.join(AMB, f"{sid}.wav"); seg_audio(sc["src"], sc["tin"], D, out)
    amb_files.append(out)
concat(amb_files, os.path.join(BUILD, "ambient_master.wav"))

# 2) video master (concat rendered scenes)
vm = os.path.join(BUILD, "video_master.mp4")
concat([os.path.join(SCN, s["id"]+".mp4") for s in SCENES], vm)
total = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                                       "-of","csv=p=0",vm]).strip())
fo = max(total-0.7, 0)

# 3) mux: video + (voice loudnorm) + (ambient * gain), with fades
subprocess.run(["ffmpeg","-y","-loglevel","error",
     "-i", vm, "-i", VOICE, "-i", os.path.join(BUILD,"ambient_master.wav"),
     "-filter_complex",
     f"[0:v]fade=t=in:st=0:d=0.4,fade=t=out:st={fo:.2f}:d=0.7[v];"
     f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={fo:.2f}:d=0.7[vo];"
     f"[2:a]volume={GAIN},afade=t=in:st=0:d=0.6,afade=t=out:st={fo:.2f}:d=0.7[amb];"
     f"[vo][amb]amix=inputs=2:normalize=0:duration=first[a]",
     "-map","[v]","-map","[a]","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
     "-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest", OUT], check=True)
print(f"FINAL (voice + ambient@{GAIN}): {OUT}  ({total:.1f}s)")
