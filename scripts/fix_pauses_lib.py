# -*- coding: utf-8 -*-
"""Audit TTS pauses vs 断句; regen scenes whose long pauses fall mid-line. voice-clone venv."""
import os, sys, json, re, subprocess, tempfile, shutil
BUILD=os.path.dirname(os.path.abspath(__file__))
HOME="/Volumes/Storage/voice-clone"
os.environ["VOICE_REF"]=os.path.join(HOME,"voice_ref_tennis_backup.wav")
os.environ["VOICE_REF_TEXT"]=os.path.join(HOME,"voice_ref_text_tennis_backup.txt")
sys.path.insert(0,BUILD)
from scenes import SCENES, CAPTIONS
AUD=os.path.join(BUILD,"audio"); GAP=0.34
REFT=open(os.path.join(HOME,"voice_ref_text_tennis_backup.txt")).read().strip()
_D={'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
clean=lambda s: re.sub(r'[^0-9A-Za-z一-鿿]','',"".join(_D.get(c,c) for c in s))
PROBES=[clean(REFT)[i:i+8] for i in range(0,max(1,len(clean(REFT))-8),6)]
def words(wav):
    tmp=tempfile.mkdtemp(); env={k:v for k,v in os.environ.items() if k!="PYTHONHASHSEED"}
    subprocess.run(["whisper",wav,"--language","Chinese","--model","small","--word_timestamps","True",
        "--output_format","json","--output_dir",tmp,"--fp16","False","--verbose","False"],
        capture_output=True,text=True,env=env)
    jp=os.path.join(tmp,os.path.splitext(os.path.basename(wav))[0]+".json")
    j=json.load(open(jp)); shutil.rmtree(tmp,ignore_errors=True)
    out=[]
    for seg in j["segments"]:
        for w in seg.get("words",[]): out.append((w["word"].strip(),w["start"],w["end"]))
    return out, "".join(x["text"] for x in j["segments"])
def silences(wav):
    r=subprocess.run(["ffmpeg","-i",wav,"-af","silencedetect=noise=-34dB:d=0.24","-f","null","-"],capture_output=True,text=True)
    out=[]; st=None
    for line in r.stderr.splitlines():
        m=re.search(r"silence_start: ([0-9.]+)",line)
        if m: st=float(m.group(1))
        m=re.search(r"silence_end: ([0-9.]+)",line)
        if m and st is not None:
            out.append((st,float(m.group(1)))); st=None
    return [(a,b) for a,b in out if a>0.05]  # skip leading silence
def badgaps(wav,caps):
    import difflib
    ws,full=words(wav)
    if any(p and p in clean(full) for p in PROBES): return [("LEAK",0,"")]
    asr=clean("".join(w[0] for w in ws)); cap=clean("".join(caps))
    # caption-line end positions in cap-space
    cb=[]; c=0
    for line in caps: c+=len(clean(line)); cb.append(c)
    # map cap-space boundaries -> asr-space via difflib blocks
    sm=difflib.SequenceMatcher(None,cap,asr); blocks=sm.get_matching_blocks()
    def map_pos(b):
        best=None
        for bl in blocks:
            if bl.a<=b<=bl.a+bl.size: return bl.b+(b-bl.a)
            d=min(abs(b-bl.a),abs(b-(bl.a+bl.size)))
            if best is None or d<best[0]: best=(d,bl.b+max(0,min(b-bl.a,bl.size)))
        return best[1] if best else b
    bpos={map_pos(b) for b in cb}
    total=len(asr)
    bad=[]
    for a,b in silences(wav):
        mid=(a+b)/2
        pos=0; lastw=""
        for w,ws_,we_ in ws:
            if we_<=mid: pos+=len(clean(w)); lastw=w
            else: break
        if pos>=total-1: continue  # tail silence
        if not any(abs(pos-x)<1 for x in bpos):
            bad.append((round(a,2),round(b-a,2),lastw+"|"))
    return bad
