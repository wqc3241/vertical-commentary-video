# vertical-commentary-video

A Claude Code **skill** that builds ready-to-post **9:16 vertical narrated commentary / highlight
videos** (小红书 / Reels / TikTok / Shorts) from real match/event footage + a voiceover in the
creator's **own cloned voice**.

The pipeline: fact-check the script → download official footage (`yt-dlp`) → detect shot boundaries
so cuts land on **completed points** → narrate in the cloned voice (F5-TTS) or align a recording →
**word-exact** Chinese captions → render a dark moving-blur 9:16 with chips, a stats card, and a
closing poster. Supports **montage scenes** and is aware that a trophy ceremony presents the
**runner-up first** (so the ending stays on the actual champion).

→ **Read [`SKILL.md`](SKILL.md)** for the full playbook. Engine scripts live in `scripts/`,
detailed notes in `references/`, and the cloned-voice reference + `clone.py` in `assets/`.

Built on macOS (Apple Silicon) with `ffmpeg`, `yt-dlp`, `whisper`, Pillow, and F5-TTS.
Note: `assets/voice_ref.wav` is a personal voice sample — keep this repo **private**.
