---
name: vertical-commentary-video
description: >-
  Build a 9:16 vertical narrated commentary / highlight video for Xiaohongshu (小红书),
  Reels, TikTok, or Shorts from real match/event footage plus a voiceover in the user's
  OWN cloned voice. Use this whenever the user wants a vertical short video, 竖屏解说视频,
  高光集锦, or 小红书视频 about a sports player, match, tournament, or any topic where real
  footage is narrated — e.g. "做一个关于XX选手的小红书竖屏视频", "把这场比赛剪成竖屏解说",
  "make a narrated highlights short about X", "turn this into a vertical reel with my voice".
  It runs the whole pipeline: fact-check via web search, generate the 解说词 in the USER'S OWN
  ChatGPT via their browser (mandatory), source native-vertical Instagram/TikTok clips FIRST
  (landscape yt-dlp + blur letterbox only as per-scene fallback), detect rally/shot boundaries so
  cuts land on COMPLETED points, generate narration in the user's cloned voice (F5-TTS) or align
  a recording the user provides, and render 9:16 with burned Chinese captions, a stats card, and
  a final poster. Trigger even when the user only describes the topic + format without listing
  every step.
---

# Vertical Commentary Video Builder

Produces a ready-to-post **9:16 / 1080×1920** narrated video: real footage centred over a
**dark, heavily-blurred moving fill** of itself, **word-exact** burned-in Chinese captions, headline
"chips," a stats/results card, and a closing poster — timed to a voiceover in **the user's own
cloned voice**.

Playbook + engine. The `scripts/` are proven and reusable; each new video is a new project folder
where you copy the scripts, write one `scenes.py`, fetch footage, and run the pipeline. Read the
`references/` file when you reach the step it covers.

## The mental model

A video is a list of **scenes**. Each scene = one chunk of narration + footage (or a graphic card)
+ an optional chip + auto-timed captions. A scene can also be a **montage** (`clips=[(stem,tin),…]`)
that plays several footage segments in sequence — ideal for a post-win ending (cup-raise → speech →
photo). Everything is data in `build/scenes.py`.

Hard-won quality rules — the user cares about these, don't regress them:
1. **Cuts land on completed points — and a few frames BEFORE the camera cut.** Never end mid-rally.
   `detect_shots.py`+`pick_ends.py` snap each END to a real cut, then back off `EDGE_MARGIN` (~0.17s):
   a detected boundary is the *first frame of the next shot*, so ending exactly on it flashes one frame
   of crowd / reaction / handshake at the cut (the user notices). Hand-set/`_MANUAL` tins must subtract
   the margin too: `tin = boundary - 0.17 - dur`.
2. **Footage is real match play.** Avoid establishing/branding shots (court + event logo), slow-mo
   beauty close-ups, changeovers, and crowd cutaways in round scenes — pick the rally shots.
3. **Identity is correct — verify EVERY clip, including the hook/intro.** Anchor your player's kit
   colour from a *known-champion* shot (trophy lift / match-winning collapse), then match it everywhere.
   **Celebration / fist-pump close-ups are very often the OPPONENT** (a pumped player ≠ your player —
   check the colour). At a trophy ceremony the **runner-up is presented FIRST**. Single most common mistake.
   **Kit colour ALONE is not enough** — it fails at Wimbledon (all white) and whenever both players wear
   the same colour family (Beijing '25: BOTH in red; the user caught the wrong subject TWICE, 2026-07).
   Escalation ladder when colour is ambiguous, in order of reliability:
   a. **Equipment brand** — racquet/bag/kit logos are unambiguous (Nosková=Yonex vs Nike/adidas; a YONEX
      bag behind the bench settled a coin-flip). Zoom the frame until you can read a logo.
   b. **Kit construction + headwear** — one-piece dress vs top+skirt; visor vs headband vs cap; shoes.
   c. **Scorebug server-highlight / stadium screen** — the highlighted row serves; big-screen graphics name
      who's shown.
   d. **Physique** (height/build) and handedness.
   Protocol: build a per-source **identity anchor table** at footage-gate time (player = brand+kit+headwear
   per event); verify every **single-subject close-up at FULL resolution** (320px tiles lie — that's how both
   misses happened); and probe **BOTH ends of every window** — a camera cut mid-window can swap the subject
   (a window that STARTS on your player can END on the opponent). Post-final walking/waving/hugging footage
   is winner-dense: in a lost final that's the opponent. **YOLO-tracked crops need the same check on the
   TRACKED OUTPUT, not just the source** (2026-07): the tracker locked onto a standing spectator behind her
   while she sat crying, and onto the opponent at fixed-camera events where the near end swaps each game —
   extract frames from `build/reframed/*.mp4` and confirm the crop follows YOUR player for the whole window;
   if the subject is occluded/ambiguous, add the window to `FIT_WINDOWS` (full frame centered) instead.
4. **Show the exact moment the line asks for.** A round result / "he won" → that match's **match point**
   (the deciding rally ending on the winning shot), found by scanning the reel's tail; the climactic
   caption must land on the winning frame. A long `shots.json` "shot" can secretly merge rally+celebration+
   graphic — eyeball it. No clean window of your player? Use a `clips=[…]` montage. → `footage-sourcing.md`.
5. **Surface/venue consistency.** Don't drop indoor-hardcourt B-roll into a red-clay story.
6. **NO logo / title / graphic CARDS inside any window — ever.** Trailers and tribute reels splice in
   full-screen brand cards (the Netflix "N" reveal, sponsor logos, a "MAY 29" date card, "LEGEND"/
   "CHAMPION" graphics, the Roland-Garros logo bumper). These are NOT brightness/flash outliers, so the
   luma check will pass them — you must **visually scan every scene's window** (start + mid + EACH montage
   clip's start, on the rendered video) and replace any that land on a card. A small **corner watermark**
   baked into the source (e.g. "NETFLIX" top-right on every doc frame) is fine and unavoidable; only the
   full-screen CARDS are the problem. The user has caught these repeatedly — scan for them every build.
7. **Every clip must be factually true to its line.** The footage has to match what the words actually
   say: the "2022 Australian Open" line uses the *real* 2022 AO match (Nadal–Medvedev), not a look-alike
   hard-court match from another year; a "foot injury / 穆勒-魏斯综合症" line shows medical/X-ray footage,
   not a family shot; "his rivals praised him" shows the rivals, not an unrelated interviewee; "戴维斯杯"
   uses Davis Cup footage. When the user names a source/clip, use THAT one. Wrong-but-pretty ≠ acceptable.
8. **尽量不用重复素材 — but SLICE long sources into distinct moments (user rule 2026-07-16).** Every
   scene gets a DISTINCT, non-overlapping footage window (audit `[tin, tin+dur]` per source — no two
   scenes may share a window; run a programmatic overlap audit before rendering). Re-using the SAME
   moment twice is the violation; one long source containing DIFFERENT scenes (rally / bench / ceremony /
   interview) SHOULD be cut into several windows used in different places — that's how you stretch a thin
   footage pool without repeats. Spread usage across sources; don't over-lean on one reel. The deliverable
   is **full-screen, edge-to-edge** — no inset border/frame drawn by the overlay. → `footage-sourcing.md`.
9. **Static photos: PURE STATIC, ≤3s each, NO effects (user standing rule 2026-07-16 — supersedes the
   old Ken-Burns default).** "一张图出现在那儿就可以" — no zoom, no push, no pan; build stills with
   `ffmpeg -loop 1 -t <seg> -i photo.png` at native size. Photo rules, each one user-enforced:
   a. **≤3 seconds per photo/graphic** — in a montage a photo takes exactly 1 slice; longer beats use a
      VIDEO or a multi-photo montage, never one lingering still.
   b. **特写/already-tight photos are used AS-IS — never re-crop a close-up.** Second-pass cropping of an
      already-framed photo cuts heads/limbs (捧橘子照 beheaded twice).
   c. **If a 9:16 crop can't contain the whole person → show the FULL ORIGINAL image centered** (blur
      letterbox via `FIT_WINDOWS` / a `ph_*_wide` still). Do NOT iterate cx guesses hunting the subject —
      the user's exact words after two failures: "你要是不知道怎么截到整个人,你就放原图".
   d. **Every still must carry readable information — a subject's face/body or concrete numbers.** A
      zoomed fragment with no person and no legible data (the unintelligible zoomed scoreboard: "什么玩意儿")
      is worse than nothing; show the full graphic, or replace it, or extend the PREVIOUS video clip to
      fill the slot (user-preferred fix).
   e. `build_photos.py` Ken-Burns exists but is OFF by default now — only when the user explicitly asks
      for motion; ffmpeg `zoompan` stays banned always (integer-rounding jitter).
10. **The deliverable always carries 轻原声 (light ambient) — final gain 0.15 (user 2026-07-16: 0.30
   压配音,"再调小一半").** Segment previews may run 0.30 for review, but the FINAL assembly =
   `assemble_ambient.py <voice_master> 0.15` unless the user sets another value — the cloned voice must
   stay clearly on top. Voice-only `render.py assemble` is a draft, not the deliverable. Photo/silent
   sources get auto-silence. Speech-bearing windows (victory speech, on-court interview) are a feature —
   let the real voice breathe underneath.
11. **Every deliverable ends with the user's branded ending + ships as 1080p 60fps (standing rule
   2026-07-13).** After assemble_ambient/assemble16, ALWAYS run `finalize_ending.py <deliverable>`:
   appends `assets/ending.mov` (点赞收藏关注 card, native 1080×1920) — kept vertical for 9:16, center-
   cropped (`crop=1080:608:0:738`) for 16:9 — and re-encodes the whole file to 1080p@60fps. Idempotent
   (skips if the `finalized-with-ending` tag is present). Single-pass filter_complex concat dies on this
   Mac's ffmpeg — the script's 3-step method (transcode both parts to identical specs → concat -c copy)
   is deliberate, don't refactor. If the user hands you a NEW ending clip, replace `assets/ending.mov`.
12. **Produced IG reels' music is NOT venue sound — mute it.** Ambient under the narration must be REAL
   现场声 (ball strikes / crowd / broadcast); an edited reel's music bed or added SFX is not ("背景音
   不是视频背景音"). List those stems in `scenes.py` `MUTE_AMBIENT = {"ig_milan_champ", …}` — honored by
   BOTH `preview_parts.py` and `assemble_ambient.py`. Landscape 横屏 with an uncertain/two-player subject:
   fit the full frame centered (blur letterbox), do NOT zoom in guessing.
13. **Cards (战绩卡 etc.) are ≤3s INSERTS woven between match footage, never a parked full scene** (a
   16s static card loses viewers). Use per-scene `CARDS`+`treat="card:<key>"` slices inside a montage.
   Card text must not collide with the scene chip — give inserted cards `title=""` (the chip IS the
   title); if a chip covers a face, drop the chip for that scene.

## Approval gates — NEVER one-shot the whole video (the user requires this, 2026-07)
Build in stages and STOP for sign-off **twice**. Do NOT run TTS / render / assemble until BOTH gates pass —
the user asked for this explicitly ("不要一次性生成所有成片…我同意了再合成视频"). Re-running voice + reframe +
render is the expensive part; the gates exist so the user never pays for a full build of the wrong script or clips.
1. **Script gate.** After harvesting the 解说词 from ChatGPT and mapping it to `scenes.py`, PRESENT the full
   per-scene script (每个 scene 的 vo + 断句字幕, plus 标题/正文/tags) and WAIT for explicit approval / edits.
   The user's own rewrite IS the quality bar — expect edits; do not proceed to footage on your own.
2. **Footage gate.** After you've chosen every scene's clip (window + which player + full-bleed vs blur), PRESENT
   the plan — one line per scene, e.g. `S2 老德对拉(ESPN 704,跟踪)→小黑握拳特写(02_W_TB 352)→…`, backed by the
   contact-sheet frames you actually verified — and WAIT for approval before generating voice + rendering.
Only after the footage gate is approved do you run steps 3→7. (A tiny tweak the user requests mid-build — swap one
clip, fix one line — doesn't need a fresh gate; a new script or a new footage set does.)
3. **Segment-preview checkpoint (the user's standard review flow, 2026-07).** After rendering, do NOT deliver a
   one-shot final: assemble **per-part previews** (`preview_parts.py 0.30` → 预览_A..E.mp4, each = that part's
   scenes + voice + ambient at final quality), send them, and WAIT for segment feedback ("D3 不要卡" / "预览通过").
   Only then concat the full deliverable. Parts target ~1 MINUTE each — part count = ceil(runtime/60s),
   split at scene boundaries (user rule 2026-07-17: a ~2-min video = 2 parts, NOT one part per story
   beat; five ~20s files is over-splitting). The checkpoint stays regardless of length. Fixes after preview are surgical: re-render the named scene(s),
   rebuild only the affected part previews (`preview_parts.py 0.30 BCD`), then final-assemble.

## Workflow (in order)

### 0. Setup
```bash
PROJ="/Volumes/Storage/Documents/<name>"
mkdir -p "$PROJ/source" "$PROJ/build"
cp ~/.claude/skills/vertical-commentary-video/scripts/*.py "$PROJ/build/"
```

### 1. Lock the script (TEXT FIRST — get sign-off before building visuals)
- Recent/ongoing event → **verify every fact with web search FIRST** (scores, opponents, records,
  dates; treat post-cutoff dates as unknown until checked). Names/scores go on screen — get them
  exact. These verified facts feed the ChatGPT prompt below so it can't invent numbers.
- **MANDATORY — generate the 解说词 in the USER'S OWN ChatGPT via their browser; never just write
  it yourself.** The user has had to correct this repeatedly — skipping it is the #1 process
  mistake on this skill. Follow `~/.claude/skills/xhs-personal-vlog/references/copy-generation.md`:
  Claude-in-Chrome → chatgpt.com → open their copy project (`/g/g-p-…/project` URL from the DOM,
  clicking the name only expands it) → send ONE single-line prompt (newlines auto-send!) that
  includes the topic, the VERIFIED facts, spoken length (~60–90s), ≤20-char sentences, numbered
  scenes, and asks for 标题/正文/tags too — **and REQUIRE a fact-check first**: prompt 里明确写
  「先逐条核对我给出的事实清单再写稿;只使用清单内的事实,任何清单外或不确定的说法要标注出来,
  不要写进正文」(2026-07-22 rule; GPT 曾把「仅入学前奖金放开」写成「取消奖金限制」被用户抓出 —
  政策/规则类表述必须精确到适用范围) → wait 30–60s → harvest with `get_page_text`. Canvas mode
  often stalls mid-stream: ask for 纯文本对话回复 not canvas, and reload the page to see server-side
  truth before assuming failure. Save the publish copy to `<project>/小红书发布文案.md`.
- **Copy-style rules the user requires — put these IN the ChatGPT prompt AND enforce when you map to captions
  (2026-07 feedback):**
  1. **数字一律用阿拉伯数字**(比分 3-6、时间 5小时15分、纪录 第15次、25冠),**不要中文数字**。
     ⚠️ 用户口中的「罗马数字」= 阿拉伯数字(西文数字 0-9),不是真的 Roman numerals — 别写成 XII。
     (念白 `vo` 仍要中文数字给 F5-TTS,见下条;GPT 出稿用阿拉伯数字,你在 CAPTIONS 里保留数字、在 `vo` 里转中文。)
  2. **语句通顺自然、口语化,不要浮夸 / 过度夸张的说法。**
  3. **少用「不是…而是…」这类转折句式**(以及其它生硬的对比转折)。
  4. **英文大写缩写**:字幕/文案保留原文 (NCAA/TCU/ATP),念白 `vo` 写成顿号逐字母 `N、C、A、A`(见 step 3)。
  5. **人名用该账号惯用的中文译名;用户点名的昵称优先**(例:Learner Tien = 钱学生, 2026-07-22)。
- Treat the output as a DRAFT. **→ SCRIPT GATE: present the full script (per-scene vo + 断句 + 标题/正文/tags,
  with any factual/style fixes you made) and WAIT for the user's approval before touching footage.** Only if the
  browser/ChatGPT is genuinely unavailable may you draft the script yourself — and say so explicitly when presenting.
- **After** the script is approved, map it to `build/scenes.py` from `scenes_template.py`. Per scene: `vo`
  (spoken, **Chinese numerals** 六比三 so TTS doesn't read English digits — convert the GPT digits here) +
  a `CAPTIONS[id]` list of the **display lines** (the user's own 断句, **阿拉伯 digits** 6-3). Each caption
  line must equal the spoken words (only numerals / the 比↔- score separator differ) or caption timing drifts;
  keep every caption line **≤13 chars** so it never overflows (render.py wraps at 820px as a backstop). Fill
  `RESULTS_CARD`/`POSTER`. Then move to footage — the **next** stop is the Footage gate, not the render.

### 2. Source footage — VERTICAL-FIRST → `references/vertical-footage-and-instagram.md`
**DEFAULT: use真·竖屏 footage wherever possible — the user has emphasised this repeatedly; the
dark-blur letterbox is the FALLBACK, not the look.** Per scene, in order of preference:
1. **Native-vertical Instagram / TikTok reel** — search the user's logged-in IG in their browser
   (Claude-in-Chrome): keyword search (`<player> match point / forehand / celebration / edits`),
   plus official accounts' Reels tabs (@rolandgarros, @wimbledon, @atptour, the players). Pull
   `/reel/` permalinks from the DOM, download `yt-dlp --cookies-from-browser chrome`, wire in via
   `build_ig.py` (→ `build/reframed/` keys). Most reels are 720×1280 — upscale lanczos; tell the
   user which scenes are IG-720p vs 1080 so they can choose.
2. **Full-bleed tracked crop** of a landscape reel (`reframe_scenes.py`, video-autoreframe skill) —
   for beats that only exist in broadcast footage (e.g. THE match point of a specific round):
   download the official YouTube reel per `references/footage-sourcing.md`, then crop-track it.
   **Montage slices from one continuous take → `reframe_span.py`**: mark them `("stem",t),("stem","+"),…`
   and it runs ONE YOLO pass over the whole span then splits into per-slice keys — per-slice tracking
   re-centers at every cut and visibly jumps. Verify the tracked output per quality-rule 3.
3. **Classic blur-letterbox landscape** ONLY where neither works (ambiguous 2-player wide rally the
   tracker can't follow, subject occluded by crowd, or the user prefers the broadcast frame) — declare
   the window in `FIT_WINDOWS` so reframe skips it, and say which scenes fell back and why when
   presenting. This is also the mandated treatment for uncertain-subject 横屏 (rule 12) and
   can't-crop-the-whole-person photos (rule 9c): full frame/image centered, never a zoom guess.
Mix per scene; `lock: True` every full-bleed/IG scene. Verify each clip's resolution and **eyeball
frames** (`contact_sheet.py`) — content, surface, and which player is which. Match every scene's
clip to its `vo` (round result → that match's **match point**, scanned from the reel's tail) and
**confirm the player by kit colour** anchored to a known-champion shot — `footage-sourcing.md`
covers match-point/identity/montage selection in detail; identity checks apply to IG clips too
(search returns look-alikes and fan edits with baked-in text cards — reject those).
**→ FOOTAGE GATE: present the per-scene clip plan (with the contact-sheet frames you verified) and WAIT for
approval before step 3.** Montage note: clips are sliced **equally** (`D/n`), so a caption beat can spill onto the
next clip — order clips so the important line (the punchline / the named player) lands on the RIGHT clip, and say
so if a minor spill remains.

### 3. Voiceover → `references/voice-and-audio.md`
Default = the user's cloned voice via the ANTI-LEAK wrapper (never bare `clone.py scenes` — the default
reference clip deterministically leaks its tail phrase "尤其是他的叔叔托尼" into clip starts, and the
padded variant does NOT fix it; 7 recurrences as of 2026-07):
```bash
VOICE_SPEED=0.85 /Volumes/Storage/voice-clone/venv/bin/python \
   "$PROJ/build/regen_tts.py"     # tennis_backup ref + per-clip whisper verify + retry<=4 -> audio/<id>.wav + durations.json
python "$PROJ/build/check_tts.py" # standalone report; homophones/traditional-script/number-normalization are FALSE alarms — eyeball diffs
```
**断句/语气 audit — MANDATORY before captions (this made the 2026-07 build "完成度非常高"; the user
had previously flagged 断句奇怪 like "深圳|女孩"):** F5-TTS sometimes inserts a prosody break MID-phrase.
Whisper word-gap timestamps CANNOT detect these — audit acoustically:
```bash
/Volumes/Storage/voice-clone/venv/bin/python "$PROJ/build/fix_pauses.py"        # audit + auto-regen flagged scenes
/Volumes/Storage/voice-clone/venv/bin/python "$PROJ/build/regen_fix.py" S3,S7   # targeted re-takes if any remain
```
Method (in `fix_pauses.py`/`fix_pauses_lib.py`): ffmpeg `silencedetect` (-34dB / 0.24s, tightened
2026-07-21) finds real pauses → whisper word positions + difflib `SequenceMatcher` map each pause onto
the caption-line 断句 boundaries (survives digit/homophone drift; exact ±0 boundary match — a ±1
tolerance masked a real "李慧|说" break once). A pause AT a line boundary is correct prosody; a pause
INSIDE a line is a break → regenerate that scene and re-pick takes until ZERO intra-line pauses
(gaps whose context contains a latin letter are exempt — 顿号-spelled acronym letters pause legitimately).
**vo 写法 (2026-07-21/22 定稿):** clauses ≤20 chars separated by ,。 — **NEVER put "/" in `vo`**:
F5 vocalizes each slash as an audible junk syllable (one scene grew 14 extras; regen_tts strips "/"
defensively but don't write them). **ALL-CAPS acronyms = 顿号逐字母** in vo (NCAA→`N、C、A、A`,
TCU→`T、C、U`; user ear-tested — hanzi phonetics and glued NCAA both rejected), CAPTIONS keep latin
NCAA; regen_tts's acronym gate verifies every letter is heard. 读音有争议时:`clone.py say` 生成 3-4 个
候选读法试听 wav 放项目根目录让用户点选 — 你没有耳朵,不要盲猜。用户报"生硬/音调不对"= 韵律问题:
把 regen 提前收稿阈值 sim 0.88→0.95 强制满 5 稿择优。If scenes are regenerated AFTER previews,
rebuild `audio_master.wav` before final assembly (stale-master bug, 2026-07). 16G Mac 上 F5 连续跑会
死机重启:必须加 `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7`(故意让 MPS 初始化失败回落 CPU — 慢但整机稳,
不要"修复") + `caffeinate -i nice -n 10`,驱动脚本 `nohup … & disown` 逐场景独立进程,完成标志文件
监控(启动前先 rm 旧标志防误报);TCC 中途撤销卷授权时改走 Desktop Commander。详见 voice-and-audio.md。
Or the user records one take → `align.py` (see reference).

### 4. Word-exact captions  → `references/voice-and-audio.md`
```bash
python "$PROJ/build/caption_times.py"     # whisper each scene's audio -> build/captions.json
```
Aligns each caption line to the actual spoken words (fixes "captions out of sync / bunched up").
It auto-re-transcribes when you re-record (staleness check). If you skip this, render falls back to
proportional timing.

### 5. Snap cuts to completed points (a few frames BEFORE the cut)
```bash
python "$PROJ/build/detect_shots.py"      # -> shots.json
python "$PROJ/build/pick_ends.py"         # -> proposed_tins.json + verify_ends.png  (auto EDGE_MARGIN ~0.17s)
```
**Look at `verify_ends.png`** (now shows each scene's TRUE last frame) — every ending is a rally, never
the opponent / a replay / a logo / a 1-frame crowd-reaction flash. Fix via `END_OVERRIDES`/`AVOID_ENDS`/
`lock`+manual tins; re-run. For a **match-point** ending or a user-given window, hand-set the tin with
the margin baked in: `tin = boundary - 0.17 - dur`, locked via `_MANUAL`. `shots.json` can merge a
rally+celebration+graphic into one long "shot" — eyeball the window, never trust its duration alone.

### 6. Render → SEGMENT PREVIEWS → final assemble  (only after BOTH gates are approved)
```bash
python "$PROJ/build/render.py" all        # overlay + cards + per-scene 9:16 (montage-aware)
# 6a. SELF-QC the rendered scenes (see step 7 checks) BEFORE showing the user anything.
# 6b. SEGMENT PREVIEWS — the user's standard flow: per-part files at final quality, then WAIT for feedback:
python "$PROJ/build/preview_parts.py" 0.30           # -> 预览_A..E.mp4 (part scenes + voice + ambient@0.30)
# ... user reviews; fix named scenes; rebuild affected parts: preview_parts.py 0.30 BCD
# 6c. FINAL — always WITH ambient (rule 10, final gain 0.15). TTS voice: concat build/audio/<id>.wav
#     in scene order first (REBUILD it if any scene was regenerated after previews — stale-master bug):
python build/assemble_ambient.py build/audio_master.wav 0.15    # TTS voice master + ambient -> $PROJ/<OUTPUT_NAME>
# recorded take instead: python build/assemble_ambient.py build/voice/full48k.wav 0.15
# (voice-only render.py assemble / assemble-voice = drafts only, not the deliverable)
# 6d. ALWAYS finish with the branded ending + 1080p60 re-encode (rule 11):
python build/finalize_ending.py "$PROJ/<OUTPUT_NAME>"
```
**16:9 landscape variant** (the user often wants this too): `render16.py` reuses the SAME `scenes.py`,
`durations.json` and `captions.json` and renders 1920×1080 (footage fills the frame, cards re-laid-out);
`assemble16.py` muxes the same voice + ambient. So one project yields both 9:16 and 16:9 — run
`finalize_ending.py` on that output too (it auto-detects 16:9 and crops the ending to landscape).

### 7. Verify + deliver — LOOK at every scene, not just a 14-frame sweep
`contact_sheet.py video <out.mp4> 14` → Read it. Confirm chips, captions in sync, card **scores +
names**, the win/trophy is YOUR player, the poster. For recorded takes, sync-spot-check (reference).
**Then run the FIVE checks the user keeps catching (see `footage-sourcing.md`):**
1. **Logo/card scan** — tile a frame from every scene's start + mid + each montage clip start, Read it,
   and replace any window that lands on a Netflix/sponsor/title/date CARD (luma checks miss these).
2. **Flash-free** — luma-profile each source (`signalstats`) and confirm no window has a near-black or
   spike frame (`pick_clean.py`); fix the reported ones AND the ones they didn't spot.
3. **Distinct + factual** — no two scenes share a window; every clip is literally true to its line.
4. **Identity re-check on the RENDERED output** — for every single-subject window (close-up, bench,
   walk, celebration): full-res frames at BOTH ends of the window; confirm subject via the rule-3
   escalation ladder (brand logo > kit construction > scorebug), not colour alone. A window can start
   on your player and end on the opponent after an in-window camera cut — probe the last second.
5. **Re-scan after EVERY duration change** — re-recording even ONE scene's voice changes all montage
   slice lengths and shifts every window: after any re-assembly, re-extract frames and repeat checks
   1+4 on the shifted windows. A full-screen "COACH" title card drifted into frame TWICE this way
   (2026-07-22) — the previous QC pass does not protect the new cut.
Deliver the MP4. Re-render only changed scenes (`render.py scene <ID>` / `render16.py scene <ID>`).

**内容章节 — the 4th standard deliverable (user standard 2026-07-16), alongside 成片/封面图/发布文案:**
a chapter list with timestamps + themes, appended to `小红书发布文案.md`.
- **This list feeds the PLATFORM chapter features at publish time — it must NOT be pasted into the
  XHS note body** (user rule 2026-07-23): XHS = 内容设置→添加章节, set during the FIRST publish
  (locked afterwards — unlocking requires re-uploading the video); douyin = 章节功能 (智能章节 or
  manual). See the `publish-xhs-douyin` skill.
- **Chapter count ≤ the video's length in minutes** (6-min video → ≤6 chapters, 5-min → ≤5; round the
  runtime UP). With more scenes than that, MERGE adjacent scenes into one chapter per story beat
  (起步→夺冠→爆发…), don't emit one chapter per scene.
- Timestamps = cumulative scene durations from `build/durations.json` (scene renders equal their audio
  length; the branded ending only adds tail time). Format `mm:ss`, floor to the second.
- **Frame-verify 3-4 boundaries before delivering**: extract a frame just after each claimed timestamp
  and confirm the scene chip/content matches the chapter title — never ship unchecked arithmetic.
- Titles follow the copy-style rules (Arabic digits, natural phrasing, no hype).

### 8. 小红书封面图 — deliver WITH the 发布文案, every video (user standard, 2026-07)
**The cover MUST be generated in the user's web ChatGPT — NEVER self-generate one (user hard rule
2026-07-16: "一定要用 web 版 GPT 去生成,不要你自己生成").** Local `make_cover.py` typography is NOT an
acceptable default or silent fallback — it may be used only if GPT repeatedly fails AND the user
explicitly approves switching. One consistent cover style across the account, made in the SAME project
chat that wrote the 解说词. The account typography is FROZEN — four text zones, only the 【】 slots vary
per video:
> 大标题「【主标,≤6字,压缩自小红书标题】」厚重宋体衬线白字深色描边 · 其下金色副标题「【副标,≤10字】」·
> 左上角红棕圆角胶囊白字「网球故事」(不压标题) · 底部居中白字「【主人公人名】」两侧金色小圆点 ·
> 竖版3比4 · 所有汉字逐字准确 · 除四处文字外无任何其他文字/水印/logo

**封面选型 — 按内容类型选,不要一律套人物模板 (user rule 2026-07-22):**
- **人物专题**(单一主角的故事)→ 上面的四区冻结模板原样用(胶囊+主标+副标+人名)。
- **话题片/群像/盘点**(如「NCAA 的魔力」这类多人主题)→ **多位主角头像特写拼版**(2-4 人竖条并排,
  人脸取自已验证身份的素材帧或官方照片),**只保留主标+副标 — 不要「网球故事」胶囊、不要人名**,
  字体可以换(现代粗黑体等)。拼版自己合成好再注入 GPT(留出标题头部空间、避开路人/新闻条;
  `ffmpeg -map_metadata -1` 剥掉 XMP 再 b64 分块注入)。
- GPT 项目会惯性沿用老模板:prompt 必须显式写「这期不要胶囊、不要人名」;若它仍套错,不要重新生成,
  用「基于你上一张生成的封面图修改:…」来纠正(重出图会连底图一起换掉)。

**MODE A — 真实照片底图 + GPT 只做排版 (THE DEFAULT; user decision 2026-07-13,不要纯AI画人):**
1. **Find the real photo**: the subject's IG / official collab posts (@wta·@wimbledon×player "champion"
   posts are gold) / a full-res frame from own footage. Prefer 竖版, high-emotion 夺冠特写 (捧杯/举杯/
   泪目). Identity-verify via the rule-3 ladder. Download: IG scontent → hidden-form POST the signed URL
   to `scripts/cover_bridge.py` (server-side fetch works for IG, unlike oaiusercontent).
2. **Attach it to the ChatGPT chat** — the ONLY path that works from this harness (file_upload
   whitelist, CSP fetch/img-to-localhost, synthetic cmd+V, upload_image: ALL blocked): compress to
   ≤20KB JPEG → base64 (~26K chars) → inject via `javascript_tool` in **3200-char chunks**
   (`window.__P+='...'`, verify cumulative length EVERY call — longer self-authored literals silently
   truncate) → `atob`→`Uint8Array` (check JPEG magic 0xFFD8) → `new File`→`new DataTransfer` →
   dispatch `ClipboardEvent('paste',{clipboardData:dt})` on the focused `#prompt-textarea` → confirm
   the attachment thumbnail appears (screenshot). ~10 tool calls.
3. **Prompt** (one line, insertText): 「以我附上的这张她本人的真实夺冠照片为封面底图:保留照片里真实的
   人物、姿势和球场背景,不要重绘、替换或美化人物,只在这张照片上做封面排版——【四处文字模板】;画面按
   竖版3比4输出,可在上下用照片的虚化延展补足空间,所有汉字必须逐字准确。」 The output keeps the
   authentic face/pose/crowd with the typography on top. Wait 60-120s.
4. **逐字校验 (MANDATORY — 4o's #1 failure is mangled hanzi):** download the result (in-page
   `fetch(img.src)`→b64→form-POST to the bridge; async JS must write to `window.__r`, direct await
   returns `{}`), crop the four text zones at FULL resolution, Read them, check EVERY character.
   Any wrong/extra/missing char → tell GPT which char and regenerate in the same chat.
5. Upscale to 1242×1656 lanczos → `封面图.jpg`, delivered together with `小红书发布文案.md`.

**MODE B — 全AI直出 (fallback when no usable real photo exists):** same four-text-zone template plus
人物主体描述【外形+本片高光瞬间特写】+ 写实电影感【光线/场景】+ 人物占中下2/3、头顶不碰副标题。
高光瞬间 = the video's emotional peak (夺冠=举杯, 逆转=怒吼, 告别=背影…). Pose language must be
PRECISE (高举过头顶≠捧起≠端着 — "捧起" rendered as 端盘子 once). Pose/composition fixes = EDIT the
previous image (「基于你上一张生成的封面图修改:【改动】,其余全部不变」), never re-prompt from scratch.

**MODE C — ONLY with the user's explicit approval, never on your own initiative (demoted 2026-07-16):**
if 4o repeatedly mangles text after regeneration attempts, ASK the user; only if they approve, request
the art 不带任何文字 + 顶部1/4负空间, then burn typography locally with `scripts/make_cover.py <base>
封面图.jpg "主标" ["副标"] ["人名"] [角标]` (Songti SC Black/Bold, gold sub, tracked name + gold dots,
#C4563A pill, 1242×1656).

**Composer gotchas (each one happened):** `computer type` can silently DROP characters (「21」+parens
vanished) and cmd+A-delete can fail so text ACCUMULATES → always `javascript_tool` with
`execCommand('selectAll')+('delete')+('insertText',P)`, VERIFY key substrings in `#prompt-textarea`
innerText, then JS-click `button[data-testid="send-button"]`. Newlines auto-send — ONE line only.

### 9. 发布 — when the user asks to publish, use the `publish-xhs-douyin` skill
Both platforms' web backends are fully automatable from Claude-in-Chrome (proven 2026-07-23):
video upload via the window.name relay + `publish_bridge.py`, title/body/tags, chapter features,
declarations, custom cover, and 定时发布. The complete dual-platform playbook (step order, injection
snippets, per-platform quirks, timezone semantics, white-screen recovery) lives in the separate
**`publish-xhs-douyin`** skill — invoke it; do not improvise from memory. Non-negotiable user rules
enforced there: 🎾 title prefix (tennis); XHS = chapters via 添加章节 **at first publish** (locked
after; never in the body text) + 原创声明 ON; douyin = 自主声明「内容为个人观点或见解」+ chapters
(智能章节 or manual) + last-tag trailing space. Default schedule slot: Beijing 19:00 (XHS picker IS
Beijing time; douyin picker is browser-local — convert).

## Why it looks the way it does
- **Dark moving blur fill**: the footage is scaled-to-cover, blurred, and **darkened ~0.42** behind
  the centred 16:9 strip, with a clay overlay darkening top/bottom for text. Dynamic (not a static
  card) but ad boards never read as text. (`make_overlay` + `_render_base` in render.py.)
- **All text is PIL → PNG → ffmpeg overlay** (this ffmpeg lacks drawtext/subtitles). Font: clean
  heavy **Hiragino Sans GB W6** (`index=2`) — legible is the priority.
- Captions: word-exact from `captions.json`; else proportional. Montage scenes concat per-clip bases
  then overlay chip/caps across the full scene.

## Engine scripts (`scripts/`, copied into `build/`)
`scenes_template.py` (config; incl. optional `CARDS`/`MUTE_AMBIENT`/`FIT_WINDOWS`/`IG_EXCLUDE`/`PART_MAP`
knobs + "+" contiguous-slice markers) · `detect_shots.py` · `pick_ends.py` · `align.py` (align a recording) ·
`caption_times.py` (word-exact captions) · `render.py` (`all`/`scene <ID>`/`assemble`/`assemble-voice`/
`assets`; per-scene cards via `treat="card:<key>"`) · `tts_say.py` (robotic draft) · `contact_sheet.py` ·
`shotsheet.py` · `pick_clean.py` (flash-free window finder from `/tmp/lum_*.txt` signalstats profiles) ·
`assemble_ambient.py` (FINAL assembler: voice + each clip's real audio — final gain 0.15, rule 10; honors
`MUTE_AMBIENT`; silent sources → auto-silence) · `finalize_ending.py` (LAST step, rule 11: append
`assets/ending.mov` + re-encode 1080p60; auto 9:16/16:9) · `regen_tts.py` (QUADRUPLE-GATE cloned TTS — the default voice step: anti-leak probe + junk-insert
detection + acronym-completeness + zero intra-line pauses per take, 5 takes, best-of; strips "/" from vo;
TARGETS-resumable) · `check_tts.py` (transcript-check report) ·
`fix_pauses.py`/`fix_pauses_lib.py`/`regen_fix.py` (断句 audit: silencedetect + difflib line-boundary
mapping → regen mid-line-pause scenes; the step-3 prosody pass) · `preview_parts.py` (per-part
预览_A….mp4, voice+ambient, `PART_MAP`-aware — the segment-preview checkpoint) · `build_photos.py`
(photo→video Ken-Burns via PIL subpixel affine — user-request ONLY now, rule 9: stills default to pure
static `-loop 1`; zoompan always banned) ·
`make_cover.py` (小红书封面本地排版 — MODE C, explicit user approval only) · `cover_bridge.py`
(localhost 图片下载桥, ChatGPT/IG 签名URL专用) · `publish_bridge.py` (发布桥: 本地文件服务器喂
成片/封面给创作者后台上传控件, CORS+PNA 头齐全 — the publish workflow itself lives in the
`publish-xhs-douyin` skill) ·
`render16.py` + `assemble16.py` (16:9 / 1920×1080 variant from the same scenes/timing/captions) ·
`reframe_scenes.py` (full-bleed: crop landscape→9:16 tracking the player, via video-autoreframe) ·
`reframe_span.py` (contiguous montage slices: ONE YOLO pass per span split into per-slice keys; skips
vertical stems + `FIT_WINDOWS`) ·
`build_ig.py` (native-vertical + `ig_ph_*` clips → `build/reframed/` keys; cover-crop scale so non-9:16
never stretches; respects `IG_EXCLUDE`).
render.py prefers a `build/reframed/<stem>_<tin>_<dur>.mp4` if present (full-bleed) else blur-fill — see
`references/vertical-footage-and-instagram.md`.

Voice cloning lives at `/Volumes/Storage/voice-clone/` (venv + `clone.py` + the user's reference clip;
`VOICE_SPEED` env controls pace). Recreate per `references/voice-and-audio.md` if missing.
