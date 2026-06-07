# Render internals & gotchas

## The look
- The 16:9 source is scaled to full width (1080×~608) and centred over a **DARK, heavily-blurred
  MOVING fill of itself** (boxblur + brightness −0.42), with a semi-transparent clay overlay
  (`overlay.png`) darkening the top (behind the chip) and bottom (behind captions). Dynamic depth,
  but the courtside ad boards never read as text. Keeping the WHOLE court visible matters when the
  narration discusses positioning/angles — don't crop the sides; only punch in for single-player shots.
- An earlier version used a *static* gradient bg to kill the ad-amplification; the user wanted the
  motion back, so it's now a *darkened* moving blur — keep both goals (dynamic AND ads unreadable).
- Top: a clay **chip**. Bottom: **captions** on a dark rounded bar.
- Cards: **results** (stats/scoreline) and **poster** (VS/tagline), over a more-dimmed (−0.52) blur.
- **Montage scene**: `clips=[(stem,tin),…]` plays N footage segments (equal slices of the scene
  length), each with the same bg+strip treatment, concatenated, then chip/caps overlaid across the
  whole scene. Use it for a varied post-win ending (cup → speech → photo). See `_render_base`.

## ffmpeg in this environment lacks drawtext/subtitles
This Homebrew ffmpeg has **no freetype/libass** → no `drawtext`, no `subtitles`. Don't use them.
All text is rendered to transparent PNGs with **PIL** and composited via `overlay`. `overlay` with a
single PNG persists for the whole scene (`eof_action=repeat`); caption windows use
`enable='between(t,a,b)'`. Font: clean heavy **Hiragino Sans GB W6** (`index=2`) — legibility first
(the user found the light W3 too plain and a 庆科黄油体 display font too thick; W6 was the keeper).
`boxblur`, `crop`, `scale`, `fade`, `overlay`, `drawbox` are present; `tile`/`zoompan` are not.

## Pipeline order (why)
1. `clone.py scenes` / `align.py` first — **durations drive everything** (each scene's video length
   = its narration length).
2. `caption_times.py` — word-exact caption timing from the actual audio (re-run after any re-record).
3. `detect_shots.py` then `pick_ends.py` — snap every scene's END to a real cut so we never leave a
   rally mid-flight. `pick_ends.py` writes a `verify_ends.png` — always look at it.
4. `render.py all` — PIL cards/chips/captions + per-scene 9:16 video (montage-aware).
5. `render.py assemble` (cloned/TTS per-scene audio) or `assemble-voice <wav>` (one recording).
   All scenes share identical encode settings so the concat demuxer can `-c copy`.

## Editing footage choices after the fact
- Change a scene's clip: edit `src`/`tin` in `scenes.py`, re-run `pick_ends.py` (or set `lock:True`
  + a manual tin / `_MANUAL`), then `render.py scene <ID>` + re-assemble. No full re-render needed.
- The user may hand you exact windows ("use this video 1:33–2:11"). Convert mm:ss→seconds, set
  `tin = window_end - duration` so the scene ENDS at the window's clean cut, and `lock:True`.
- 5 scenes but only 3 footage windows? Slice the long window into consecutive sub-ranges across
  scenes; it reads as continuous clay tennis. Reuse across distant scenes is fine.

## Verify before delivering
`contact_sheet.py video <out.mp4> 9` → Read it. Confirm: hook chip, tactic chips, the stats-card
**scores**, the celebration beat lands on YOUR player, and the poster. Then send the MP4.

## Short version
Write a condensed `scenes.py` (~6 scenes / 60–90s) reusing the best windows + the two cards, run the
same pipeline into a different `OUTPUT_NAME`. If the user already recorded the long script, a real-
voice short can be cut from chosen segments of that recording instead of re-recording.

## Performance
~4.5 min of 1080×1920 encodes twice (scenes + final) in a few minutes on an M-series Mac. Render
only changed scenes (`render.py scene <ID>`) when iterating, then re-assemble.
