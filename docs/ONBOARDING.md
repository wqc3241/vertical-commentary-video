# 新用户开箱（一次性）— 用你自己的声音和形象跑通整条流水线

> 本仓库**不含任何人的声音或形象数据**。声音参考、数字人模板、品牌片尾都属于个人数据，
> 只存在你自己的电脑上（`personal.env` 指定的位置），并被 `.gitignore` 挡在仓库外。
> **在生成第一条视频之前，必须先完成下面 1-3 步的录制** —— 否则流水线会在对应环节
> 停下来并把你带回这份文档。

## 0. 准备个人配置
```bash
cp personal.env.example personal.env   # 填入你的路径; personal.env 永不提交
bash scripts/check_personal_assets.sh  # 随时自检缺什么
```

## 1. 录你的声音（两段，各 20-30 秒）
| 文件 | 内容 | 用途 |
|---|---|---|
| `voice_ref.wav` | **平稳叙述**：用正常语速念一段与你频道主题相关的稿子，咬字清楚，句间自然停顿 | 音色参考（决定"你听起来是谁"）|
| `emo_ref.wav` | **自然聊天**：像给朋友讲一件让你兴奋的事，语气起伏越自然越好，忘词就自由发挥 | 情感参考（决定"你说话的劲儿"）|

要点：安静房间、手机距嘴 20-30cm、44.1kHz 以上、开头结尾留 1 秒安静；
不要念得像播音——**你平时怎么说话就怎么录**。存到 `personal.env` 里 `VOICE_REF`/`EMO_REF` 指向的路径。

## 2. 录你的数字人模板（2-3 分钟竖屏）
完整规范见 `docs/数字人模板录制指南.md`（构图/光线/背景三忌/眼神/台词范例）。
核心三条：手机竖屏胸上景、全程机位不动、**开头结尾各留 5 秒不说话**（循环接缝用）。
录完转 720p 放到 `$PERSONAL_ASSETS/template2_720.mp4`：
```bash
ffmpeg -i 你的原片.mov -vf "scale=720:1280" -r 30 -c:v libx264 -crf 18 -an template2_720.mp4
```

## 3. 做你的品牌片尾（可选但推荐）
- `ending.mov`：1080×1920 的 2-3 秒"点赞关注"卡（拿你的头像+频道名做一张即可）
- `ending_voice.wav`：你的快速口播（管线可以用你在第 1 步的声音自动合成，如
  "关注我，了解更多XX内容"，见 SKILL.md 片尾语音节）
没有这两件时流水线不会报错——只是成片没有片尾。

## 4. 安装引擎（一次性）
- **IndexTTS-2**（配音）: `git clone` 官方 repo → `uv sync` → `hf download IndexTeam/IndexTTS-2`
  → 路径填入 `ITTS_HOME`；16G 内存机器务必 CPU 模式（脚本默认）
- **wav2lip-onnx-256**（数字人对嘴）: 装好后路径填入 `W2L_HOME`
- **whisper CLI**（质检门）: `brew install openai-whisper` 或 pip 装，保证 `whisper` 在 PATH
- ffmpeg / Python3 / numpy / pypinyin（装进 ITTS venv）

## 5. 自检通过即开工
```bash
bash scripts/check_personal_assets.sh   # 全绿后, 按 SKILL.md 从步骤 0 开始做片
```
