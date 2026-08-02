# -*- coding: utf-8 -*-
"""外科手术式修"句末该停没停": 不重新合成, 在连读处插入停顿.

为什么不重新合成: F5-TTS 每一稿随机吞掉不同的句号(实测原稿 1 处坏, 重生成的
3 稿各坏 3-4 处), 掷骰子不收敛. 插停顿只改那一个时间点, 其余样本不变.

v2 (2026-08-02, 黄泽林项目用户听出"强"字被劈开后重写) — 三条硬规则:
  1. 切点必须落在声学低谷: 在 whisper 边界时刻 ±SEARCH 内找 20ms-RMS 最低点;
     该低谷仍高于 GATE(说明字还没说完/无缝可切) → 跳过该边界, 宁可连读也不切字.
  2. 插入的不是数字零而是本段自身的"室内底噪"(全段最安静的 0.22s 克隆),
     纯零静音在有底噪的语音里是一个可听见的"洞".
  3. 插入块两端各做 10ms raised-cosine 淡入淡出, 消除拼接突跳(采样值跳变
     >0.01 即可听见"咔哒" — v1 的硬拼正是这样被用户听出来的).
修完仍用 boundary_report 复核; durations.json 同步更新(时长每处 +PAUSE).
用法: insert_pauses.py S3,S5         (voice-clone venv; 需要 whisper + numpy)"""
import os, sys, json, re, subprocess, difflib, wave
import numpy as np

BUILD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUILD)
from scenes import SCENES, CAPTIONS
from check_boundaries import boundary_report

AUD = os.path.join(BUILD, "audio")
PAUSE = 0.22          # 插入停顿长度(秒)
MINSIL = 0.15         # 边界处已有 >= 此静音则视为正常
SEARCH = 0.25         # 在边界时刻 ± 此范围内找声学低谷
GATE = 0.020          # 低谷 RMS 高于此值(满幅=1) => 字没说完, 跳过不切
FADE = 0.010          # 插入块两端淡入淡出
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

# ---------- v2 声学核心 ----------

def read_wav(p):
    w = wave.open(p, "rb")
    sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch).astype(np.float64)
    w.close()
    return a, sr, ch

def write_wav(p, a, sr, ch):
    w = wave.open(p, "wb")
    w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(np.clip(np.round(a), -32768, 32767).astype(np.int16).tobytes())
    w.close()

def rms_at(mono, i, f):
    seg = mono[max(0, i):i + f]
    return float(np.sqrt((seg ** 2).mean())) if len(seg) else 1e9

def best_cut(mono, sr, t):
    """在 t±SEARCH 内找 20ms-RMS 最低点; 返回 (采样点, 该点RMS/满幅)."""
    f = int(0.020 * sr)
    lo = max(f, int((t - SEARCH) * sr))
    hi = min(len(mono) - f, int((t + SEARCH) * sr))
    if hi <= lo:
        return None, 1.0
    best_i, best_r = None, None
    for i in range(lo, hi, f // 2):
        r = rms_at(mono, i, f)
        if best_r is None or r < best_r:
            best_r, best_i = r, i + f // 2
    return best_i, best_r / 32768.0

def room_tone(a, sr, need):
    """全段最安静的 need 秒作为插入底噪(比数字零更贴合本段音色)."""
    mono = np.abs(a).mean(axis=1)
    n = int(need * sr); step = int(0.05 * sr)
    if len(mono) <= n:
        return np.zeros((n, a.shape[1]))
    best_i, best_v = 0, None
    for i in range(0, len(mono) - n, step):
        v = float(mono[i:i + n].mean())
        if best_v is None or v < best_v:
            best_v, best_i = v, i
    return a[best_i:best_i + n].copy()

def splice(a, sr, cut_samples):
    """在各切点插入 room-tone, 两端 raised-cosine 融合. cut_samples 需升序."""
    tone = room_tone(a, sr, PAUSE)
    nf = int(FADE * sr)
    ramp = 0.5 * (1 - np.cos(np.linspace(0, np.pi, nf)))[:, None]   # 0->1
    t2 = tone.copy()
    t2[:nf] *= ramp                       # 淡入
    t2[-nf:] *= ramp[::-1]                # 淡出
    out, prev = [], 0
    for c in cut_samples:
        seg = a[prev:c].copy()
        if len(seg) >= nf:
            seg[-nf:] *= ramp[::-1]       # 语音尾部淡出到低谷
        out.append(seg); out.append(t2.copy())
        prev = c
    tail = a[prev:].copy()
    if len(tail) >= nf:
        tail[:nf] *= ramp                 # 语音头部淡入
    out.append(tail)
    return np.concatenate(out)

def wav_dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout.strip())

for sid in sys.argv[1].split(","):
    sc = next(s for s in SCENES if s["id"] == sid)
    caps = CAPTIONS[sid]
    want = strong_lines(sc["vo"].replace("/", ""), caps)
    wav = os.path.join(AUD, sid + ".wav")
    rep = boundary_report(wav, caps)
    if not rep:
        print(f"{sid} UNVERIFIABLE", flush=True); continue
    bad = [(li, t) for li, hit, ln, ctx, t in rep if li in want and ln < MINSIL]
    print(f"{sid} strong={sorted(want)} bad={[(li, round(t,2)) for li, t in bad]}", flush=True)
    if not bad:
        print(f"{sid} ok", flush=True); continue

    a, sr, ch = read_wav(wav)
    mono = a.mean(axis=1)
    total = len(a) / sr
    cuts, skipped = [], []
    for li, t in bad:
        if not (0.15 < t < total - 0.15):
            skipped.append((li, "边界越界")); continue
        i, r = best_cut(mono, sr, t)
        if i is None or r > GATE:
            skipped.append((li, f"无声学低谷(rms={r:.3f}) 字未说完, 不切"))
            continue
        cuts.append(i)
    for li, why in skipped:
        print(f"  line{li} SKIP: {why}", flush=True)
    if not cuts:
        print(f"  {sid} 无可安全插入的边界, 保留原稿", flush=True); continue

    cuts = sorted(set(cuts))
    fixed = splice(a, sr, cuts)
    out = os.path.join(AUD, f"{sid}_paused.wav")
    write_wav(out, fixed, sr, ch)

    rep2 = boundary_report(out, caps)
    bad2 = [li for li, hit, ln, ctx, t in rep2 if li in want and ln < MINSIL] if rep2 else ["?"]
    print(f"  after: bad={bad2}  sil={[ln for _,_,ln,_,_ in rep2]}", flush=True)
    if bad2 and bad2 != ["?"] and len(bad2) >= len(bad):
        print(f"  {sid} 未改善, 保留原稿", flush=True)
        os.remove(out)
    else:
        os.replace(out, wav)
        man = json.load(open(os.path.join(BUILD, "durations.json")))
        for row in man:
            if row["id"] == sid:
                row["dur"] = round(wav_dur(wav), 3)
        json.dump(man, open(os.path.join(BUILD, "durations.json"), "w"),
                  ensure_ascii=False, indent=2)
        print(f"  {sid} FIXED dur={wav_dur(wav):.3f} (插入 {len(cuts)} 处)", flush=True)
print("DONE", flush=True)
