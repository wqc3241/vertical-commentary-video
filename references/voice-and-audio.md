# Voiceover & audio

Three ways to get narration. **Default to the user's cloned voice; current engine is IndexTTS-2**
按 SKILL.md 的整句/语义段落方式生成；F5 是点名音色或引擎故障时的后备，不自行切回旧逐短句模式。

## 批准文本、断句与读音门（所有配音引擎必读）

1. **一份 canonical 文本。** 批准稿里的 `vo` 标点、段落和明确的语义停顿是口播真源。
   按完整句/语义段落生成，保留句内语气；不能按字幕宽度、字数、卡片切换或镜头时长切碎句子。
   CAPTIONS 只是显示换行，数字用阿拉伯形式；停顿标注另存，不把 `/`、拼音注释或“停顿”念出来。
   必须切批时选择已批准的句末/语义边界；不能截在姓名、数量词、主谓或紧密短语中间。
2. **先判读法再配音。** 逐稿抽取数字、人名/昵称、外文缩写、多音字，按语境写出显示形式→口播形式。
   名称沿用用户确定的叫法，仍需确认正确声调；新姓名用可靠词典、本人/官方读音等依据核实，不凭汉字外观猜。
   未解决的读音列明并保留，正式整批配音前解决。

   | 显示与语境 | 口播示例 | 不能混用 |
   |---|---|---|
   | 只拿2分（数量） | 只拿两分 | 二分 |
   | 2个破发点、2次 | 两个破发点、两次 | 全局机械转成二 |
   | 局/盘比分2比1 | 二比一 | 自动替换所有二为两 |
   | 第2盘、第2名 | 第二盘、第二名 | 第两盘 |
   | 单盘6-3、抢七7-2 | 六比三、七比二 | 数字逐个读/英语读数 |
   | 2026年、10月2日 | 二零二六年、十月二日 | 按普通数量读年份 |
   | 15%、1.5小时 | 百分之十五、一个半小时 | 脱离单位读数 |

   这是语境示例，不是全局替换表；“二分之一”等固定表达保留其正确读法。排名还要核查排名种类与统计日期。
   在已有脚本/核查记录中保存关键读法、依据及TTS输入；拼音纠正只改变读法输入，不偷偷更换昵称或原句。
3. **完整句短样。** 两个制作门通过后，先合成含比分、数量词、关键姓名和句末停顿的代表性完整句/短段，
   核对实际发音、重音和停顿后再跑整批；正确的模板读法不能代替新文本检查。试听争议保留2–3个有依据候选。
4. **逐场景实际声音验收。** 数字边界、两/二、前后鼻音、多音字逐项对照；ASR可能把“两分/二分”同归为2分，
   也可能把错声调转成同一人名，归一化/拼音相似度绿灯不是发音正确证据。不要把这两类错误归一化掉。
   听每个完整句以及场景衔接，检查词内误停、句末漏停、切音、语调复位和赶字；不能只听独立数字小样。
   本次工具无法听音时明确尚未核验，给出文件和秒段供用户验收，不声称“已听过/发音已确认”。
5. **局部修复。** 先区分事实/文字错、读法错、韵律错和ASR误报；只修受影响句/语义段。修读法保存可追踪映射，
   修文案同步 canonical 源；重建该段字幕、母带、受影响预览和素材窗口，不能拿旧母带发布。
   没有获得实际声音通过记录时，不把机器转写通过当成 `publish_ready`。

## A) F5 cloned voice — 后备引擎，用户自己的声音
A permanent home lives at `/Volumes/Storage/voice-clone/`:
- `venv/` — Python 3.13 venv with `f5-tts`
- `clone.py` — the engine (modes: `say "文本" out.wav` | `scenes <build_dir>`)
- `voice_ref.wav` + `voice_ref_text.txt` — the user's reference clip and its exact transcript
- `hf-cache/` — the downloaded F5-TTS model

**Generate with the ANTI-LEAK wrapper — never bare `clone.py scenes` (2026-07, 7 recurrences):**
the default `voice_ref.wav` deterministically leaks its tail "尤其是他的叔叔托尼" onto clip starts
(sometimes MID-clip at batch joins, and it can FUSE with and corrupt a real number/word);
`voice_ref_padded.wav` does NOT fix it. The wrapper uses the known-clean 7.98s
`voice_ref_tennis_backup.*`, then per clip: synth → whisper(small) → reject leak-probe hits /
sim<0.80 / ASR≫script → retry ≤4, keep best:
```bash
VOICE_SPEED=0.85 /Volumes/Storage/voice-clone/venv/bin/python "$PROJ/build/regen_tts.py"
python "$PROJ/build/check_tts.py"   # report; expect FALSE alarms: traditional-script output (sim can
                                    # hit 0.55), homophones (温王/女丹/科威托瓦/手筋), whisper turning
                                    # audio "一千" into "1000" — eyeball diffs, don't re-record on ratio alone
```
(If a child python dies with `Fatal Python error: config_init_hash_seed`, strip/override
`PYTHONHASHSEED` — F5-TTS/this shell pollutes it; regen_tts.py already strips it for whisper.)
This writes `build/audio/<id>.wav` (loudness-normalized, 48k stereo) + `build/durations.json`.
First call loads the model (~slow); the rest of the scenes are fast in the same process.
**`VOICE_SPEED`** (env, default 1.0) controls pace; **0.85 reads more deliberately** — the default
clone tends to rush. **Write numbers in `vo` as CHINESE numerals** (六比三, 二零二六) or F5-TTS reads
them as English digits. To re-voice just a couple of scenes, call `clone.synth(text, raw)` from a
small script and re-run `caption_times.py` (its staleness check re-transcribes the changed ones).

One-off line: `... clone.py say "要合成的中文" /tmp/x.wav`.

**Names / polyphones can be mis-voiced — test, don't assume (2026-07: "德约"→"德于").** F5-TTS read the
Djokovic nickname **德约** (dé-**yuē**) as **dé-yú** ("等于/德于") — the polyphone 约 came out wrong, and the user
caught it. When a name/term matters, verify the intended reading first, synth a few evidence-based candidates in a carrier
sentence, and listen; ASR is only an auxiliary check (wrong reading shows up as a different homophone — 德于/德月/德腰). Fixes that
work: use a spelling the model gets right (here the user's other nickname **老德** lǎo-dé, which also fit the
"39-year-old veteran" theme), or the full name. **Change BOTH `vo` and the matching CAPTION** so audio and text
stay consistent (never leave the caption showing the old name). This is separate from the reference-clip **leak**
bug — see the [[cloned-voice-transcript-check]] memory / `voice_ref_tennis_backup.*` fix.

**If the home is missing**, recreate it:
```bash
export UV_CACHE_DIR=/Volumes/Storage/.uvcache
uv venv --python 3.13 /Volumes/Storage/voice-clone/venv
uv pip install --python /Volumes/Storage/voice-clone/venv/bin/python f5-tts
# restore the engine + reference clip from the skill assets:
cp ~/.claude/skills/vertical-commentary-video/assets/clone.py           /Volumes/Storage/voice-clone/
# 音色参考属个人声音数据, 不随仓库分发 — 自己的参考按 docs/ONBOARDING.md 第1步录制,
# 存放于 /Volumes/Storage/voice-clone/ (或 personal.env 里自定义的位置)
```

**Better reference = better clone.** A clean, quiet 30–60s sample lifts quality. To re-clone from a
new reference: cut a clean clip (ends on a pause), write its exact transcript next to it, and point
`VOICE_REF`/`VOICE_REF_TEXT` at them (or overwrite the files in the home).

**Higher fidelity tier:** if the user wants it even closer (emotional emphasis, prosody), fine-tune
**GPT-SoVITS** on a few minutes of their audio — more setup, best Chinese results. Offer it; don't
default to it.

Note: F5-TTS has a buggy interpreter teardown (`config_init_hash_seed`) that fires AFTER the wav is
written — `clone.py` hard-exits 0 to hide it. The output is fine.

## 断句/语气 audit — 生成后、字幕前

所有引擎都以本文件开头的批准文本/读音门验收；模型输出的随机停顿不覆盖批准断句。
ffmpeg `silencedetect` 可找可疑停顿，Whisper/difflib 可辅助定位；停顿须映射到批准 `vo` 的语义边界，
不能仅依据 CAPTIONS 换行。逗号允许自然轻连读，句末应有合适停顿/语气收束；不强制所有句子相同静音长度。

旧 `fix_pauses.py`/`fix_pauses_lib.py`/`regen_fix.py` 以字幕行界为代理且可能自动重录，只在已确认行界
与语义边界一致的 F5 后备项目中适用。未确认时只读检查，禁止循环自动重录直到“行内静音为零”。
旧 `insert_pauses.py` 是 F5 的局部后处理工具，不默认用于 IndexTTS 整段模式；确需修复时先定位真实句末，
不得切进字中间或用等长静音掩盖断句错误，修后听接缝并更新 durations/captions/母带/受影响预览。
任何预览之后的重配音都要重建 `audio_master.wav`，防止旧录音随成片交付。

## Ambient 轻原声 — the deliverable ALWAYS carries it (2026-07 standard)
The final video beds each clip's ORIGINAL audio (ball strikes, crowd, ceremony speech) under the
narration. **Final gain 0.15** (2026-07-16: 0.30 masked the voice — user had it halved; 0.14-0.15 with
loudnorm'd voice on top is right; previews may run 0.30 for review). Only REAL venue sound qualifies —
produced IG reels' music beds go in `scenes.py MUTE_AMBIENT` (honored by preview_parts + assemble_ambient).
For TTS voice, build the voice master first (concat `build/audio/<id>.wav` in scene order →
`build/audio_master.wav`), then:
```bash
python build/assemble_ambient.py build/audio_master.wav 0.15    # or build/voice/full48k.wav for a recorded take
```
- Silent sources (photo `ig_ph_*` clips, muted reels) are auto-padded with silence — `seg_audio()`
  probes for an audio stream first; keep that fallback when copying the script forward.
- Windows containing real speech (victory speech, on-court interview) are a feature: pick the window
  so HER actual words sit under the matching narration beat (whisper the source to time-locate quotes).
- **Segment previews use the same mix** so the user reviews final sound: `preview_parts.py 0.30`
  → `预览_A..E.mp4` (per-part video + that part's voice + ambient). Rebuild only affected parts after
  fixes: `preview_parts.py 0.30 BCD`. Its per-scene ambient cache lives in `build/amb/` — delete a
  scene's wav there if you retimed its window, or it reuses the stale extract.

## B) User records the script themselves (single take)
They'll provide e.g. `build/voice/full.m4a` (Voice Memos temp paths vanish — copy it immediately).
Make the cuts follow THEIR pacing by aligning their words to the script:
```bash
ffmpeg -y -i build/voice/full.m4a -ar 16000 -ac 1 build/voice/full16k.wav
ffmpeg -y -i build/voice/full.m4a -ar 48000 -ac 2 build/voice/full48k.wav
whisper build/voice/full16k.wav --language Chinese --model small --word_timestamps True \
        --output_format json --output_dir build/voice --fp16 False
python build/align.py                      # -> build/durations.json (real pacing)
python build/render.py all
python build/render.py assemble-voice build/voice/full48k.wav
```
`align.py` uses difflib so whisper homophone slips (他/她, 赢/英) don't matter — it aligns on timing.

## C) Quick robotic draft (no clone)
`python build/tts_say.py` (macOS `say`, voice Tingting). Only for throwaway timing drafts.

## Sync spot-check (for recorded takes)
Confirm the on-screen scene matches the spoken words. For sample times, compare the whisper word at
time `t` against which scene the cumulative `durations.json` places at `t` and its chip — they
should agree. A mismatch means a bad alignment boundary; nudge and re-run.

## Captions — word-exact is the DEFAULT
```bash
python build/caption_times.py        # -> build/captions.json (each line timed to the spoken words)
```
`caption_times.py` whispers each scene's audio and aligns the **display lines** (`CAPTIONS[id]` in
scenes.py — the user's own 断句, with DIGITS like 6-3) to the spoken words. It converts digits→Chinese
internally so digit captions still align to Chinese-numeral audio. **Each caption line must be the
same words as the spoken `vo`** (only numerals differ) — if you shorten/reword a line, alignment
collapses (middle lines bunch up, last line stretches). If `captions.json` is absent, render falls
back to proportional timing.

**Re-record cache:** transcripts cache in `build/capjson/`. The script re-transcribes any scene whose
wav is newer than its cache, so a re-record is picked up automatically. (If in doubt, `rm -rf
build/capjson` and re-run.)


## 英文缩写读音 + 读法仲裁(2026-07-22 定稿,NCAA网球 项目)
- **ALL-CAPS 缩写在 `vo` 里一律写成顿号分隔的逐字母**:NCAA → `N、C、A、A`,TCU → `T、C、U`。
  字幕仍显示 NCAA/TCU。已被用户否掉的写法:汉字注音(恩西诶诶,"听感不像英文字母")、连写 NCAA(乱拼)、
  空格 `N C A A`(不稳)。regen_tts 的缩写门会校验每个字母都被 whisper 听到(听成 "NCA" 即废稿重掷)。
- **读音争议先核实，再试听。** 完整句候选 WAV 放项目目录，记录依据及具体秒段；本次无法听音时请用户核验，不能盲猜。
- **“生硬/音调不对”**：检查批准断句、语义重音和句内连贯性；有根据地局部重录。ASR相似度不衡量自然度，
  不把最高sim或固定五稿当通过标准。
- 转写核对的假警报清单新增:whisper 把"一百"写成"100"(归一化里做 一零零→一百),繁体输出(归一化表),
  顿号字母被写成 "NCAA"(这是**正确**信号,说明读音就是字母音)。

## 16G Mac 跑 F5 的防死机跑法(2026-07-21/22,连续 3 次整机死机后的定式)
- 前缀:`PYTHONHASHSEED=0 VOICE_SPEED=0.85 PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7 OMP_NUM_THREADS=4`
  + `caffeinate -i nice -n 10`。watermark=0.7 会让 torch MPS 初始化失败回落 **CPU** —— 这是特性不是
  bug:每稿慢一点(~2.5min)但整机不再被统一内存挤爆;不要"修好"它。
- **驱动脚本必须 `nohup ... & disown` 完全脱离会话**——Claude 会话退出/应用重启曾三次带走后台任务。
  逐场景独立进程(`for sid in ...; do python regen_tts.py $sid; done`),崩一段只损一段;
  regen_tts 的 keep-existing 分支保证 durations.json 每次都完整。
- 监控用完成标志文件(`build/xxx_done`),**启动新一轮前必须先删旧标志**(陈旧标志会造成完成误报);
  监视器可能因 TCC 读不到卷而沉默——用 Desktop Commander 亲自查真实状态。
- macOS 可能中途撤销终端对可移动卷的授权(整卷 EPERM、`stat` 能过 `ls` 不能过):数据没丢,
  改走 Desktop Commander 通道继续,并提醒用户去 系统设置→隐私与安全性 恢复授权。
