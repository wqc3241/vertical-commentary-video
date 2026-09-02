#!/bin/bash
# 右下角口播数字人 (wav2lip-onnx-256) — 贴纸样式 = 默认 (2026-09-02 用户拍板; 老德美网一轮游 2026-08-31 首用)。
#   不裁圆、无底色、无边框: 720x960 上半身取景 → RVM 抠透明 + 轮廓白描边(14px, 缩放后~5px)
#   → 270x360 直接叠画面右下 (790,1568), 躯干贴底出画; 人脸提亮已烘进 matte_sticker.py。
#   旧的 186px 圆框+描边环版本保留在 avatar_corner_circle.sh (用户点名要圆框时才用)。
# 用法: bash build/avatar_corner.sh <成片.mp4> <voice_master.wav> [模板偏移秒=0] [输出.mp4]
#   成片 = finalize_ending 之后的最终交付件 (含结尾卡)。
#   voice_master = build/audio_master.wav (纯口播 concat) — 数字人嘴型对口播, 不对混音。
#   V = voice_master 时长 = 结尾卡开始时刻; 数字人只出现在 0..V, 结尾卡无头像。
# 引擎/资产 (耐久位置):
#   引擎  /Volumes/Storage/wav2lip-onnx-256 (venv + wav2lip_256.onnx + rvm_mobilenetv3_fp32.onnx)
#   模板  /Volumes/Storage/avatar-template/assets/template2_720.mp4 (126.5s, 首尾各5s安静=循环接缝设计)
# 音频比模板长时引擎自动循环帧 (inference_onnxModel.py: i%len(frames)) — 不要自己做倒放回文
#   (ffmpeg reverse 会把整段吃进内存, 16G 机器必崩; 内置循环零内存成本, 接缝落在设计好的安静段)。
# 长片 (>2min) 用偏移 0 吃满整条模板; 短片系列各集错开偏移 (5/15/25/35/45) 避免头像动作雷同。
# ⚠ 两条 2026-09-01 (Kids Day 项目) 实踩:
#   ① wav2lip 引擎内部拼 ffmpeg 命令不给路径加引号 — 项目目录含空格时 --outfile 被截断, 整步静默失败。
#      所以工作目录固定放在无空格路径 (AVATAR_TMP 可覆盖), 且 BASE/AM 先转成绝对路径再 cd 进引擎目录。
#   ② 合成滤镜里任何无限流 (-loop 1 的 PNG) 会让 ffmpeg 在主输入 EOF 后永不终止 (卡在 V-1s 处, 编码器
#      lookahead 让进度停在 133.7/134.7)。贴纸版没有 PNG 输入; 贴纸 mov 比 V 短的 ~0.1s 用 tpad 克隆末帧补齐。
set -eu
_abs(){ cd "$(dirname "$1")" && printf '%s/%s' "$(pwd)" "$(basename "$1")"; }
BASE="$(_abs "$1")"; AM="$(_abs "$2")"; OFF="${3:-0}"; OUT="${4:-${BASE%.mp4}_数字人.mp4}"
W="${W2L_HOME:-/Volumes/Storage/wav2lip-onnx-256}"
AS="${PERSONAL_ASSETS:-/Volumes/Storage/avatar-template/assets}"
BD="$(cd "$(dirname "$0")" && pwd)"
[ -f "$AS/template2_720.mp4" ] || { echo "⚠ 缺数字人模板 $AS/template2_720.mp4 — 个人形象件不随仓库分发, 录制见 docs/ONBOARDING.md 第2步"; exit 2; }
TMP="${AVATAR_TMP:-/Volumes/Storage/tmp/avatar_$(printf '%s' "$BASE" | md5 | cut -c1-8)}"; mkdir -p "$TMP"
case "$TMP" in *" "*) echo "⚠ 工作目录含空格: $TMP — wav2lip 引擎会截断路径, 请用 AVATAR_TMP 指定无空格目录"; exit 2;; esac

V=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AM")
TPLD=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$AS/template2_720.mp4")
SEGDUR=$(python3 -c "print(min($V+1.0, $TPLD-$OFF))")
echo "=== avatar-sticker V=${V}s seg=${SEGDUR}s off=${OFF} tmp=$TMP $(date +%H:%M:%S) ==="

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
  "$W/venv/bin/python" "$BD/gate_lip_audio.py" "$AM" "$TMP/am_gated.wav"
  DRV="$TMP/am_gated.wav"
fi
# 2. 对嘴 (~8-9min/分钟音频, CPU) — 必须 cd 进引擎目录: 人脸检测模型是相对路径 ./insightface_func/models
cd "$W"
"$W/venv/bin/python" -W ignore "$W/inference_onnxModel.py" \
  --checkpoint_path "$W/checkpoints/wav2lip_256.onnx" \
  --face "$TMP/seg.mp4" --audio "$DRV" --outfile "$TMP/avraw.mp4" --pads 0 10 0 0
[ -s "$TMP/avraw.mp4" ] || { echo "⚠ wav2lip 没有产出 $TMP/avraw.mp4"; exit 3; }
echo "=== wav2lip done $(date +%H:%M:%S) ==="
# 3. 上半身取景 720x960 (头顶留白 ~y120: 头+肩+胸; 麦克风在画内属模板本色)
ffmpeg -v error -i "$TMP/avraw.mp4" -vf "crop=720:960:0:120" -an \
  -c:v libx264 -crf 16 -preset fast -y "$TMP/avub.mp4"
# 4. RVM 透明抠像 + 白描边 → ProRes4444 alpha (亮度/对比已烘入: brightness+0.09 contrast×1.06, 同封面头像提亮规矩)
"$W/venv/bin/python" "$BD/matte_sticker.py" "$TMP/avub.mp4" "$TMP/avsticker.mov" "${STICKER_STROKE:-14}"
echo "=== matte done $(date +%H:%M:%S) ==="
# 5. 合成 0..V: 贴纸缩到 270x360 直叠右下 (790,1568), 无遮罩无环无底卡;
#    贴纸流先 tpad 克隆末帧 3s 兜底(它比 V 短 ~0.1s), 输出侧 -t V 收口; 无任何无限流输入。
ffmpeg -v error -i "$BASE" -i "$TMP/avsticker.mov" \
  -filter_complex "[1:v]tpad=stop_mode=clone:stop_duration=3,scale=${STICKER_W:-270}:${STICKER_H:-360}[p];[0:v][p]overlay=${STICKER_X:-790}:${STICKER_Y:-1568}[out]" \
  -map "[out]" -an -t "$V" -c:v libx264 -crf 18 -preset medium -r 60 -y "$TMP/partA.mp4"
ffmpeg -v error -ss "$V" -i "$BASE" -an -c:v libx264 -crf 18 -preset medium -r 60 -y "$TMP/partB.mp4"
printf "file '%s'\nfile '%s'\n" "$TMP/partA.mp4" "$TMP/partB.mp4" > "$TMP/cl.txt"
ffmpeg -v error -f concat -safe 0 -i "$TMP/cl.txt" -i "$BASE" \
  -map 0:v -map 1:a -c:v copy -c:a copy -movflags +faststart -y "$OUT"
echo "=== DONE -> $OUT $(date +%H:%M:%S) ==="
