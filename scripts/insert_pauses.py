# -*- coding: utf-8 -*-
"""外科手术式修"句末该停没停": 不重新合成, 直接在原音频的连读处插入静音.

为什么不重新合成: F5-TTS 每一稿随机吞掉不同的句号(实测原稿 1 处坏, 重生成的
3 稿各坏 3-4 处), 掷骰子不收敛. 插静音只改那一个时间点, 其余样本逐比特不变.

只处理 vo 中 STRONG 标点(。？！)对应的字幕行边界; 逗号处不停是正常朗读.
用法: insert_pauses.py [S3,S5]         (voice-clone venv, 需要 whisper)"""
import os, sys, json, re, subprocess, difflib

BUILD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUILD)
from scenes import SCENES, CAPTIONS
from check_boundaries import boundary_report

AUD = os.path.join(BUILD, "audio")
PAUSE = 0.22          # 插入静音长度
MINSIL = 0.15
STRONG = "。？！"
ALLP = "，。、？！"
_D = {'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
cl = lambda s: re.sub(r'[^0-9A-Za-z一-鿿]', '', "".join(_D.get(c, c) for c in s))

def strong_lines(vo, caps):
    vclean, vidx = "", []
    for i, ch in enumerate(vo):
        c = cl(ch)
        if c:
            vclean += c; vidx += [i] * len(c)
    capall = cl("".join(caps))
    sm = difflib.SequenceMatcher(None, capall, vclean)
    blocks = sm.get_matching_blocks()
    def mp(p):
        best = None
        for bl in blocks:
            if bl.a <= p <= bl.a + bl.size:
                return bl.b + (p - bl.a)
            d = min(abs(p - bl.a), abs(p - (bl.a + bl.size)))
            if best is None or d < best[0]:
                best = (d, bl.b + max(0, min(p - bl.a, bl.size)))
        return best[1] if best else p
    out = set()
    for li in range(len(caps) - 1):
        cpos = len(cl("".join(caps[:li + 1])))
        k = vidx[min(mp(cpos), len(vidx) - 1)] if vidx else 0
        cand = [(abs(j - k), j) for j in range(max(0, k - 3), min(len(vo), k + 5))
                if vo[j] in ALLP]
        if cand and vo[min(cand)[1]] in STRONG:
            out.add(li)
    return out

def dur(w):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of", "csv=p=0", w],
                                capture_output=True, text=True).stdout.strip())

def run(cmd):
    subprocess.run(cmd, check=True)

for sid in sys.argv[1].split(","):
    sc = next(s for s in SCENES if s["id"] == sid)
    caps = CAPTIONS[sid]
    want = strong_lines(sc["vo"].replace("/", ""), caps)
    wav = os.path.join(AUD, sid + ".wav")
    rep = boundary_report(wav, caps)
    if not rep:
        print(f"{sid} UNVERIFIABLE", flush=True); continue
    bad = [(li, t) for li, hit, ln, ctx, t in rep if li in want and ln < MINSIL]
    print(f"{sid} strong={sorted(want)} bad={[(li, t) for li, t in bad]}", flush=True)
    if not bad:
        print(f"{sid} ok", flush=True); continue

    total = dur(wav)
    cuts = sorted(t for _, t in bad if 0.15 < t < total - 0.15)
    if not cuts:
        print(f"{sid} 边界时间越界, skip", flush=True); continue

    tmpd = os.path.join(AUD, f"_{sid}_ins")
    os.makedirs(tmpd, exist_ok=True)
    sil = os.path.join(tmpd, "sil.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=48000:cl=stereo", "-t", str(PAUSE), sil])
    seq, prev = [], 0.0
    for i, c in enumerate(cuts):
        p = os.path.join(tmpd, f"p{i}.wav")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ss", str(prev),
             "-to", str(c), "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", p])
        seq += [p, sil]; prev = c
    p = os.path.join(tmpd, "pz.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ss", str(prev),
         "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", p])
    seq.append(p)
    lst = os.path.join(tmpd, "list.txt")
    open(lst, "w").write("".join(f"file '{x}'\n" for x in seq))
    out = os.path.join(AUD, f"{sid}_paused.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", out])

    rep2 = boundary_report(out, caps)
    bad2 = [li for li, hit, ln, ctx, t in rep2 if li in want and ln < MINSIL] if rep2 else ["?"]
    print(f"  after: bad={bad2}  sil={[ln for _,_,ln,_,_ in rep2]}", flush=True)
    if bad2 and bad2 != ["?"] and len(bad2) >= len(bad):
        print(f"  {sid} 未改善, 保留原稿", flush=True)
    else:
        run(["cp", out, wav])
        man = json.load(open(os.path.join(BUILD, "durations.json")))
        for row in man:
            if row["id"] == sid:
                row["dur"] = round(dur(wav), 3)
        json.dump(man, open(os.path.join(BUILD, "durations.json"), "w"),
                  ensure_ascii=False, indent=2)
        print(f"  {sid} FIXED dur={dur(wav):.3f}", flush=True)
    subprocess.run(["rm", "-rf", tmpd])
print("DONE", flush=True)
