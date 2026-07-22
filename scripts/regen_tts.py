# -*- coding: utf-8 -*-
"""Cloned-voice generation with QUADRUPLE gates per take (the 2026-07-22 battle-tested default).
Run with the voice-clone venv python. Usage:
  regen_tts.py            # all scenes
  regen_tts.py S3,S9      # only these (others keep existing wavs; durations.json always complete)
Per take: synth (vo with "/" STRIPPED — F5 vocalizes slashes as junk syllables!) -> whisper(small) ->
gates: (1) ref-leak probes  (2) INSERTED content via difflib insert-ops (catches hallucinated
extra words the user can hear)  (3) letter-by-letter acronym completeness (N、C、A、A must all be heard)
(4) zero intra-line pauses via fix_pauses_lib (letter-gaps between spelled letters are exempt).
Retry <= MAX_TRIES, keep best (leak, inserts, gaps, -sim). Raise the early-break sim (0.88 -> 0.95)
when the user reports 生硬 prosody, to force full takes and pick the smoothest."""
import os, sys, json, re, difflib, subprocess, tempfile, shutil

BUILD = os.path.dirname(os.path.abspath(__file__))
HOME = os.environ.get("VOICE_CLONE_HOME", "/Volumes/Storage/voice-clone")
sys.path.insert(0, HOME)
os.environ["VOICE_REF"] = os.path.join(HOME, "voice_ref_tennis_backup.wav")
os.environ["VOICE_REF_TEXT"] = os.path.join(HOME, "voice_ref_text_tennis_backup.txt")
import clone  # noqa  (uses VOICE_REF/VOICE_REF_TEXT/VOICE_SPEED env)
sys.path.insert(0, BUILD)
from scenes import SCENES, CAPTIONS
import fix_pauses_lib as FP

REFT = open(os.path.join(HOME, "voice_ref_text_tennis_backup.txt")).read().strip()
_D = {'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
_TRAD = str.maketrans("後沒來還學裡歲產馬蘭勝負績轉業職圓夢寫歷萬億圖書館開關門東車貝見長門問間們幾點無爲為與獎їі讓誰請謝運動員專屬網絡續約錄擊敗數據隊員師賽場館歐陽؀؁", "后没来还学里岁产马兰胜负绩转业职圆梦写历万亿图书馆开关门东车贝见长门问间们几点无为为与奖ii让谁请谢运动员专属网络续约录击败数据队员师赛场馆欧阳؀؁")
def clean(s):
    s = s.translate(_TRAD)
    s = s.replace("一零零", "一百")
    return re.sub(r'[^0-9A-Za-z一-鿿]', '', s)
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
    """Triple gate: ref-leak probes, INSERTED content (difflib insert ops of >=2 hanzi
    — catches hallucinated extra words the user heard), similarity."""
    h, w = clean(d2c(heard)), clean(d2c(want))
    leak = any(p in h for p in LEAK_PROBES if p)
    h_cn = re.sub(r'[A-Za-z]', '', h); w_cn = re.sub(r'[A-Za-z]', '', w)
    if len(h_cn) - len(w_cn) > 6: leak = True
    ins = 0
    # letter-by-letter acronym reads (N、C、A、A / T、C、U ...) must be heard COMPLETE:
    # a take where whisper misses a letter (e.g. hears "NCA") is rejected and re-rolled
    flat_heard = re.sub(r'[^A-Za-z0-9一-鿿]', '', heard)
    for _run in re.findall(r'[A-Z](?:、[A-Z])+', want):
        if _run.replace('、', '') not in flat_heard:
            ins += 1
    sm = difflib.SequenceMatcher(None, w, h)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "insert" and (j2 - j1) >= 2 and re.search(r'[一-鿿]{2}', h[j1:j2]):
            ins += 1
        if op == "replace" and (j2 - j1) - (i2 - i1) >= 2 and re.search(r'[一-鿿]{2}', h[j1:j2]):
            ins += 1
    sim = sm.ratio()
    return leak, ins, sim

MAX_TRIES = 5
AUD = os.path.join(BUILD, "audio"); os.makedirs(AUD, exist_ok=True)
TARGETS = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
man = []
for sc in SCENES:
    sid = sc["id"]; want = sc["vo"].replace("/", "")
    if TARGETS and sid not in TARGETS:
        final = os.path.join(AUD, sid + ".wav")
        if os.path.exists(final):
            d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                                               "-of","csv=p=0",final]).strip())
            man.append({"id": sid, "dur": round(d, 3)})
            print(f"{sid}: keep existing ({d:.1f}s)", flush=True)
        else:
            print(f"{sid}: MISSING and not targeted!", flush=True)
        continue
    best = None  # (leak, -sim, path)
    for t in range(1, MAX_TRIES + 1):
        raw = os.path.join(AUD, f"{sid}_try{t}_raw.wav")
        wav = os.path.join(AUD, f"{sid}_try{t}.wav")
        clone.synth(want, raw)
        try:
            import torch
            if hasattr(torch, "mps"): torch.mps.empty_cache()
        except Exception: pass
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
            "-af", "loudnorm=I=-16:TP=-1.5,apad=pad_dur=0.18", "-ar", "48000", "-ac", "2", wav],
            check=True)
        os.remove(raw)
        heard = whisper_text(wav)
        if not heard:
            print(f"{sid} try{t}: UNVERIFIABLE (whisper failed)", flush=True)
            leak, ins, sim = True, 9, 0.0
        else:
            leak, ins, sim = score(heard, want)
        gaps = FP.badgaps(wav, CAPTIONS[sid]) if sid in CAPTIONS else []
        # letter-by-letter acronym reads (N、C、A、A) legitimately pause between letters;
        # exempt gaps whose context is a latin letter so they don't fail the zero-gap gate
        gaps = [g for g in gaps if not re.search(r'[A-Za-z]', str(g[2]))]
        print(f"{sid} try{t}: leak={leak} ins={ins} gaps={len(gaps)}{gaps} sim={sim:.3f}", flush=True)
        cand = (leak, ins, len(gaps), -sim, wav)
        if best is None or cand < best: best = cand
        if (not leak) and ins == 0 and len(gaps) == 0 and sim >= 0.95: break
    leak, ins, gaps, nsim, wav = best
    final = os.path.join(AUD, sid + ".wav")
    shutil.copyfile(wav, final)
    print(f"{sid}: PICK {os.path.basename(wav)} leak={leak} ins={ins} gaps={gaps} sim={-nsim:.3f}", flush=True)
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
