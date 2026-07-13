# -*- coding: utf-8 -*-
"""Regenerate every scene's cloned VO with per-clip transcript verification (anti-leak).
Run with the voice-clone venv python. For each scene: synth -> whisper(small) -> check
(no ref-text leak substring + similarity >= threshold) -> retry up to MAX_TRIES, keep best."""
import os, sys, json, re, difflib, subprocess, tempfile, shutil

BUILD = os.path.dirname(os.path.abspath(__file__))
HOME = os.environ.get("VOICE_CLONE_HOME", "/Volumes/Storage/voice-clone")
sys.path.insert(0, HOME)
os.environ["VOICE_REF"] = os.path.join(HOME, "voice_ref_tennis_backup.wav")
os.environ["VOICE_REF_TEXT"] = os.path.join(HOME, "voice_ref_text_tennis_backup.txt")
import clone  # noqa  (uses VOICE_REF/VOICE_REF_TEXT/VOICE_SPEED env)
sys.path.insert(0, BUILD)
from scenes import SCENES

REFT = open(os.path.join(HOME, "voice_ref_text_tennis_backup.txt")).read().strip()
_D = {'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
clean = lambda s: re.sub(r'[^0-9A-Za-z一-鿿]', '', s)
d2c = lambda s: "".join(_D.get(ch, ch) for ch in s)
REFC = clean(d2c(REFT))
LEAK_PROBES = [REFC[i:i+8] for i in range(0, max(1, len(REFC)-8), 6)]

def whisper_text(wav):
    for attempt in range(2):
        tmp = tempfile.mkdtemp(prefix="wtts_")
        env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
        r = subprocess.run(["whisper", wav, "--language", "Chinese", "--model", "small",
                        "--output_format", "json", "--output_dir", tmp, "--fp16", "False",
                        "--verbose", "False"], capture_output=True, text=True, env=env)
        jp = os.path.join(tmp, os.path.splitext(os.path.basename(wav))[0] + ".json")
        if r.returncode == 0 and os.path.exists(jp):
            j = json.load(open(jp)); shutil.rmtree(tmp, ignore_errors=True)
            return j["text"]
        print(f"  whisper fail rc={r.returncode} attempt={attempt}: {r.stderr[-200:]}", flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
    return ""

def score(heard, want):
    h, w = clean(d2c(heard)), clean(d2c(want))
    leak = any(p in h for p in LEAK_PROBES if p)
    if len(h) - len(w) > 8: leak = True   # ASR much longer than script = extra content bled in
    sim = difflib.SequenceMatcher(None, h, w).ratio()
    return leak, sim

MAX_TRIES = 4
AUD = os.path.join(BUILD, "audio"); os.makedirs(AUD, exist_ok=True)
man = []
for sc in SCENES:
    sid = sc["id"]; want = sc["vo"]
    best = None  # (leak, -sim, path)
    for t in range(1, MAX_TRIES + 1):
        raw = os.path.join(AUD, f"{sid}_try{t}_raw.wav")
        wav = os.path.join(AUD, f"{sid}_try{t}.wav")
        clone.synth(want, raw)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
            "-af", "loudnorm=I=-16:TP=-1.5,apad=pad_dur=0.18", "-ar", "48000", "-ac", "2", wav],
            check=True)
        os.remove(raw)
        heard = whisper_text(wav)
        if not heard:
            print(f"{sid} try{t}: UNVERIFIABLE (whisper failed)", flush=True)
            leak, sim = True, 0.0   # treat as suspect -> prefer a verified take
        else:
            leak, sim = score(heard, want)
        print(f"{sid} try{t}: leak={leak} sim={sim:.3f}", flush=True)
        cand = (leak, -sim, wav)
        if best is None or cand < best: best = cand
        if not leak and sim >= 0.80: break
    leak, nsim, wav = best
    final = os.path.join(AUD, sid + ".wav")
    shutil.copyfile(wav, final)
    print(f"{sid}: PICK {os.path.basename(wav)} leak={leak} sim={-nsim:.3f}", flush=True)
    d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                                       "-of","csv=p=0",final]).strip())
    man.append({"id": sid, "dur": round(d, 3)})
# clean try files
for f in os.listdir(AUD):
    if "_try" in f: os.remove(os.path.join(AUD, f))
json.dump(man, open(os.path.join(BUILD, "durations.json"), "w"), ensure_ascii=False, indent=2)
print(f"TOTAL {sum(m['dur'] for m in man):.1f}s across {len(man)} scenes -> durations.json", flush=True)
sys.stdout.flush(); sys.stderr.flush()
os._exit(0)
