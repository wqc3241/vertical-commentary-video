# -*- coding: utf-8 -*-
"""收紧现有配音 (2026-08-03 用户预览反馈: 语速有点慢 + 断句空隙太长).
不重合成 — 对 build/audio/S*.wav 外科处理:
  1. RMS 找 >=0.24s 的静音段(句间程序化停顿 0.28s 是主要目标), 居中裁到 0.185s, 10ms 余弦融合
  2. 整体 atempo 1.0323 (净语速 0.93 -> 0.96)
就地覆盖 build/audio/<id>.wav 并重写 durations.json. 原版在 audio_v1_backup/.
"""
import os, sys, glob, wave, json, subprocess
import numpy as np

BUILD = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(BUILD, "audio")
WIN, THR = 0.020, 0.020          # 20ms 窗, RMS<0.020 视为静音 (与 insert_pauses GATE 同标定)
LONG, TARGET = 0.24, 0.185       # >=0.24s 的静音裁到 0.185s (atempo 后 ~0.179s)
FADE = 0.010
ATEMPO = 1.0323

def rd(p):
    w = wave.open(p, 'rb'); sr, ch = w.getframerate(), w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch).astype(np.float64)
    w.close(); return a, sr, ch

def wr(p, a, sr, ch):
    w = wave.open(p, 'wb'); w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(np.clip(np.round(a), -32768, 32767).astype(np.int16).tobytes()); w.close()

def silent_runs(a, sr):
    mono = np.abs(a).mean(axis=1) / 32768.0
    n = int(WIN * sr)
    nw = len(mono) // n
    rms = np.sqrt((mono[:nw*n].reshape(nw, n) ** 2).mean(axis=1))
    runs, start = [], None
    for i, v in enumerate(rms):
        if v < THR and start is None: start = i
        elif v >= THR and start is not None:
            runs.append((start * n, i * n)); start = None
    if start is not None: runs.append((start * n, nw * n))
    return [(s, e) for s, e in runs if (e - s) / sr >= LONG]

manifest = []
for p in sorted(glob.glob(os.path.join(AUD, "S*.wav")),
                key=lambda x: int(os.path.basename(x)[1:-4])):
    sid = os.path.basename(p)[:-4]
    a, sr, ch = rd(p)
    runs = silent_runs(a, sr)
    nf = int(FADE * sr)
    ramp = 0.5 * (1 - np.cos(np.linspace(0, np.pi, nf)))[:, None]
    cut = 0
    # 从后往前裁, 不打乱前面的索引; 跳过头尾 0.15s 内的段
    for s, e in reversed(runs):
        if s < int(0.15 * sr) or e > len(a) - int(0.15 * sr): continue
        keep = int(TARGET * sr)
        excess = (e - s) - keep
        if excess <= 0: continue
        mid = (s + e) // 2
        L, R = mid - excess // 2, mid + (excess - excess // 2)
        head, tail = a[:L].copy(), a[R:].copy()
        head[-nf:] *= ramp[::-1]; tail[:nf] *= ramp
        pad = head[-nf:] + tail[:nf]          # 交叠融合 10ms
        a = np.concatenate([head[:-nf], pad, tail[nf:]])
        cut += excess / sr
    tmp = p + ".trim.wav"
    wr(tmp, a, sr, ch)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp,
                    "-af", f"atempo={ATEMPO}", "-ar", "48000", "-ac", "2", p], check=True)
    os.remove(tmp)
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", p]).strip())
    manifest.append({"id": sid, "dur": round(d, 3)})
    print(f"{sid}: pauses_trimmed={len(runs)} cut={cut:.2f}s -> {d:.2f}s", flush=True)

json.dump(manifest, open(os.path.join(BUILD, "durations.json"), "w"), indent=2)
tot = sum(x["dur"] for x in manifest)
print(f"DONE 总长 {tot:.1f}s = {int(tot//60)}分{tot%60:.0f}秒")
