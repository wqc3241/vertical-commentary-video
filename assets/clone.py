# -*- coding: utf-8 -*-
"""Cloned-voice TTS via F5-TTS (the user's own voice).

Run with the stable venv python:
  /Volumes/Storage/voice-clone/venv/bin/python /Volumes/Storage/voice-clone/clone.py <mode> ...

Modes:
  say  "要合成的中文文本"  out.wav          # one clip
  scenes  <build_dir>                       # read <build_dir>/scenes.py -> per-scene wavs + durations.json
                                            # (drop-in replacement for a TTS step; output in the user's voice)

Env overrides:
  VOICE_CLONE_HOME (default /Volumes/Storage/voice-clone)
  VOICE_REF / VOICE_REF_TEXT  (reference clip + its transcript)
"""
import os, sys, json, subprocess

HOME = os.environ.get("VOICE_CLONE_HOME", "/Volumes/Storage/voice-clone")
os.environ.setdefault("HF_HOME", os.path.join(HOME, "hf-cache"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
REF  = os.environ.get("VOICE_REF",      os.path.join(HOME, "voice_ref.wav"))
REFT = open(os.environ.get("VOICE_REF_TEXT", os.path.join(HOME, "voice_ref_text.txt"))).read().strip()
SPEED = float(os.environ.get("VOICE_SPEED", "1.0"))   # <1.0 = slower / more deliberate

_model = None
def _get():
    global _model
    if _model is None:
        import torch
        from f5_tts.api import F5TTS
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        try:
            _model = F5TTS(device=dev)
        except Exception as e:
            print("MPS init failed -> CPU:", e); _model = F5TTS(device="cpu")
    return _model

def synth(text, out):
    _get().infer(ref_file=REF, ref_text=REFT, gen_text=text, file_wave=out, remove_silence=True, speed=SPEED)
    return out

def _dur(p):
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())

def scenes_mode(build):
    sys.path.insert(0, build)
    from scenes import SCENES
    aud = os.path.join(build, "audio"); os.makedirs(aud, exist_ok=True)
    man = []
    for sc in SCENES:
        raw = os.path.join(aud, sc["id"] + "_raw.wav")
        wav = os.path.join(aud, sc["id"] + ".wav")
        synth(sc["vo"], raw)
        # loudness-normalize + 48k stereo + small tail pad for breathing room between scenes
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",raw,
            "-af","loudnorm=I=-16:TP=-1.5,apad=pad_dur=0.18","-ar","48000","-ac","2",wav], check=True)
        os.remove(raw)
        d = _dur(wav); man.append({"id": sc["id"], "dur": round(d,3)})
        print(f'{sc["id"]}: {d:5.2f}s  | {sc["vo"][:20]}...')
    json.dump(man, open(os.path.join(build,"durations.json"),"w"), ensure_ascii=False, indent=2)
    print(f'TOTAL {sum(m["dur"] for m in man):.1f}s across {len(man)} scenes -> durations.json')

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "say":
        synth(sys.argv[2], sys.argv[3]); print("OK", sys.argv[3])
    elif mode == "scenes":
        scenes_mode(sys.argv[2])
    else:
        print(__doc__)
    # F5-TTS has a buggy interpreter teardown (config_init_hash_seed / resource_tracker)
    # that fires AFTER outputs are written. Flush and hard-exit 0 to avoid the spurious crash.
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(0)
