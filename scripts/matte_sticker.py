#!/usr/bin/env python
"""RVM matte -> transparent cutout with WHITE silhouette stroke (sticker style).
Outputs ProRes 4444 with alpha. Brightness/contrast baked into the person pixels.

Usage: matte_sticker.py <in.mp4> <out.mov> [stroke_px=14]
"""
import sys, subprocess, os
import numpy as np
import cv2
import onnxruntime as ort

src_path, out_path = sys.argv[1], sys.argv[2]
stroke = int(sys.argv[3]) if len(sys.argv) > 3 else 14

W2L = os.environ.get("W2L_HOME", "/Volumes/Storage/wav2lip-onnx-256")
sess = ort.InferenceSession(
    os.path.join(W2L, "checkpoints/rvm_mobilenetv3_fp32.onnx"),
    providers=["CPUExecutionProvider"])

cap = cv2.VideoCapture(src_path)
fps = cap.get(cv2.CAP_PROP_FPS)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

ff = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
     "-r", f"{fps}", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
     "-pix_fmt", "yuva444p10le", "-y", out_path],
    stdin=subprocess.PIPE)

rec = [np.zeros([1, 1, 1, 1], dtype=np.float32)] * 4
dsr = np.array([0.4], dtype=np.float32)
kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (stroke * 2 + 1, stroke * 2 + 1))

n = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    src = rgb.transpose(2, 0, 1)[None]
    fgr, pha, *rec = sess.run(None, {
        "src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
        "downsample_ratio": dsr})
    fgr = fgr[0].transpose(1, 2, 0)
    pha = pha[0, 0]
    # bake the corner-avatar brightening (standing rule) into the person pixels
    fgr = np.clip((fgr - 0.5) * 1.06 + 0.5 + 0.09, 0.0, 1.0)
    # white sticker stroke = dilated alpha ring around the person
    ring = cv2.dilate(pha, kern)
    a_out = np.clip(ring, 0.0, 1.0)
    p3 = pha[:, :, None]
    premult = fgr * p3 + 1.0 * (a_out[:, :, None] - p3)   # white ring under person
    a3 = np.maximum(a_out[:, :, None], 1e-6)
    straight = np.clip(premult / a3, 0.0, 1.0)
    bgra = np.dstack([cv2.cvtColor((straight * 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                      (a_out * 255).astype(np.uint8)])
    ff.stdin.write(bgra.tobytes())
    n += 1
    if n % 50 == 0:
        print(f"{n}/{N}", flush=True)

cap.release()
ff.stdin.close()
ff.wait()
print(f"done {n} frames -> {out_path}")
