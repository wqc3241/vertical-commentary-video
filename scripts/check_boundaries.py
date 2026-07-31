# -*- coding: utf-8 -*-
"""断句审计 v2 · "该断没断" (fix_pauses.py 查的是"停错地方",互补).

v1 用 whisper 词间隔判断 —— 错误方法: whisper 中文词级时间戳是连续切分的
(相邻词 end==start), 量不出真实停顿, 结果几乎全部误报 0.0.
v2 改为声学法: ffmpeg silencedetect 找真实静音段, 再把字幕行边界映射到时间轴,
检查边界附近 WIN 秒内有没有静音. 没有 -> 两行连读.

用法: check_boundaries.py [S3,S5]      (voice-clone venv)"""
import os, sys, json, re, subprocess, tempfile, shutil, difflib

BUILD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUILD)
from scenes import SCENES, CAPTIONS

AUD = os.path.join(BUILD, "audio")
NOISE = "-34dB"      # 与 fix_pauses 同阈值
MINSIL = 0.10        # 认定为"可听停顿"的最短静音
WIN = 0.28           # 边界时间点 ±WIN 内找得到静音即算断开
_D = {'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
clean = lambda s: re.sub(r'[^0-9A-Za-z一-鿿]', '', "".join(_D.get(c, c) for c in s))

def words(wav):
    tmp = tempfile.mkdtemp()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    subprocess.run(["whisper", wav, "--language", "Chinese", "--model", "small",
                    "--word_timestamps", "True", "--output_format", "json",
                    "--output_dir", tmp, "--fp16", "False", "--verbose", "False"],
                   capture_output=True, text=True, env=env)
    jp = os.path.join(tmp, os.path.splitext(os.path.basename(wav))[0] + ".json")
    j = json.load(open(jp)); shutil.rmtree(tmp, ignore_errors=True)
    out = []
    for seg in j["segments"]:
        for w in seg.get("words", []):
            out.append((w["word"].strip(), w["start"], w["end"]))
    return out

def silences(wav):
    r = subprocess.run(["ffmpeg", "-i", wav, "-af",
                        f"silencedetect=noise={NOISE}:d={MINSIL}", "-f", "null", "-"],
                       capture_output=True, text=True)
    out, st = [], None
    for line in r.stderr.splitlines():
        m = re.search(r"silence_start: (-?[0-9.]+)", line)
        if m: st = float(m.group(1))
        m = re.search(r"silence_end: ([0-9.]+)", line)
        if m and st is not None:
            out.append((st, float(m.group(1)))); st = None
    return [(a, b) for a, b in out if a > 0.05]

def boundary_report(wav, caps):
    """[(line_idx, has_pause, silence_len, context, boundary_time)] — 每个字幕行内部边界一条"""
    ws = words(wav)
    if not ws:
        return None
    sils = silences(wav)
    asr = clean("".join(w[0] for w in ws))
    cap = clean("".join(caps))
    cb, c = [], 0
    for line in caps:
        c += len(clean(line)); cb.append(c)
    cb = cb[:-1]
    sm = difflib.SequenceMatcher(None, cap, asr)
    blocks = sm.get_matching_blocks()
    def map_pos(b):
        best = None
        for bl in blocks:
            if bl.a <= b <= bl.a + bl.size:
                return bl.b + (b - bl.a)
            d = min(abs(b - bl.a), abs(b - (bl.a + bl.size)))
            if best is None or d < best[0]:
                best = (d, bl.b + max(0, min(b - bl.a, bl.size)))
        return best[1] if best else b
    pos, marks = 0, []
    for i, (w, s, e) in enumerate(ws):
        pos += len(clean(w))
        marks.append((pos, i))
    res = []
    for li, b in enumerate(cb):
        target = map_pos(b)
        wi = min(range(len(marks)), key=lambda k: abs(marks[k][0] - target))
        t = ws[wi][2]                                  # 该行最后一个词的结束时刻
        hit = [(a, e) for a, e in sils if a - WIN <= t <= e + WIN]
        ctx = ws[wi][0] + "|" + (ws[wi + 1][0] if wi + 1 < len(ws) else "")
        res.append((li, bool(hit), round(max((e - a for a, e in hit), default=0.0), 3), ctx, round(t, 3)))
    return res

if __name__ == "__main__":
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    flagged = {}
    for sc in SCENES:
        sid = sc["id"]
        if only and sid not in only:
            continue
        wav = os.path.join(AUD, sid + ".wav")
        if not os.path.exists(wav):
            continue
        rep = boundary_report(wav, CAPTIONS[sid])
        if rep is None:
            print(sid, "UNVERIFIABLE", flush=True); continue
        bad = [(li, ctx) for li, hit, ln, ctx, t in rep if not hit]
        if bad:
            flagged[sid] = bad
        print(sid, ("RUN-ON " + str(bad)) if bad else "ok",
              " sil=" + str([ln for _, _, ln, _, _ in rep]), flush=True)
    json.dump(flagged, open(os.path.join(BUILD, "boundary_audit.json"), "w"), ensure_ascii=False)
    print("FLAGGED:", list(flagged), flush=True)
