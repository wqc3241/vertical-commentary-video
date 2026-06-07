# -*- coding: utf-8 -*-
"""Word-exact captions: whisper each scene's cloned wav, align to the VO, emit per-chunk
[start,end] (relative to scene start) -> build/captions.json. Fixes caption sync/position.
Run AFTER the cloned audio exists (build/audio/<id>.wav)."""
import subprocess, json, os, sys, re, bisect, difflib, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenes import SCENES

BUILD=os.path.dirname(os.path.abspath(__file__)); AUD=os.path.join(BUILD,"audio")
CAPJ=os.path.join(BUILD,"capjson"); os.makedirs(CAPJ,exist_ok=True)
clean=lambda s: re.sub(r'[^0-9A-Za-z一-鿿]','',s)
import scenes as _S
CAPTIONS=getattr(_S,"CAPTIONS",{})          # user-specified caption lines (display, with digits)
_D={'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
def d2c(s): return "".join(_D.get(ch,ch) for ch in s)   # digits->Chinese to match spoken audio

# 1) whisper all scene wavs in one batch (model loads once).
#    Re-transcribe when the json is MISSING *or STALE* (wav newer than its cache) — so a re-record
#    of the voice is picked up automatically instead of aligning to old audio.
wavs=[os.path.join(AUD,s["id"]+".wav") for s in SCENES if os.path.exists(os.path.join(AUD,s["id"]+".wav"))]
def _stale(w):
    j=os.path.join(CAPJ, os.path.splitext(os.path.basename(w))[0]+".json")
    return (not os.path.exists(j)) or os.path.getmtime(w) > os.path.getmtime(j)
need=[w for w in wavs if _stale(w)]
if need:
    subprocess.run(["whisper",*need,"--language","Chinese","--model","small","--word_timestamps","True",
                    "--output_format","json","--output_dir",CAPJ,"--fp16","False","--verbose","False"],check=True)

def chunks_of(vo):
    seps="，。？！、：—"; parts,cur=[],""
    for ch in vo:
        if ch=="—": continue
        cur+=ch
        if ch in seps: parts.append(cur.strip("，。？！、：")); cur=""
    if cur.strip(): parts.append(cur.strip("，。？！、："))
    out,buf=[],""
    for p in [x for x in parts if x]:
        if len(buf)+len(p)<=14: buf+=p
        else:
            if buf: out.append(buf)
            buf=p
            while len(buf)>16: out.append(buf[:14]); buf=buf[14:]
    if buf: out.append(buf)
    return out or [vo[:14]]

captions={}
for sc in SCENES:
    sid=sc["id"]; jp=os.path.join(CAPJ,sid+".json")
    if not os.path.exists(jp): continue
    J=json.load(open(jp)); dur=float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",os.path.join(AUD,sid+".wav")]).strip())
    # asr char stream with per-char time
    ac,at=[],[]
    for seg in J["segments"]:
        for w in seg.get("words",[]):
            t=clean(w["word"]);
            if not t: continue
            a,b,n=w["start"],w["end"],len(t)
            for i,ch in enumerate(t): ac.append(ch); at.append(a+(b-a)*(i+0.5)/max(n,1))
    if not ac: continue
    asr="".join(ac)
    chs=CAPTIONS.get(sid) or chunks_of(sc["vo"]); voclean="".join(clean(d2c(c)) for c in chs)
    bnds=[]; acc=0
    for c in chs: bnds.append(acc); acc+=len(clean(d2c(c)))
    bnds.append(acc)
    # align voclean <-> asr
    sm=difflib.SequenceMatcher(None,asr,voclean,autojunk=False); ax,ay=[],[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=="equal":
            for k in range(i2-i1): ax.append(j1+k); ay.append(at[i1+k])
    def tat(j):
        if not ax: return 0.0
        if j<=ax[0]: return ay[0]
        if j>=ax[-1]: return ay[-1]
        p=bisect.bisect_left(ax,j)
        if ax[p]==j: return ay[p]
        x0,x1,y0,y1=ax[p-1],ax[p],ay[p-1],ay[p]; return y0+(y1-y0)*(j-x0)/(x1-x0)
    items=[]
    for k,c in enumerate(chs):
        a=tat(bnds[k]); b=(dur if k==len(chs)-1 else tat(bnds[k+1])); items.append({"text":c,"a":round(max(a,0),2),"b":round(min(b,dur),2)})
    captions[sid]=items
    print(f"{sid}: {len(items)} caps  {[round(i['a'],1) for i in items]}")

json.dump(captions, open(os.path.join(BUILD,"captions.json"),"w"), ensure_ascii=False, indent=1)
print("-> build/captions.json")
