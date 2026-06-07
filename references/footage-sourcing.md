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
