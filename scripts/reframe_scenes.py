# -*- coding: utf-8 -*-
"""Reframe each scene window (and each montage clip) from landscape source to a
full-bleed 9:16 vertical clip that tracks the main player, using the
video-autoreframe skill pipeline. Output -> build/reframed/<stem>_<tin>_<dur>.mp4

Keying matches render.py._render_base: stem = source basename, tin/dur formatted
%.3f. Single scenes use (tin, DUR[id]); montage clips use (clip_tin, DUR[id]/n).
Re-run safe: skips windows whose output already exists (delete to redo).

v2 (2026-08-02):
- scenes.py 的 FIT_WINDOWS 现在真正生效: 表内 (stem, tin) 的窗口直接跳过
  (不产 reframed 文件 => render.py 自动回落整幅居中+模糊补边). 之前 SKILL.md
  写了但没实现, 标了 7 个窗口全被 YOLO 白裁了一轮.
- 复用 YOLO 检测顺手产出 build/subject_report.json + 控制台 ⚠ 警告:
  有人帧占比 <85% 或主体高度占比均值 <0.13 的窗口标为可疑(阈值用黄泽林项目
  实测标定: 用户抓的 3 处"画面没人/画中画"窗口分别是 61%/72%/73%, 通过的
  全部 >=85%). 整屏卡片(0人)也会被同一检查逮住. 可疑窗口再人工看图, 其余免看.
"""
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
FIT = [(str(st), float(t)) for st, t in getattr(S, "FIT_WINDOWS", [])]

MIN_PRESENCE = 0.85   # 有人帧占比低于此 => 可疑
MIN_SUBJ_H   = 0.13   # 最大人物框高/画面高 的均值低于此 => 主体太小/远景

def is_fit(stem, tin):
    return any(st == stem and abs(t - tin) < 0.06 for st, t in FIT)

def window_clip(stem, tin, dur, out):
    """Cut exact landscape window [tin, tin+dur] from source -> out (re-encoded, clean GOP)."""
    subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{tin:.3f}","-t",f"{dur:.3f}",
        "-i",os.path.join(SRC,stem+".mp4"),"-an","-c:v","libx264","-preset","fast","-crf","14",
        "-pix_fmt","yuv420p",out],check=True)

def subject_stats(det_path):
    """det.json -> (有人帧占比, 主体高占比均值). 检测已做, 统计是免费的."""
    try:
        j = json.load(open(det_path))
    except Exception:
        return None
    smp = j.get("samples") or []
    H = j.get("H") or 1
    if not smp:
        return None
    withp = [s for s in smp if s.get("people")]
    presence = len(withp) / len(smp)
    hs = [max(p["h"] for p in s["people"]) / H for s in withp]
    return (round(presence, 3), round(sum(hs) / len(hs), 3) if hs else 0.0)

REPORT = {}

def reframe(stem, tin, dur):
    key = f"{stem}_{tin:.3f}_{dur:.3f}"
    out = os.path.join(REF, key+".mp4")
    if is_fit(stem, tin):
        if os.path.exists(out):
            os.remove(out)                # 曾被误裁过的, 撤下让 render 回落
            print(f"  FIT {key} (removed stale reframe -> blur letterbox)")
        else:
            print(f"  FIT {key} (skip YOLO -> blur letterbox)")
        REPORT[key] = {"mode": "fit"}
        return None
    work = f"/tmp/rf_{key}"; os.makedirs(work, exist_ok=True)
    det = os.path.join(work, "det.json")
    if os.path.exists(out):
        st = subject_stats(det) if os.path.exists(det) else None
        REPORT[key] = {"mode": "tracked", "presence": st[0] if st else None,
                       "subj_h": st[1] if st else None}
        print(f"  skip {key} (exists)"); return out
    win = os.path.join(work, "win.mp4")
    print(f"  window {key} ...", flush=True)
    window_clip(stem, tin, dur, win)
    subprocess.run([PY, os.path.join(SKILL,"scripts","1_detect.py"), win, det], check=True)
    st = subject_stats(det)
    REPORT[key] = {"mode": "tracked", "presence": st[0] if st else None,
                   "subj_h": st[1] if st else None}
    subprocess.run([PY, os.path.join(SKILL,"scripts","2_solve_path.py"),
        "--detections",det,"--target-aspect","9:16",
        "--out-cmds",os.path.join(work,"cmds.txt")], check=True)
    subprocess.run([PY, os.path.join(SKILL,"scripts","3_encode.py"),
        "--src",win,"--cmds",os.path.join(work,"cmds.txt"),
        "--out",out,"--target-aspect","9:16","--crf","12"], check=True)
    print(f"  -> {out}", flush=True)
    return out

def windows():
    """Yield (sid, stem, tin, dur) for every render window, matching render.py keys."""
    for sc in S.SCENES:
        if sc["treat"].startswith("card:"): continue
        sid = sc["id"]; D = DUR[sid]; clips = sc.get("clips")
        if clips:
            seg = D/len(clips)
            for cs, ct in clips:
                yield (sid, cs, float(ct), seg)
        else:
            yield (sid, sc["src"], float(sc["tin"]), D)

if __name__ == "__main__":
    only = sys.argv[1:] if len(sys.argv) > 1 else None  # optional stems/keys filter
    seen, owner = set(), {}
    for sid, stem, tin, dur in windows():
        key = f"{stem}_{tin:.3f}_{dur:.3f}"
        owner.setdefault(key, sid)
        if key in seen: continue
        seen.add(key)
        if only and not any(o in key for o in only): continue
        reframe(stem, tin, dur)

    # ---- 主体在场报告: 可疑的必须人工看图, 其余可免看 ----
    sus = []
    for key, r in REPORT.items():
        if r.get("mode") != "tracked": continue
        p, h = r.get("presence"), r.get("subj_h")
        why = []
        if p is not None and p < MIN_PRESENCE: why.append(f"有人帧仅{p*100:.0f}%")
        if h is not None and h < MIN_SUBJ_H:  why.append(f"主体高占比{h:.2f}(太小/远景)")
        if why:
            sus.append((owner.get(key, "?"), key, ", ".join(why)))
            r["suspect"] = why
    json.dump({"thresholds": {"presence": MIN_PRESENCE, "subj_h": MIN_SUBJ_H},
               "windows": REPORT},
              open(os.path.join(BUILD, "subject_report.json"), "w"),
              ensure_ascii=False, indent=1)
    if sus:
        print("\n⚠ 主体存疑窗口(整屏卡片/画中画/没人/远景 — 必须人工看图确认):")
        for sid, key, why in sus:
            print(f"  {sid}  {key}  {why}")
    else:
        print("\n主体在场检查: 全部窗口通过 (>=85% 有人帧, 主体高占比>=0.13)")
    print("ALL REFRAMES DONE  (report -> build/subject_report.json)")
