---
name: vertical-commentary-video
description: >-
  Build a 9:16 vertical narrated commentary / highlight video for Xiaohongshu (小红书),
  Reels, TikTok, or Shorts from real match/event footage plus a voiceover in the user's
  OWN cloned voice. Use this whenever the user wants a vertical short video, 竖屏解说视频,
  高光集锦, or 小红书视频 about a sports player, match, tournament, or any topic where real
  footage is narrated — e.g. "做一个关于XX选手的小红书竖屏视频", "把这场比赛剪成竖屏解说",
  "make a narrated highlights short about X", "turn this into a vertical reel with my voice".
  It runs the whole pipeline: fact-check the script via web search, download official footage
  with yt-dlp, detect rally/shot boundaries so cuts land on COMPLETED points, generate narration
  in the user's cloned voice (F5-TTS) or align a recording the user provides, and render
  blurred-letterbox 9:16 with burned Chinese captions, a stats card, and a final poster.
  Trigger even when the user only describes the topic + format without listing every step.
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
4. **Show the exact moment the line asks for.** A round result / "he won" → that match's **match point**
   (the deciding rally ending on the winning shot), found by scanning the reel's tail; the climactic
   caption must land on the winning frame. A long `shots.json` "shot" can secretly merge rally+celebration+
   graphic — eyeball it. No clean window of your player? Use a `clips=[…]` montage. → `footage-sourcing.md`.
5. **Surface/venue consistency.** Don't drop indoor-hardcourt B-roll into a red-clay story.

## Workflow (in order)

### 0. Setup
```bash
PROJ="/Volumes/Storage/Documents/<name>"
mkdir -p "$PROJ/source" "$PROJ/build"
cp ~/.claude/skills/vertical-commentary-video/scripts/*.py "$PROJ/build/"
```

### 1. Lock the script (TEXT FIRST — get sign-off before building visuals)
- Recent/ongoing event → **verify every fact with web search** (scores, opponents, records, dates;
  treat post-cutoff dates as unknown until checked). Names/scores go on screen — get them exact.
- Write `build/scenes.py` from `scenes_template.py`. Per scene: `vo` (spoken, **Chinese numerals**
  六比三 so TTS doesn't read English digits) + a `CAPTIONS[id]` list of the **display lines** (the
  user's own 断句, **digits** 6-3 for clarity). Each caption line must equal the spoken words
  (only numerals differ) or caption timing drifts. Fill `RESULTS_CARD`/`POSTER`. Present + wait.

### 2. Source footage → `references/footage-sourcing.md`
Official YouTube (RG/WTA/ATP/league) via `yt-dlp`; `--cookies-from-browser chrome` for bot-gated
ones. Verify each clip's resolution and **eyeball frames** (`contact_sheet.py`) — content, surface,
and which player is which. Match every scene's clip to its `vo` (round result → that match's **match
point**, scanned from the reel's tail) and **confirm the player by kit colour** anchored to a
known-champion shot — the reference covers match-point/identity/montage selection in detail.

### 3. Voiceover → `references/voice-and-audio.md`
Default = the user's cloned voice (slow it a touch so it breathes):
```bash
VOICE_SPEED=0.85 /Volumes/Storage/voice-clone/venv/bin/python \
   /Volumes/Storage/voice-clone/clone.py scenes "$PROJ/build"   # -> audio/<id>.wav + durations.json
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

### 6. Render + assemble
```bash
python "$PROJ/build/render.py" all        # overlay + cards + per-scene 9:16 (montage-aware)
python "$PROJ/build/render.py" assemble   # cloned/TTS audio -> $PROJ/<OUTPUT_NAME>
# OR, recorded take: python build/render.py assemble-voice build/voice/full48k.wav
```

### 7. Verify + deliver
`contact_sheet.py video <out.mp4> 14` → Read it. Confirm chips, captions in sync, card **scores +
names**, the win/trophy is YOUR player, the poster. For recorded takes, sync-spot-check (reference).
Deliver the MP4. Re-render only changed scenes (`render.py scene <ID>`) when iterating.

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
`assets`) · `tts_say.py` (robotic draft) · `contact_sheet.py` · `shotsheet.py`.

Voice cloning lives at `/Volumes/Storage/voice-clone/` (venv + `clone.py` + the user's reference clip;
`VOICE_SPEED` env controls pace). Recreate per `references/voice-and-audio.md` if missing.
