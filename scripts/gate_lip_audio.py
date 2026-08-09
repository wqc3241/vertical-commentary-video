# -*- coding: utf-8 -*-
"""数字人驱动音频静默门控 (2026-08-09) — 解决"没说话时嘴还在动"。

wav2lip 把 TTS 底噪 / 呼吸尾音 / insert_pauses 填的室内底噪当成微弱语音, 静默段嘴唇会持续微动。
本脚本只处理喂给 wav2lip 的**驱动副本**: 把 RMS 低于阈值且持续足够长的窗口清零(数字零 = 嘴闭合),
两端 15ms 余弦融合防 mel 突变。成片音轨走 avatar_corner.sh 第5步的 -map 1:a, 与此无关, 听感零变化。

用法: python gate_lip_audio.py <in.wav> <out.wav>
环境旋钮: GATE_DB (默认 -40, 语音 -20~-12 / TTS底噪 -55以下, 别高过 -32 以免吃掉轻声字)
          GATE_MIN_MS (默认 120, 短于此的低能量不清零 — 保住字间自然过渡)
"""
import sys, os, subprocess, struct, math

IN, OUT = sys.argv[1], sys.argv[2]
GATE_DB = float(os.environ.get("GATE_DB", "-40"))
MIN_MS = float(os.environ.get("GATE_MIN_MS", "120"))
SR = 16000  # wav2lip 的工作采样率, 门控直接在这个平面做

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", IN, "-ac", "1", "-ar", str(SR),
                      "-f", "f32le", "-"], capture_output=True, check=True).stdout
n = len(raw) // 4
x = list(struct.unpack(f"<{n}f", raw))

hop = int(SR * 0.010)          # 10ms 帧
thr = 10 ** (GATE_DB / 20)
nf = (n + hop - 1) // hop
low = []
for i in range(nf):
    seg = x[i * hop:(i + 1) * hop]
    rms = math.sqrt(sum(v * v for v in seg) / max(len(seg), 1))
    low.append(rms < thr)

min_frames = max(1, int(MIN_MS / 10))
ramp = int(SR * 0.015)         # 15ms 余弦融合
gated = 0.0
intervals = []
i = 0
while i < nf:
    if low[i]:
        j = i
        while j < nf and low[j]:
            j += 1
        if j - i >= min_frames:
            a, b = i * hop, min(j * hop, n)
            for k in range(a, b):
                if k < a + ramp:
                    g = 0.5 * (1 + math.cos(math.pi * (k - a) / ramp))      # 1→0
                elif k >= b - ramp:
                    g = 0.5 * (1 - math.cos(math.pi * (k - (b - ramp)) / ramp))  # 0→1
                else:
                    g = 0.0
                x[k] *= g
            gated += (b - a) / SR
            intervals.append((round(a / SR, 2), round(b / SR, 2)))
        i = j
    else:
        i += 1

pcm = struct.pack(f"<{n}f", *x)
p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1",
                    "-i", "-", "-c:a", "pcm_s16le", "-y", OUT], input=pcm, check=True)
total = n / SR
print(f"gate_lip_audio: {total:.1f}s 中清零 {gated:.1f}s ({100*gated/total:.0f}%), "
      f"阈值 {GATE_DB}dB / 最短 {MIN_MS:.0f}ms, 共 {len(intervals)} 段")
for a, b in intervals:
    print(f"  [{a:6.2f} - {b:6.2f}] {b-a:.2f}s")
