# -*- coding: utf-8 -*-
"""16:9 (1920x1080) render variant of render.py. Same scenes.py data, durations.json (real-voice
pacing) and captions.json. Footage fills the frame (it's already 16:9), slightly darkened, with
top/bottom scrims for chip + captions. Cards re-laid-out for landscape.
Writes build/scene16/<id>.mp4 + build/png16/*. Commands: assets | scene <ID> | all"""
import subprocess, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as S
from scenes import SCENES
from PIL import Image, ImageDraw, ImageFont

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(BUILD)
SRC   = os.path.join(ROOT, "source")
PNG   = os.path.join(BUILD, "png16"); os.makedirs(PNG, exist_ok=True)
SCN   = os.path.join(BUILD, "scene16"); os.makedirs(SCN, exist_ok=True)

W, H, FPS = 1920, 1080, 30
CLAY=(196,86,58); GOLD=(226,188,104); WHITE=(248,246,243); INK=(20,16,14)
BODY_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
_fc={}
def fbody(sz): _fc.setdefault(sz,ImageFont.truetype(BODY_PATH,sz,index=2)); return _fc[sz]
DUR  = {d["id"]: d["dur"] for d in json.load(open(os.path.join(BUILD,"durations.json")))}
CAPS = json.load(open(os.path.join(BUILD,"captions.json"))) if os.path.exists(os.path.join(BUILD,"captions.json")) else {}

def run_w(text, sz): return sum(fbody(sz).getlength(c) for c in text)
def draw_run(d,x,y,text,sz,fill,sw=0,sfill=None):
    f=fbody(sz)
    for c in text: d.text((x,y),c,font=f,fill=fill,stroke_width=sw,stroke_fill=sfill); x+=f.getlength(c)
def draw_center(d,y,text,sz,fill,sw=0,sfill=None,cx=W/2): draw_run(d,cx-run_w(text,sz)/2,y,text,sz,fill,sw,sfill)
def rrect(d,box,r,fill): d.rounded_rectangle(box,radius=r,fill=fill)

def make_overlay():
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img); clay=(28,15,11)
    for y in range(H):
        if   y<200:  a=int(150-150*(y/200))             # top (behind chip) 150->0
        elif y>760:  a=int(0+205*((y-760)/(H-760)))     # bottom (behind caption) 0->205
        else:        a=0
        d.line([(0,y),(W,y)],fill=(*clay,a))
    img.save(os.path.join(PNG,"overlay.png"))

def make_chip_png(text,path):
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    sz=44; tw=run_w(text,sz); px,py=38,14; by0=46; by1=by0+sz+py*2
    bx0,bx1=(W-tw)/2-px,(W+tw)/2+px
    rrect(d,[bx0,by0,bx1,by1],(by1-by0)/2,(*CLAY,242)); draw_center(d,by0+py-4,text,sz,WHITE,sw=1,sfill=(0,0,0,110))
    img.save(path)

def _wrap(text,sz,maxw):
    f=fbody(sz); lines,cur=[],""
    for ch in text:
        if f.getlength(cur+ch)>maxw and cur: lines.append(cur); cur=ch
        else: cur+=ch
    if cur: lines.append(cur)
    return lines

def make_caption_png(text,path):
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    sz=50; lines=_wrap(text,sz,1500); lh=66
    tw=max(fbody(sz).getlength(l) for l in lines); th=lh*len(lines); px,py=44,18
    bx0,bx1=(W-tw)/2-px,(W+tw)/2+px; by1=1018; by0=by1-th-py*2
    rrect(d,[bx0,by0,bx1,by1],26,(0,0,0,150)); y=by0+py
    for l in lines: draw_center(d,y,l,sz,WHITE,sw=3,sfill=(0,0,0,230)); y+=lh
    img.save(path)

def _scrim(img,top=120,bot=180):
    d=ImageDraw.Draw(img)
    for y in range(H): d.line([(0,y),(W,y)],fill=(0,0,0,int(top+(bot-top)*(y/H))))

def make_results_card(path):
    cfg=getattr(S,"RESULTS_CARD",None)
    img=Image.new("RGBA",(W,H),(0,0,0,0)); _scrim(img,120,185); d=ImageDraw.Draw(img)
    if not cfg: img.save(path); return
    draw_run(d,90,70,cfg.get("title","战绩"),92,WHITE,sw=2,sfill=(0,0,0,170))
    pill=cfg.get("pill","")
    if pill:
        w=run_w(pill,34); rrect(d,[90,196,90+w+44,256],30,(*CLAY,242)); draw_run(d,112,205,pill,34,WHITE)
    if cfg.get("subtitle"): draw_run(d,90,284,cfg["subtitle"],36,(238,226,214))
    rows=cfg.get("rows",[]); y=372; rh=150
    for i,(rd,op,sc) in enumerate(rows):
        y0=y+i*rh; last=(i==len(rows)-1) and cfg.get("highlight_last",True)
        rrect(d,[90,y0,W-90,y0+rh-18],18,(*CLAY,238) if last else (255,255,255,28))
        rrect(d,[112,y0+22,272,y0+rh-40],14,(*GOLD,240)); draw_center(d,y0+34,rd,40,INK,cx=192)
        draw_run(d,300,y0+30,op,52,WHITE,sw=1,sfill=(0,0,0,150))
        if sc:
            fs=48; draw_run(d,W-112-fbody(fs).getlength(sc),y0+(rh-18-fs)/2-2,sc,fs,(248,242,225))
    img.save(path)

def make_poster_card(path):
    cfg=getattr(S,"POSTER",None)
    img=Image.new("RGBA",(W,H),(0,0,0,0)); _scrim(img,120,190); d=ImageDraw.Draw(img)
    if not cfg: img.save(path); return
    lbl=cfg.get("label","")
    if lbl:
        w=run_w(lbl,42); rrect(d,[(W-w)/2-32,160,(W+w)/2+32,242],41,(*CLAY,242)); draw_center(d,176,lbl,42,WHITE)
    if cfg.get("vs"):      draw_center(d,420,cfg["vs"],150,GOLD,sw=2,sfill=(0,0,0,180))
    if cfg.get("tagline"): draw_center(d,720,cfg["tagline"],132,WHITE,sw=2,sfill=(0,0,0,180))
    img.save(path)

def caps_for(sc):
    sid=sc["id"]; D=DUR[sid]
    if sid in CAPS and CAPS[sid]: return [(c["text"],c["a"],c["b"]) for c in CAPS[sid]]
    seps="，。？！、：—"; parts,cur=[],""
    for ch in sc["vo"]:
        if ch=="—": continue
        cur+=ch
        if ch in seps: parts.append(cur.strip("，。？！、：")); cur=""
    if cur.strip(): parts.append(cur.strip("，。？！、："))
    chunks,buf=[],""
    for p in [x for x in parts if x]:
        if len(buf)+len(p)<=18: buf+=p
        else:
            if buf: chunks.append(buf)
            buf=p
    if buf: chunks.append(buf)
    chunks=chunks or [sc["vo"][:18]]; n=sum(len(c) for c in chunks); t=0.0; out=[]
    for j,c in enumerate(chunks):
        seg=D*len(c)/n; a=t; b=(D if j==len(chunks)-1 else t+seg); t=b; out.append((c,a,b))
    return out

def _render_base(src,tin,dur,card,out):
    dim=0.42 if card else 0.06
    subprocess.run(["ffmpeg","-y","-loglevel","error",
        "-ss",f"{tin:.3f}","-t",f"{dur:.3f}","-i",src,
        "-loop","1","-t",f"{dur:.3f}","-i",os.path.join(PNG,"overlay.png"),
        "-filter_complex",
        f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
        f"eq=brightness=-{dim}:saturation=1.03[fg];[fg][1:v]overlay=0:0[v]",
        "-map","[v]","-an","-r",str(FPS),"-c:v","libx264","-preset","medium","-crf","20",
        "-pix_fmt","yuv420p","-t",f"{dur:.3f}",out],check=True)

def _concat(files,out):
    lst=out+".txt"; open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,"-c","copy",out],check=True)

def render_scene(sc):
    sid=sc["id"]; D=DUR[sid]; card=sc["treat"].startswith("card:")
    base=os.path.join(SCN,f"_base_{sid}.mp4")
    clips=sc.get("clips")
    if clips:
        seg=D/len(clips); segfiles=[]
        for i,(cs,ct) in enumerate(clips):
            f=os.path.join(SCN,f"_seg_{sid}_{i}.mp4"); _render_base(os.path.join(SRC,cs+".mp4"),ct,seg,card,f); segfiles.append(f)
        _concat(segfiles,base)
    else:
        _render_base(os.path.join(SRC,sc["src"]+".mp4"),sc["tin"],D,card,base)
    inputs=["-i",base]; overlays=[]; idx=1
    if card:
        cardpng=os.path.join(PNG,("results" if "results" in sc["treat"] else "poster")+".png")
        inputs+=["-loop","1","-t",f"{D:.3f}","-i",cardpng]; overlays.append((idx,None)); idx+=1
    else:
        if sc.get("chip"):
            cp=os.path.join(PNG,f"chip_{sid}.png"); make_chip_png(sc["chip"],cp)
            inputs+=["-loop","1","-t",f"{D:.3f}","-i",cp]; overlays.append((idx,None)); idx+=1
        for j,(c,a,b) in enumerate(caps_for(sc)):
            cp=os.path.join(PNG,f"cap_{sid}_{j:02d}.png"); make_caption_png(c,cp)
            inputs+=["-loop","1","-t",f"{D:.3f}","-i",cp]; overlays.append((idx,(a,b))); idx+=1
    last="0:v"; parts=[]
    for k,(ii,en) in enumerate(overlays):
        o=f"v{k+1}"
        if en is None: parts.append(f"[{last}][{ii}:v]overlay=0:0:eof_action=repeat[{o}]")
        else: parts.append(f"[{last}][{ii}:v]overlay=0:0:eof_action=repeat:enable='between(t,{en[0]:.2f},{en[1]:.2f})'[{o}]")
        last=o
    outp=os.path.join(SCN,f"{sid}.mp4")
    if parts:
        subprocess.run(["ffmpeg","-y","-loglevel","error",*inputs,"-filter_complex",";".join(parts),
            "-map",f"[{last}]","-an","-r",str(FPS),"-c:v","libx264","-preset","medium","-crf","20",
            "-pix_fmt","yuv420p","-t",f"{D:.3f}",outp],check=True)
    else:
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",base,"-c","copy",outp],check=True)
    print(f"  16:9 scene {sid}: {D:5.2f}s  {os.path.getsize(outp)//1024}KB")

if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else "all"
    if cmd=="assets":
        make_overlay(); make_results_card(os.path.join(PNG,"results.png")); make_poster_card(os.path.join(PNG,"poster.png")); print("16:9 bg+cards rendered")
    elif cmd=="scene": render_scene(next(s for s in SCENES if s["id"]==sys.argv[2]))
    elif cmd=="all":
        make_overlay(); make_results_card(os.path.join(PNG,"results.png")); make_poster_card(os.path.join(PNG,"poster.png"))
        for sc in SCENES: render_scene(sc)
