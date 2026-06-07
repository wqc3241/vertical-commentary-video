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

## Copyright framing
This is broadcast footage. For the user's own commentary/fan edit it's their call to make; just be
transparent about the source. Don't reproduce long copyrighted text anywhere in the deliverable.
