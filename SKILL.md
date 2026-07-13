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
   is winner-dense: in a lost final that's the opponent.
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
8. **No repeated or overlapping clips, and no decorative frame.** Every scene gets a DISTINCT,
   non-overlapping footage window (audit `[tin, tin+dur]` per source — no two scenes share footage; don't
   over-lean on one reel). The deliverable is **full-screen, edge-to-edge** — no inset border/frame drawn
   by the overlay. → detection techniques in `footage-sourcing.md`.
9. **Photo scenes never jitter — `build_photos.py` only, NEVER ffmpeg zoompan.** Early-life / archive
   beats use photos with a slow Ken-Burns push. ffmpeg `zoompan` rounds x/y to integers every frame →
   visible micro-jitter the user caught (2026-07). `scripts/build_photos.py` renders the zoom with PIL
   affine SUBPIXEL sampling (float coords, bicubic) piped to x264 — perfectly smooth. Pre-crop each photo
   9:16 around the subject, name outputs `source/ig_ph_<name>.mp4` (the `ig_` prefix makes `build_ig.py`
   wire them FULL-BLEED automatically), `lock: True` their scenes. Smoothness check: consecutive-frame
   `tblend=difference` YAVG should be small and STEADY (no alternating spikes).
10. **The deliverable always carries 轻原声 (light ambient).** Final assembly = `assemble_ambient.py
   <voice_master> 0.30` — every clip's original audio (ball strikes / crowd / ceremony speech) bedded
   under the narration at gain 0.30 (0.14 proved too quiet). Voice-only `render.py assemble` is a draft,
   not the deliverable. Photo/silent sources get auto-silence (handled in the script). Speech-bearing
   windows (victory speech, on-court interview) are a feature — let the real voice breathe underneath.

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
   Only then concat the full deliverable. Long videos: parts = the script's chapters (~1min each); short ones may
   collapse to 2-3 parts, but the checkpoint stays. Fixes after preview are surgical: re-render the named scene(s),
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
  scenes, and asks for 标题/正文/tags too → wait 30–60s → harvest with `get_page_text`. Save the
  publish copy to `<project>/小红书发布文案.md`.
- **Copy-style rules the user requires — put these IN the ChatGPT prompt AND enforce when you map to captions
  (2026-07 feedback):**
  1. **数字一律用阿拉伯数字**(比分 3-6、时间 5小时15分、纪录 第15次、25冠),**不要中文数字**。
     ⚠️ 用户口中的「罗马数字」= 阿拉伯数字(西文数字 0-9),不是真的 Roman numerals — 别写成 XII。
     (念白 `vo` 仍要中文数字给 F5-TTS,见下条;GPT 出稿用阿拉伯数字,你在 CAPTIONS 里保留数字、在 `vo` 里转中文。)
  2. **语句通顺自然、口语化,不要浮夸 / 过度夸张的说法。**
  3. **少用「不是…而是…」这类转折句式**(以及其它生硬的对比转折)。
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
3. **Classic blur-letterbox landscape** ONLY where neither works (ambiguous 2-player wide rally the
   tracker can't follow, or the user prefers the broadcast frame) — and say which scenes fell back
   and why when presenting.
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
# 6c. FINAL — always WITH ambient (rule 10). TTS voice: concat build/audio/<id>.wav in scene order first:
python build/assemble_ambient.py build/audio_master.wav 0.30    # TTS voice master + ambient -> $PROJ/<OUTPUT_NAME>
# recorded take instead: python build/assemble_ambient.py build/voice/full48k.wav 0.30
# (voice-only render.py assemble / assemble-voice = drafts only, not the deliverable)
```
**16:9 landscape variant** (the user often wants this too): `render16.py` reuses the SAME `scenes.py`,
`durations.json` and `captions.json` and renders 1920×1080 (footage fills the frame, cards re-laid-out);
`assemble16.py` muxes the same voice + ambient. So one project yields both 9:16 and 16:9.

### 7. Verify + deliver — LOOK at every scene, not just a 14-frame sweep
`contact_sheet.py video <out.mp4> 14` → Read it. Confirm chips, captions in sync, card **scores +
names**, the win/trophy is YOUR player, the poster. For recorded takes, sync-spot-check (reference).
**Then run the FOUR checks the user keeps catching (see `footage-sourcing.md`):**
1. **Logo/card scan** — tile a frame from every scene's start + mid + each montage clip start, Read it,
   and replace any window that lands on a Netflix/sponsor/title/date CARD (luma checks miss these).
2. **Flash-free** — luma-profile each source (`signalstats`) and confirm no window has a near-black or
   spike frame (`pick_clean.py`); fix the reported ones AND the ones they didn't spot.
3. **Distinct + factual** — no two scenes share a window; every clip is literally true to its line.
4. **Identity re-check on the RENDERED output** — for every single-subject window (close-up, bench,
   walk, celebration): full-res frames at BOTH ends of the window; confirm subject via the rule-3
   escalation ladder (brand logo > kit construction > scorebug), not colour alone. A window can start
   on your player and end on the opponent after an in-window camera cut — probe the last second.
Deliver the MP4. Re-render only changed scenes (`render.py scene <ID>` / `render16.py scene <ID>`).

### 8. 小红书封面图 — deliver WITH the 发布文案, every video (user standard, 2026-07)
One consistent cover style across the account. **DEFAULT MODE (user decision 2026-07-12): GPT paints
the COMPLETE cover, text included** — in the SAME project chat that wrote the 解说词 (it has full
context). 4o renders Chinese accurately when the prompt spells every string verbatim and demands it.
1. **Send ONE single-line prompt** from this fixed template — only the 【】 slots vary per video
   (the four text zones + layout language are FROZEN; they ARE the account style):
   > 再生成一版完整封面,这次把文字直接画进图里,所有汉字必须逐字准确、不能错字漏字多字。竖版3比4。
   > 文字共四处:第一处,画面上部居中大标题「【主标,≤6字,压缩自小红书标题】」,厚重宋体风格衬线大字,
   > 白色带深色描边;第二处,大标题正下方一行金色副标题「【副标,≤10字】」,略小的金黄色衬线字;
   > 第三处,左上角红棕色圆角胶囊标签,内有白色小字「网球故事」,标签不要压到大标题;第四处,画面底部
   > 居中白色小字「【主人公人名】」,两侧各一个金色小圆点。人物主体:【主人公外形+本片高光瞬间特写,
   > 如:白色网球服白遮阳帽,双手捧温布尔登金盘、眼含泪光微微望天】,人物占画面中下部三分之二,头顶
   > 不要碰到副标题文字。写实电影感,【光线/场景,如:金色黄昏逆光,中央球场深绿背景大幅虚化】,浅景深。
   > 除上述四处文字外,画面内不要出现其他任何文字、水印或logo。
   高光瞬间 = the video's emotional peak (夺冠=捧杯, 逆转=怒吼, 告别=背影…). Wait 60-120s.
2. **Composer gotchas (each one happened):** the `computer type` action can silently DROP characters
   (「21」 and parens vanished) and cmd+A-delete can fail, so text ACCUMULATES. Reliable path: focus the
   composer, then via `javascript_tool` run `execCommand('selectAll')+('delete')+('insertText', P)`,
   VERIFY the four text substrings are present in `#prompt-textarea` innerText, then JS-click
   `button[data-testid="send-button"]`. Newlines auto-send — the prompt must be ONE line.
3. **Download via the bridge** (`scripts/cover_bridge.py`, port 8765). chatgpt.com's CSP blocks
   page-fetch to 127.0.0.1 AND server-side urllib gets 403 on the signed oaiusercontent URL — the
   working chain: in-page `fetch(img.src)` → FileReader→b64 (async JS must write results to
   `window.__r`; direct await returns `{}`) → hidden `<form method=POST>` submit (forms bypass
   connect-src) → navigate the tab back.
4. **逐字校验 (MANDATORY — 4o's #1 failure is mangled hanzi):** crop the four text zones at FULL
   resolution, Read them, and check EVERY character stroke-level against the intended strings. Any
   wrong/extra/missing char → tell GPT which char is wrong and regenerate (same chat). Then upscale
   to 1242×1656 lanczos → `封面图.jpg`, delivered together with `小红书发布文案.md`.
5. **Fallback (art-only + local typography):** if 4o repeatedly fails the text check, ask it for the
   SAME cover 但画面内不要任何文字 + 顶部1/4负空间, then burn the text with
   `scripts/make_cover.py <base> 封面图.jpg "主标" ["副标"] ["人名"] [角标]` — pixel-identical fonts
   (Songti SC Black 主标 / Songti SC Bold 金色副标 / bottom tracked name + gold dots / #C4563A pill,
   3:4 1242×1656, subject layer 86% bottom-anchored). Art re-prompts vary ONLY the 【高光/光线】 slots.

## Why it looks the way it does
- **Dark moving blur fill**: the footage is scaled-to-cover, blurred, and **darkened ~0.42** behind
  the centred 16:9 strip, with a clay overlay darkening top/bottom for text. Dynamic (not a static
  card) but ad boards never read as text. (`make_overlay` + `_render_base` in render.py.)
- **All text is PIL → PNG → ffmpeg overlay** (this ffmpeg lacks drawtext/subtitles). Font: clean
  heavy **Hiragino Sans GB W6** (`index=2`) — legible is the priority.
- Captions: word-exact from `captions.json`; else proportional. Montage scenes concat per-clip bases
  then overlay chip/caps across the full scene.

## Engine scripts (`scripts/`, copied into `build/`)
`scenes_template.py` (config) · `detect_shots.py` · `pick_ends.py` · `align.py` (align a recording) ·
`caption_times.py` (word-exact captions) · `render.py` (`all`/`scene <ID>`/`assemble`/`assemble-voice`/
`assets`) · `tts_say.py` (robotic draft) · `contact_sheet.py` · `shotsheet.py` ·
`pick_clean.py` (flash-free window finder from `/tmp/lum_*.txt` signalstats profiles) ·
`assemble_ambient.py` (FINAL assembler: voice + each clip's original audio at 0.30; silent sources →
auto-silence) · `regen_tts.py` (ANTI-LEAK cloned TTS: per-clip whisper verify + retries — the default
voice step) · `check_tts.py` (transcript-check report) · `preview_parts.py` (per-part 预览_A..E.mp4,
voice+ambient — the segment-preview checkpoint) · `build_photos.py` (photos → 9:16 Ken-Burns via PIL
subpixel affine; never zoompan) ·
`make_cover.py` (小红书封面统一排版: 3:4 + W6字体 + 金色副标 + 系列角标) · `cover_bridge.py`
(localhost 图片下载桥, ChatGPT/IG 签名URL专用) ·
`render16.py` + `assemble16.py` (16:9 / 1920×1080 variant from the same scenes/timing/captions) ·
`reframe_scenes.py` (full-bleed: crop landscape→9:16 tracking the player, via video-autoreframe) ·
`build_ig.py` (scale native-vertical Instagram clips AND `ig_ph_*` photo clips → `build/reframed/` keys).
render.py prefers a `build/reframed/<stem>_<tin>_<dur>.mp4` if present (full-bleed) else blur-fill — see
`references/vertical-footage-and-instagram.md`.

Voice cloning lives at `/Volumes/Storage/voice-clone/` (venv + `clone.py` + the user's reference clip;
`VOICE_SPEED` env controls pace). Recreate per `references/voice-and-audio.md` if missing.
