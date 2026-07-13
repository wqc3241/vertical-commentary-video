# Footage sourcing

Goal: get clean landscape highlight reels into `<project>/source/<stem>.mp4`, one stem per
match/segment. You cut vertical segments from these later.

## Find candidates with yt-dlp search
`yt-dlp` can search YouTube and print results without downloading:
```bash
yt-dlp --no-warnings --flat-playlist \
  --print "%(duration>%H:%M:%S)s | %(channel)s | %(title)s | https://youtu.be/%(id)s" \
  "ytsearch15:<player> <event> highlights" | head
```
Prefer **official channels** — Roland-Garros, WTA, ATP, the league/federation. They post the same
highlights as Instagram but are reliably downloadable. Reputable aggregators (House of Highlights,
etc.) are fine fallbacks when an official reel for a specific round isn't indexed.

## Download
```bash
yt-dlp --no-warnings --no-playlist \
  -f "bv*[height<=1080]+ba/b[height<=1080]" --merge-output-format mp4 \
  -o "source/<stem>.%(ext)s" "https://youtu.be/<id>"
```
Name stems so the bracket reads in order, e.g. `01_R1_Zheng`, `04_R16_Parry`, `06_SF_Shnaider`,
`07_Andreeva_QF`.

## Bot check
If you see `Sign in to confirm you're not a bot`, retry with the user's browser cookies:
```bash
yt-dlp --cookies-from-browser chrome  ... # (chrome worked on this Mac; safari sometimes too)
```
Chrome may prompt for keychain access. The plain `--extractor-args "youtube:player_client=ios,tv"`
trick sometimes helps too, but cookies are the reliable fix.

## Instagram
The user often *asks* for WTA / tournament Instagram. IG is login-gated and anti-scraping —
`yt-dlp` usually fails without `--cookies-from-browser`. The same footage is on the official
YouTube channels, which is what to use in practice. Tell the user you're substituting the official
YouTube source (same broadcast) and why, rather than silently failing on IG.

## Verify before you trust a clip
- `ffprobe` each file: confirm 1920×1080 and a sane duration.
- **Eyeball a few frames** with `contact_sheet.py source <stem>,<t> ...` — confirm it's the right
  match AND the right surface/venue. A real example: a "best points" reel turned out to be an
  indoor hard-court event; dropping it into a red-clay story looked jarring. Catch this here.

## Pick the clip the script line actually asks for
The scene's `vo` tells you WHICH moment to show. Match the footage to the words — and to the right
player — every time. Hard-won, from real fixes the user caught:

### "That round / the winning moment" → use the MATCH POINT (the last point of that match)
When a line is about a round result or "he finally won," show that match's **match point**: the
deciding rally ending on the **winning shot**. Highlight reels are structured:
`… rallies … → [match-point rally] → [winning shot] → [celebration/collapse] → [handshake] → [interview/graphics]`.
- Find it by contact-sheeting the reel's **last ~45s** at ~2s steps. The match point is the last
  RALLY right before the first celebration / reaction close-up / crowd-on-its-feet / handshake shot.
- Set the scene END at the end of that rally (then **back off EDGE_MARGIN**, see below).
- **Finals caveat:** the broadcast often holds ONE continuous long shot through the winning shot AND
  the player's collapse — there is **no cut at the win**. Don't trust a boundary here; eyeball the
  exact frame where the ball lands / he drops, and end there. (RG'26 final: rally through ~656s,
  winning shot ~657.5s, collapse onto the clay 658s — ending at the earlier "boundary" cut the rally
  mid-flight.) Make the climactic caption ("拿到冠军！") land on that winning frame — captions are
  auto-timed to the audio, so design the END so spoken climax == visual climax.

### Identity: confirm WHICH player is on screen before locking ANY clip
This is the single most common mistake; verify it for every footage scene, **including the hook/intro**.
- **Anchor the kit colour from a known-champion shot** — the trophy lift and the match-winning
  collapse are unambiguously YOUR player. Read that shirt colour, then match it everywhere. (RG'26:
  Zverev = navy/black; Cobolli = purple. The fired-up fist-pump I first grabbed for the intro was the
  *opponent* in purple.)
- **Celebration / fist-pump / roar close-ups are very often the OPPONENT**, especially in a tight
  match where they had momentum. A pumped player ≠ your player — check the colour, don't assume.
- Trophy ceremonies present the **runner-up first** (the early cup/podium shots are often the loser).
- An intro/bridge scene with **no dedicated match** still must show YOUR player. If the line is about
  past struggle/resolve, a determined rally or intense close-up of your player fits — not a rival's
  celebration, and (unless deliberately a cold-open) not a duplicate of the championship point.

**When kit colour is ambiguous — the escalation ladder (mandatory, 2026-07).** Colour matching FAILS at
Wimbledon (all-white) and whenever both players wear the same colour family. Real misses the user caught
(诺斯科娃 video, Beijing '25 final): "her walking in dark red" was ANISIMOVA — both wore red; the re-pick
nearly failed again until a **YONEX bag** behind the bench settled it. Escalate in this order:
1. **Equipment / kit BRAND** (most reliable): racquet paintjob, bag on the bench, logo on tank/visor/
   shoes. Sponsor contracts are per-player (e.g. Nosková=Yonex+RADO patch; Anisimova=Nike; Muchová=adidas).
   Zoom to full resolution until a logo is readable.
2. **Kit construction + headwear**: one-piece dress vs top+skirt; visor vs headband vs cap vs bare.
3. **Scorebug server-highlight** (the highlighted row is serving — match it to the player at the baseline)
   and stadium big-screen name/photo graphics inside the frame.
4. **Physique/handedness**: height difference (e.g. 1.85m vs 1.64m reads clearly in wides), left/right handed.
Cross-check at least TWO independent signals for every **single-subject** shot (close-up / bench / walking /
celebration) — those are where both real misses happened; two-player wides self-disambiguate via court sides.
Operational rules:
- Verify single-subject windows at **FULL RESOLUTION** — 320px contact-sheet tiles are how wrong IDs slip
  through. One full-res grab per window minimum.
- Probe **BOTH ENDS of the window** (start AND `tin+dur-0.2`): broadcast cuts mid-window can swap the
  subject — a scene that STARTS on your player can END on the opponent walking in (happened at Beijing:
  bench shot cut to the opponent's serve prep 0.9s before the window ended).
- **Post-final footage is winner-dense**: after the last point, the player walking / waving / hugging the
  box is almost always the WINNER — in a final your player LOST, default-assume such shots are the opponent
  until proven otherwise.
- Write the per-source anchor table (player = brand + kit + headwear, opponent = …) into the footage-gate
  plan so every later window pick checks against it.

### Don't trust a long "shot" as clean — the detector MERGES content
`shots.json` is scene-change detection; gradual transitions let it **merge a rally + a celebration +
a graphic board into one 20s "shot."** A big `du` does NOT mean continuous rally. Always **eyeball any
window** (fine contact sheet at ~1.5s steps) before locking it. The contact sheet is the source of
truth; shots.json is only a guide.

### No single clean window? Use a montage of verified short clips
If your player's footage for a beat is broken up by opponent close-ups or graphics (so no clean
N-second window exists), build the scene as `clips=[(stem,t1),(stem,t2)]` — two short clips you've each
verified are your player. (Used for the intro "fight" beat and the post-win cup-raise.) Each clip plays
an equal slice of the scene; pick `t` so each slice stays inside one clean shot.

### Factual relevance — the clip must be the REAL thing the line names
Pretty-but-wrong is a defect the user WILL catch. The footage has to be literally true to the words:
- A specific match/event line → that exact match (the **2022 AO** line needs the real 2022 Nadal–Medvedev
  final, NOT a 2012 Nadal–Djokovic match used as a "hard-court stand-in"). Download the real one.
- A medical / injury line (穆勒-魏斯综合症, 脚伤) → medical / X-ray / treatment footage, not a family or
  crowd shot. A "rivals praised him" line → the rivals (Federer/Djokovic), not an unrelated interviewee.
  "戴维斯杯" → Davis Cup footage. "红土/法网" → clay.
- **When the user gives you a source URL or a timestamp range, use exactly that** (e.g. "use 11:01–13:01
  from this video for the close-ups"). Don't substitute a different clip because it's easier.

### Avoid logo / brand / title CARDS — and the visual-scan that catches them
Trailers and tribute reels splice in full-screen **brand/title cards**: the Netflix "N" reveal, a
"MAY 29" date card, "LEGEND"/"CHAMPION" graphics, a Roland-Garros logo bumper, sponsor stings. Dropping
a window on one of these is the single most-reported mistake on this project.
- They are **NOT flash/brightness outliers** (a logo on black is mid-grey on average), so `pick_ends` and
  the luma check below will NOT flag them. The only reliable catch is to **look**.
- After every render, **scan every scene's window on the rendered video**: extract a frame at each scene
  start (+0.4s), its mid, and **each montage clip's start**, tile them with the scene id, and Read the
  sheet. Replace any window that opens on / passes through a card.
- A small **corner watermark** baked into the source (e.g. "NETFLIX" top-right on every doc frame) is
  fine and unavoidable — only full-screen CARDS are the problem. Brand cards cluster at a reel's head/
  tail and at segment transitions; tribute reels also drop the event logo between shots.

### Flash-free windows via a per-frame luma profile (when sources are cut-dense)
Trailers / montage tributes have black fade-frames, white-flash transitions and near-black tails that
cause a 1–N frame flicker at a cut. To pick windows that contain none of them WITHOUT eyeballing every
frame, profile each source's luma ONCE and reject any window with a near-black frame or a 1–2 frame
spike vs its neighbours:
```bash
# per-frame average luma (YAVG) for a source, one pass:
ffmpeg -hide_banner -i source/<stem>.mp4 -vf "signalstats,metadata=print:file=/tmp/lum_<stem>.txt" -an -f null -
```
A window `[t, t+dur]` is "clean" if no frame YAVG < ~18 (near-black) and no frame deviates > ~32 from its
local-neighbour median (a bright/dark spike). Scan candidate `tin`s and keep the cleanest that doesn't
overlap another scene's window. (This project keeps a `pick_clean.py` helper that does exactly this:
loads `/tmp/lum_*.txt`, `clean(stem,t0,t1)`, and finds nearest-clean windows per scene. Copy it in.)
The user reported flashes at five timestamps once; this profiling found those PLUS seven more they hadn't
spotted — run it across ALL scenes, not just the reported ones.

### Distinct windows — no repeated clips
Every scene must use a DISTINCT, non-overlapping window. Audit it: for each source, list every scene's
`[tin, tin+dur]` (montage clips count individually) and flag any pair that intersects. Don't over-
concentrate on one favourite reel — spread load across all downloaded sources, or the video feels
repetitive even when no two windows are byte-identical. Re-audit after any retime (durations change ⇒
window ends move).

## Avoid the 1-frame jump at every cut (EDGE_MARGIN)
A detected boundary `e` is the **first frame of the NEXT shot**. Ending a scene exactly at `e` flashes
one frame of crowd / reaction / handshake / logo at the cut. `pick_ends.py` now backs every end off by
`EDGE_MARGIN` (~0.17s ≈ 5 frames) automatically. **When you hand-set tins** (`lock`/`_MANUAL` for
match points or user-given windows), do it yourself: `tin = boundary - EDGE_MARGIN - dur`. To diagnose
a reported jump, extract fine frames straddling the END (source at END-0.3 … END+0.1): the cut shows as
a content change — keep the END a few frames on the rally side of it. `verify_ends.png` now samples the
TRUE last frame, so a stray ending is visible there before you ever render.

## Copyright framing
This is broadcast footage. For the user's own commentary/fan edit it's their call to make; just be
transparent about the source. Don't reproduce long copyrighted text anywhere in the deliverable.
