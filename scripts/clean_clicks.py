# -*- coding: utf-8 -*-
"""清除 IndexTTS 句尾残渣 (2026-08-03 用户在 S24 听到"每句话结束一个短促zh声").
逐句合成的 vocoder 偶发在句尾吐一个 ~40-100ms 的擦音残片; 拼接后以"静音包围的孤立短音"
形式存在句界处. 判据: 响段 ≤0.12s + 两侧 ≥0.10s 静音 + 前后 0.6s 内没有其它孤岛
(W、T、A 逐字母是 0.2-0.4s 一串, 不会孤立, 不受伤). 用相邻底噪原位替换, 时长零变化
(captions/durations 全部不动, 只需重出受影响 part 的预览).
用法: python3 build/clean_clicks.py          # 全部场景, 就地清理
"""
import os, glob, wave
import numpy as np

BUILD = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(BUILD, "audio")
WIN = 0.020
LOUD, MAXD, ISO, LONE = 0.02, 0.12, 0.10, 0.60
FADE = 0.008

def rd(p):
    w = wave.open(p, 'rb'); sr, ch = w.getframerate(), w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch).astype(np.float64)
    w.close(); return a, sr, ch

def wr(p, a, sr, ch):
    w = wave.open(p, 'wb'); w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(np.clip(np.round(a), -32768, 32767).astype(np.int16).tobytes()); w.close()

def loud_runs(a, sr):
    mono = np.abs(a).mean(axis=1) / 32768.0
    n = int(WIN * sr); nw = len(mono) // n
    rms = np.sqrt((mono[:nw*n].reshape(nw, n) ** 2).mean(axis=1))
    runs, i = [], 0
    while i < nw:
        if rms[i] > LOUD:
            j = i
            while j < nw and rms[j] > LOUD: j += 1
            runs.append((i * n, j * n))
            i = j
        else:
            i += 1
    return runs, n, nw

total = 0
for p in sorted(glob.glob(os.path.join(AUD, "S*.wav")),
                key=lambda x: int(os.path.basename(x)[1:-4])):
    sid = os.path.basename(p)[:-4]
    a, sr, ch = rd(p)
    runs, n, nw = loud_runs(a, sr)
    iso = int(ISO * sr)
    cands = []
    for k, (s, e) in enumerate(runs):
        if (e - s) / sr > MAXD: continue
        prev_e = runs[k-1][1] if k > 0 else 0
        next_s = runs[k+1][0] if k+1 < len(runs) else len(a)
        if s - prev_e < iso or next_s - e < iso: continue          # 不够孤立
        near = [r for j, r in enumerate(runs) if j != k
                and abs((r[0]+r[1])/2 - (s+e)/2) < LONE * sr
                and (r[1]-r[0])/sr <= 0.45]
        if any((r[1]-r[0])/sr <= MAXD or True for r in near) and near:  # 0.6s 内有邻居=逐字母串
            continue
        cands.append((s, e))
    nf = int(FADE * sr)
    ramp = 0.5 * (1 - np.cos(np.linspace(0, np.pi, nf)))[:, None]
    fixed = []
    for s, e in cands:
        L = max(0, s - int(0.02 * sr)); R = min(len(a), e + int(0.02 * sr))
        span = R - L
        tone_s = max(0, L - span - nf)
        if L - tone_s < span: continue
        tone = a[L-span-nf if L-span-nf>=0 else 0:L][-span:].copy()
        if len(tone) < span: continue
        tone[:nf] *= ramp; tone[-nf:] *= ramp[::-1]
        a[L:L+nf] = a[L:L+nf] * ramp[::-1] + tone[:nf]
        a[L+nf:R-nf] = tone[nf:-nf]
        a[R-nf:R] = a[R-nf:R] * ramp + tone[-nf:]
        fixed.append(round(L / sr, 2))
    if fixed:
        wr(p, a, sr, ch)
        total += len(fixed)
        print(f"{sid}: 清除 {len(fixed)} 处句尾残渣 @ {fixed}", flush=True)
print(f"DONE 共清除 {total} 处 (时长零变化)")
