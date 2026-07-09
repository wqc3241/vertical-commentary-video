# Full-bleed vertical footage + Instagram sourcing

Two upgrades to the default pipeline, used when the user wants **真·竖屏** (the footage itself
vertical and edge-to-edge), not the default dark-blur-letterbox look:

1. **Full-bleed tracked vertical** — crop landscape sources to 9:16 while tracking the subject.
2. **Native-vertical Instagram clips** — already 9:16, used directly (no reframe).

Both feed the SAME render via a `build/reframed/<stem>_<tin>_<dur>.mp4` convention (below), so
captions / chips / scene timing / cloned-voice assembly are unchanged. You can mix per scene:
some scenes full-bleed IG, others tracked-from-landscape, others the classic blur-fill.

## The reframed-clip convention (how full-bleed plugs in)

`render.py._render_base` was extended: for a non-card scene it FIRST looks for
`build/reframed/<stem>_<tin>_<dur>.mp4` (stem = source basename, `tin`/`dur` formatted `%.3f`).
If present, it uses that clip **full-bleed** — `scale=W:H:force_original_aspect_ratio=increase,
crop=W:H` + the clay top/bottom scrim (`overlay.png`) for caption legibility, NO blur fill. If
absent, it falls back to the classic dark-blur-letterbox. Cards (results/poster) always use blur.

Keys must match what render computes:
- single scene → `(sc["src"], sc["tin"], DUR[id])`
- montage clip → `(clip_stem, clip_tin, DUR[id]/len(clips))`  ← seg duration, NOT the scene dur

`tin` is the value AFTER the scenes.py tail applies `proposed_tins.json`. **Lock every full-bleed
/ IG scene** (`lock: True`) so `pick_ends` and the import tail leave your hand-set `tin` alone —
the tail now skips locked scenes (older copies clobbered them; symptom: the wrong clip renders
even though `src` changed).

## A) Full-bleed tracked vertical (landscape → 9:16, follow the player)

Uses the **video-autoreframe** skill (YOLOv8 + ByteTrack + QP camera path). One-time venv:
`python3 -m venv ~/.claude/skills/video-autoreframe/venv && .../pip install ultralytics
opencv-python-headless numpy scipy osqp`.

`scripts/reframe_scenes.py` orchestrates it per scene window: cut the exact `[tin, tin+dur]`
landscape window, run detect → solve-path → encode, write `build/reframed/<key>.mp4` (1080×1920,
CRF 12). Run AFTER `durations.json` exists and `scenes.py` `src`/`tin` are set:
```bash
python3 build/reframe_scenes.py            # all ig_-less landscape windows; re-run safe (skips done)
python3 build/render.py all && python3 build/render.py assemble
```
- ~1–2 min per ~10s window (detect + CRF-12 slow encode). 10 windows ≈ 15 min.
- It tracks the **most prominent player**, so for 2-player rallies it may follow either — fine for
  positioning B-roll; for "this is PLAYER X" beats prefer single-subject practice/court-level
  footage (unambiguous). Verify every reframed clip (grab a mid-frame, confirm subject in frame).
- Court-level practice and slow-mo crop beautifully (subject centered); wide rallies lose context
  but read as real vertical match play.

## B) Native-vertical Instagram clips (the user's session)

IG reels are already 9:16 — no reframe, just scale to 1080×1920 + scrim. **Never enter the user's
password** (prohibited); reuse their already-logged-in browser. The user explicitly authorized
acting in their browser for this.

### Finding clips — use IG SEARCH, not just one account
The high-yield move is **search keywords**, not browsing a single fan page (fan pages are mostly
non-match edits: podium, crowd, talking-head, "core memory" text cards). Good queries (the user's
own examples): `jannik sinner forehand`, `jannik sinner close shot`, `jannik sinner point`,
`jannik sinner edits`, `<player> running forehand`, `<player> footwork`. Search → open a reel →
**Reels tab** of an account also works. Browse with the Claude-in-Chrome MCP
(`mcp__Claude_in_Chrome__*`, load via ToolSearch `+chrome navigate tabs read_page screenshot`):
`tabs_context_mcp createIfEmpty` → navigate `https://www.instagram.com/` → click search (left
rail) → type query → open results. Pull permalinks from the DOM:
`[...document.querySelectorAll('a[href*="/reel/"]')].map(a=>a.href)`.

What clips actually serve the footwork/movement theme:
- **Match points / rallies** (running forehands, defensive scrambles) → the "predict → arrive →
  hit" beats. Clay clips show sliding-into-position vividly.
- **Side-profile hits** → "看他的挥拍/侧面击球" beats.
- **Court-level / practice footwork** → the thesis "脚步才是精髓" beat.
- Avoid: title cards, score-graphic montages, talking heads, podium/trophy, anything with big
  baked-in text. Small corner watermarks (account handle, broadcaster bug) are fine.

### Downloading (two ways, both no-password)
1. **By reel URL** (preferred, has the page context):
   ```bash
   yt-dlp --cookies-from-browser chrome --no-warnings --no-playlist \
     -f "bv*[ext=mp4]+ba/b" --merge-output-format mp4 -o "ig/%(id)s.%(ext)s" \
     "https://www.instagram.com/reel/<id>/"
   ```
2. **Direct CDN .mp4** the user pastes (e.g. from the network panel / "copy link" of the asset):
   `curl -s -L -o ig/clip.mp4 '<scontent...cdninstagram.com/...mp4?...&oe=HEX>'`. These are
   **signed and EXPIRE** (`oe=` hex unix-time) — download immediately and **copy into `source/`**
   so the finished video survives the link dying.

Quality reality: most IG reels are **720×1280** (some 360p; occasional 1080×1920 gems — grab
those). Upscale to 1080×1920 with `flags=lanczos`. 720p IG looks softer than 1080p court-level
YouTube — tell the user the trade and let them choose which scenes go IG.

### Wiring IG clips in
Copy each chosen reel to `source/<stem>.mp4`, set the scene `src=<stem>`, `tin=<window start>`,
`lock=True`, then build the full-bleed reframed clips (native-vertical → just scale, no YOLO):
```bash
python3 build/build_ig.py     # scans scenes.py for src starting "ig_"/native-vertical, scale->reframed key
python3 build/render.py scene <ID> && python3 build/render.py assemble
```
`build_ig.py` computes keys from `scenes.py` + `durations.json` exactly like render (single AND
montage seg), so they always match. (For one-off windows you can also just `ffmpeg -ss tin -t dur
-i source/<stem>.mp4 -vf "scale=1080:1920:flags=lanczos,fps=30" ... build/reframed/<key>.mp4`.)

Identity still matters: confirm each IG clip is YOUR player (search returns look-alikes); a clip
of a consistent single player from a `<player>`-named search is usually safe, but eyeball it.

## Always verify after
Grab a full-res frame from each changed scene's start/mid (`ffmpeg -ss t`), tile, Read it:
confirm full-bleed (no letterbox), subject in frame, caption/chip legible over the scrim, no
title/score CARD, and that montage clips are distinct non-overlapping windows. See the three
checks in `footage-sourcing.md` — they apply to reframed/IG footage too.
