# Voiceover & audio

Three ways to get the narration. **Default to the cloned voice.**

## A) Cloned voice (default) — F5-TTS, the user's own voice
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
caught it. When a name/term matters, synth 3-4 candidate spellings in a carrier sentence, whisper each, and pick
the one whose ASR comes back right (wrong reading shows up as a different homophone — 德于/德月/德腰). Fixes that
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
cp ~/.claude/skills/vertical-commentary-video/assets/voice_ref.wav      /Volumes/Storage/voice-clone/
cp ~/.claude/skills/vertical-commentary-video/assets/voice_ref_text.txt /Volumes/Storage/voice-clone/
```

**Better reference = better clone.** A clean, quiet 30–60s sample lifts quality. To re-clone from a
new reference: cut a clean clip (ends on a pause), write its exact transcript next to it, and point
`VOICE_REF`/`VOICE_REF_TEXT` at them (or overwrite the files in the home).

**Higher fidelity tier:** if the user wants it even closer (emotional emphasis, prosody), fine-tune
**GPT-SoVITS** on a few minutes of their audio — more setup, best Chinese results. Offer it; don't
default to it.

Note: F5-TTS has a buggy interpreter teardown (`config_init_hash_seed`) that fires AFTER the wav is
written — `clone.py` hard-exits 0 to hide it. The output is fine.

## 断句/语气 audit — MANDATORY after TTS, before captions (2026-07-16; produced "完成度非常高" audio)
F5-TTS occasionally inserts a prosody break MID-phrase ("深圳|女孩", "李慧|说") even when the transcript
verifies clean. Whisper word-gap timestamps CANNOT catch these (the gaps hide inside word spans) — audit
the ACOUSTICS instead. `fix_pauses.py` (+`fix_pauses_lib.py`, `regen_fix.py` for targeted re-takes), run
with the voice-clone venv:
1. **Detect real pauses**: ffmpeg `silencedetect=noise=-34dB:d=0.24` per scene wav (tightened 2026-07-21).
2. **Map pauses to the 断句**: whisper word timestamps + difflib `SequenceMatcher` align the transcript
   to the caption lines (survives digit/homophone/traditional-script drift), giving each caption-line
   boundary a time. Boundary matching must be EXACT — a ±1-word tolerance masked a real "李慧|说" break.
3. **Judge**: a pause AT a "/" line boundary = correct prosody, keep. A pause INSIDE a line = break →
   regenerate that scene (same anti-leak flow as regen_tts: synth → whisper-verify → keep best take)
   until the audit reports ZERO intra-line pauses.
Upstream rules that make this work: clauses ≤20 chars, separated by ,。 ONLY — **never write "/"
breath markers in `vo`**: F5 vocalizes each slash as a junk syllable (2026-07-21, one scene grew 14
extra syllables; regen_tts now strips "/" defensively). The audit's boundaries come from CAPTIONS
lines. Letter-gaps inside a 顿号-spelled acronym (N、C、A、A) are legitimate micro-pauses —
regen_tts exempts gaps whose context contains a latin letter, or the zero-gap gate would kill every take.
If any scene is regenerated after previews, REBUILD `build/audio_master.wav` (concat in scene order)
before final assembly — a stale master silently ships the old takes.

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
- **你没有耳朵——读音争议不要盲猜**:用 `clone.py say` 批量生成 3-4 种候选读法的同句试听 wav
  (放项目根目录,命名 `XX读法试听1_描述.wav`),让用户点选,一轮定案。
- **"生硬/音调不对" 类反馈**:读法本身对、韵律差 → 把 regen 的提前收稿阈值从 sim≥0.88 提到 0.95,
  强制每段满 5 稿,在全部过门的稿里取最高 sim(v7 实测 S9C 首稿 1.000、S1B 0.976)。
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
