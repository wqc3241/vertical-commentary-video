#!/bin/bash
# 个人资产自检 — 全绿才能开工; 缺什么会指到 docs/ONBOARDING.md 对应步骤
[ -f personal.env ] && source personal.env
VOICE_REF="${VOICE_REF:-/Volumes/Storage/voice-clone/voice_ref_tennis_backup.wav}"
EMO_REF="${EMO_REF:-/Volumes/Storage/voice-clone/voice_ref_running_backup.wav}"
PERSONAL_ASSETS="${PERSONAL_ASSETS:-/Volumes/Storage/avatar-template/assets}"
ITTS_HOME="${ITTS_HOME:-/Volumes/Storage/indextts2}"
W2L_HOME="${W2L_HOME:-/Volumes/Storage/wav2lip-onnx-256}"
ok=0; bad=0
chk(){ if [ -e "$1" ]; then echo "  ✅ $2: $1"; ok=$((ok+1)); else echo "  ❌ $2: $1  → ONBOARDING $3"; bad=$((bad+1)); fi; }
echo "== 声音 =="
chk "$VOICE_REF" "音色参考" "第1步"
chk "$EMO_REF" "情感参考" "第1步"
echo "== 形象/品牌 =="
chk "$PERSONAL_ASSETS/template2_720.mp4" "数字人模板" "第2步"
chk "$PERSONAL_ASSETS/mask280.png" "圆形遮罩(仓库assets/可拷)" "第2步"
chk "$PERSONAL_ASSETS/ring292.png" "描边环(仓库assets/可拷)" "第2步"
[ -e "$PERSONAL_ASSETS/ending.mov" ] && echo "  ✅ 品牌片尾: $PERSONAL_ASSETS/ending.mov" || echo "  ⚪ 品牌片尾未配置(可选, 第3步)"
[ -e "$PERSONAL_ASSETS/ending_voice.wav" ] && echo "  ✅ 片尾口播" || echo "  ⚪ 片尾口播未配置(可选, 第3步)"
echo "== 引擎 =="
chk "$ITTS_HOME/checkpoints/config.yaml" "IndexTTS-2" "第4步"
chk "$W2L_HOME/checkpoints/wav2lip_256.onnx" "wav2lip-onnx" "第4步"
command -v whisper >/dev/null && { echo "  ✅ whisper CLI"; ok=$((ok+1)); } || { echo "  ❌ whisper CLI → 第4步"; bad=$((bad+1)); }
echo
[ $bad -eq 0 ] && echo "🟢 全部就绪, 按 SKILL.md 开工" || echo "🔴 缺 $bad 项 — 先完成 docs/ONBOARDING.md 再开工"
exit $bad
