#!/bin/bash
# 右下角口播数字人 (wav2lip-onnx-256) — 2026-08-03 从选拍指南会话的已验证管线移植。
# 用法: bash build/avatar_corner.sh <成片.mp4> <voice_master.wav> [模板偏移秒=0] [输出.mp4]
#   成片 = finalize_ending 之后的最终交付件 (含结尾卡)。
#   voice_master = build/audio_master.wav (纯口播 concat) — 数字人嘴型对口播, 不对混音。
#   V = voice_master 时长 = 结尾卡开始时刻; 数字人只出现在 0..V, 结尾卡无头像。
# 引擎/资产 (耐久位置):
#   引擎  /Volumes/Storage/wav2lip-onnx-256 (venv + wav2lip_256.onnx + matte_bg.py/RVM)
#   模板  /Volumes/Storage/avatar-template/assets/template2_720.mp4 (126.5s, 首尾各5s安静=循环接缝设计)
#   遮罩  同目录 mask280.png (圆) + ring292.png (描边环)
# 音频比模板长时引擎自动循环帧 (inference_onnxModel.py: i%len(frames)) — 不要自己做倒放回文
#   (ffmpeg reverse 会把整段吃进内存, 16G 机器必崩; 内置循环零内存成本, 接缝落在设计好的安静段)。
# 长片 (>2min) 用偏移 0 吃满整条模板; 短片系列各集错开偏移 (5/15/25/35/45) 避免头像动作雷同。
set -eu
BASE="$1"; AM="$2"; OFF="${3:-0}"; OUT="${4:-${BASE%.mp4}_数字人.mp4}"
W="${W2L_HOME:-/Volumes/Storage/wav2lip-onnx-256}"
AS="${PERSONAL_ASSETS:-/Volumes/Storage/avatar-template/assets}"
[ -f "$AS/template2_720.mp4" ] || { echo "⚠ 缺数字人模板 $AS/template2_720.mp4 — 个人形象件不随仓库分发, 录制见 docs/ONBOARDING.md 第2步"; exit 2; }
TMP="$(cd "$(dirname "$BASE")" && pwd)/build/avatar_tmp"; mkdir -p "$TMP"

V=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AM")
TPLD=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AS/template2_720.mp4")
SEGDUR=$(python3 -c "print(min($V+1.0, $TPLD-$OFF))")
echo "=== avatar V=${V}s seg=${SEGDUR}s off=${OFF} $(date +%H:%M:%S) ==="

# 1. 模板段 (720x1280) — 音频更长时给全段, 引擎内部循环
ffmpeg -v error -ss "$OFF" -t "$SEGDUR" -i "$AS/template2_720.mp4" \
  -c:v libx264 -crf 18 -preset fast -an -y "$TMP/seg.mp4"
# 1.5 驱动音频静默门控 (2026-08-09, 治"没说话嘴还动"): RMS<-40dB 持续>=120ms 的窗口清零,
#     wav2lip 不再被 TTS 底噪/呼吸尾音/室内底噪驱动。只影响对嘴驱动副本 — 成片音轨在第5步
#     从 $BASE 原样 copy, 听感零变化。GATE_LIP=0 跳过; 阈值 GATE_DB / GATE_MIN_MS 可调。
#     注意这只治一半: 模板素材本身张嘴的时刻, 静默输出仍会跟着微张(下巴在重绘框外泄露口型)
#     — 根治靠闭嘴聆听状态的模板, 见 docs/数字人模板录制指南.md「嘴型」条。
DRV="$AM"
if [ "${GATE_LIP:-1}" = "1" ]; then
  "$W/venv/bin/python" "$(cd "$(dirname "$0")" && pwd)/gate_lip_audio.py" "$AM" "$TMP/am_gated.wav"
  DRV="$TMP/am_gated.wav"
fi
# 2. 对嘴 (~8-9min/分钟音频, CPU) — 必须 cd 进引擎目录: 人脸检测模型是相对路径 ./insightface_func/models
cd "$W"
"$W/venv/bin/python" -W ignore "$W/inference_onnxModel.py" \
  --checkpoint_path "$W/checkpoints/wav2lip_256.onnx" \
  --face "$TMP/seg.mp4" --audio "$DRV" --outfile "$TMP/avraw.mp4" --pads 0 10 0 0
# 3. 裁成 720x720 方形 (胸上构图, y=193 对准脸部)
ffmpeg -v error -i "$TMP/avraw.mp4" -vf "crop=720:720:0:193" -an \
  -c:v libx264 -crf 16 -preset fast -y "$TMP/avsq.mp4"
# 4. RVM 抠像 → 浅蓝底 BDD8EE
"$W/venv/bin/python" "$W/matte_bg.py" "$TMP/avsq.mp4" "$TMP/avblue.mp4" BDD8EE
# 5. 合成: 186px 圆 + 描边环; 圆内画面默认提亮 (2026-08-27 用户 standing rule:
#    数字人模板偏暗, 提高亮度/对比让脸更清楚 — 与封面头像同款处理, 封面用的 PIL ×1.22 亮度;
#    视频侧 eq brightness=0.09 contrast=1.06 saturation=1.05 为等效保守档, env AV_BRIGHT/AV_CONTRAST/AV_SAT 可调), 右下角 (834,1634)/(829,1629) — 2026-08-03 用户校准:
#    280px 在 (772,1616) 手机上会被屏幕圆角/进度条卡掉, 缩 1/3 并左移上移
ffmpeg -v error -t "$V" -i "$BASE" -i "$TMP/avblue.mp4" \
  -loop 1 -i "$AS/mask280.png" -loop 1 -i "$AS/ring292.png" \
  -filter_complex "[1:v]eq=brightness=${AV_BRIGHT:-0.09}:contrast=${AV_CONTRAST:-1.06}:saturation=${AV_SAT:-1.05},scale=186:186[av];[2:v]scale=186:186[mk];[av][mk]alphamerge[avc];[0:v][avc]overlay=834:1634[t1];[3:v]scale=196:196[rg];[t1][rg]overlay=829:1629[out]" \
  -map "[out]" -an -t "$V" -c:v libx264 -crf 18 -preset medium -r 60 -y "$TMP/partA.mp4"
# ⚠ 输出侧 -t 必须有: -loop 1 的 PNG 是无限流, 主输入 EOF 后 framesync 重复末帧, 滤镜图永不终止
#   (2026-08-03 实测: 只有输入侧 -t 时, 10s 素材跑出 7 分钟+的定格输出, 2h 编了 2GB)
ffmpeg -v error -ss "$V" -i "$BASE" -an -c:v libx264 -crf 18 -preset medium -r 60 -y "$TMP/partB.mp4"
printf "file '%s'\nfile '%s'\n" "$TMP/partA.mp4" "$TMP/partB.mp4" > "$TMP/cl.txt"
ffmpeg -v error -f concat -safe 0 -i "$TMP/cl.txt" -i "$BASE" \
  -map 0:v -map 1:a -c:v copy -c:a copy -movflags +faststart -y "$OUT"
echo "=== DONE -> $OUT $(date +%H:%M:%S) ==="
