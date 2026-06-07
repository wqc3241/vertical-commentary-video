# -*- coding: utf-8 -*-
"""9:16 render engine. Per scene: a DARK, heavily-blurred MOVING fill of the footage +
semi-transparent clay overlay + centred footage strip + clear Hiragino-W6 text. Supports
word-exact captions (build/captions.json) and montage scenes (a scene with `clips=[(stem,tin),...]`
plays several footage segments in sequence). Cards read from scenes.RESULTS_CARD / POSTER.
Commands: assets | scene <ID> | all | assemble | assemble-voice <wav>"""
import subprocess, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as S
from scenes import SCENES
from PIL import Image, ImageDraw, ImageFont

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(BUILD)
SRC   = os.path.join(ROOT, "source")
AUD   = os.path.join(BUILD, "audio")
PNG   = os.path.join(BUILD, "png");   os.makedirs(PNG, exist_ok=True)
SCN   = os.path.join(BUILD, "scene"); os.makedirs(SCN, exist_ok=True)
OUT   = os.path.join(ROOT, getattr(S, "OUTPUT_NAME", "output_9x16.mp4"))

W, H, FPS = 1080, 1920, 30
CLAY=(196,86,58); GOLD=(226,188,104); WHITE=(248,246,243); INK=(20,16,14)
BODY_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"       # W6 = index 2 (heavy, clean, clear)
COV = set()   # one clean font throughout -> no per-glyph fallback needed
_fc={}
def fbody(sz): _fc.setdefault(("b",sz),ImageFont.truetype(BODY_PATH,sz,index=2)); return _fc[("b",sz)]
def fdisp(sz): return fbody(sz)   # clear font for headlines too

DUR  = {d["id"]: d["dur"] for d in json.load(open(os.path.join(BUILD,"durations.json")))}
CAPS = json.load(open(os.path.join(BUILD,"captions.json"))) if os.path.exists(os.path.join(BUILD,"captions.json")) else {}

# ---------- mixed-font (display + body fallback) draw ----------
def _font_for(c, sz, disp): return fdisp(sz) if (disp and ord(c) in COV) else fbody(sz)
def run_w(text, sz, disp=True): return sum(_font_for(c,sz,disp).getlength(c) for c in text)
def draw_run(d, x, y, text, sz, fill, disp=True, sw=0, sfill=None):
    for c in text:
        f=_font_for(c,sz,disp); d.text((x,y),c,font=f,fill=fill,stroke_width=sw,stroke_fill=sfill); x+=f.getlength(c)
def draw_center(d, y, text, sz, fill, disp=True, sw=0, sfill=None, cx=W/2):
    draw_run(d, cx-run_w(text,sz,disp)/2, y, text, sz, fill, disp, sw, sfill)
def rrect(d, box, r, fill): d.rounded_rectangle(box, radius=r, fill=fill)

# ---------- semi-transparent clay overlay (sits on the DARK MOVING blur of the footage) ----------
# Darkens top (behind chip) + bottom (behind captions) for legibility; lets the dynamic blur
# show through the middle. The blur itself is heavily darkened in render_scene so ad boards
# never read as text.
def make_overlay():
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    clay=(28,15,11)
    for y in range(H):
        if   y<480:  a=int(185-150*(y/480))        # 185 -> 35 (top, behind chip)
        elif y>1440: a=int(35+180*((y-1440)/(H-1440)))  # 35 -> 215 (bottom, behind caption)
        else:        a=35
        d.line([(0,y),(W,y)],fill=(*clay,a))
    for i,al in enumerate([80,55,30]): d.rectangle([i*7,i*7,W-i*7,H-i*7],outline=(0,0,0,al),width=7)
    img.save(os.path.join(PNG,"overlay.png"))

# ---------- overlay PNGs ----------
def make_chip_png(text, path):
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    sz=52; tw=run_w(text,sz); px,py=40,16
    bx0,bx1,by0=(W-tw)/2-px,(W+tw)/2+px,148; by1=by0+sz+py*2
    rrect(d,[bx0,by0,bx1,by1],(by1-by0)/2,(*CLAY,242)); draw_center(d,by0+py-6,text,sz,WHITE,sw=1,sfill=(0,0,0,110))
    img.save(path)

def _wrap_body(text, sz, maxw):
    f=fbody(sz); lines,cur=[],""
    for ch in text:
        if f.getlength(cur+ch)>maxw and cur: lines.append(cur); cur=ch
        else: cur+=ch
    if cur: lines.append(cur)
    return lines

def make_caption_png(text, path):
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    sz=56; lines=_wrap_body(text,sz,900); lh=74
    tw=max(fbody(sz).getlength(l) for l in lines); th=lh*len(lines); px,py=40,22
    bx0,bx1=(W-tw)/2-px,(W+tw)/2+px; by1=1620; by0=by1-th-py*2
    rrect(d,[bx0,by0,bx1,by1],28,(0,0,0,160)); y=by0+py
    for l in lines: draw_center(d,y,l,sz,WHITE,disp=False,sw=3,sfill=(0,0,0,230)); y+=lh
    img.save(path)

def _scrim(img,top=140,bot=210):
    d=ImageDraw.Draw(img)
    for y in range(H): d.line([(0,y),(W,y)],fill=(0,0,0,int(top+(bot-top)*(y/H))))

def make_results_card(path):
    cfg=getattr(S,"RESULTS_CARD",None)
    img=Image.new("RGBA",(W,H),(0,0,0,0)); _scrim(img,150,205); d=ImageDraw.Draw(img)
    if not cfg: img.save(path); return
    draw_run(d,70,196,cfg.get("title","战绩"),104,WHITE,sw=2,sfill=(0,0,0,170))
    pill=cfg.get("pill","")
    if pill:
        w=run_w(pill,36); rrect(d,[70,340,70+w+48,406],30,(*CLAY,242)); draw_run(d,94,350,pill,36,WHITE)
    if cfg.get("subtitle"):
        yy=438
        for ln in cfg["subtitle"].split("\n"): draw_run(d,70,yy,ln,38,(238,226,214),disp=False); yy+=50
    rows=cfg.get("rows",[]); y=600; rh=126 if len(rows)<=8 else int(1010/len(rows))
    for i,(rd,op,sc) in enumerate(rows):
        y0=y+i*rh; last=(i==len(rows)-1) and cfg.get("highlight_last",True)
        rrect(d,[70,y0,W-70,y0+rh-16],18,(*CLAY,238) if last else (255,255,255,30))
        rrect(d,[90,y0+20,240,y0+rh-36],14,(*GOLD,240)); draw_center(d,y0+30,rd,40,INK,cx=165)
        draw_run(d,266,y0+26,op,50,WHITE,disp=False,sw=1,sfill=(0,0,0,150))
        if sc:
            fs=42 if len(sc)<=11 else (30 if len(sc)<=20 else 25)
            draw_run(d,W-92-fbody(fs).getlength(sc),y0+(rh-16-fs)/2-2,sc,fs,(248,242,225),disp=False)
    img.save(path)

def make_poster_card(path):
    cfg=getattr(S,"POSTER",None)
    img=Image.new("RGBA",(W,H),(0,0,0,0)); _scrim(img,150,210); d=ImageDraw.Draw(img)
    if not cfg: img.save(path); return
    lbl=cfg.get("label","")
    if lbl:
        w=run_w(lbl,44); rrect(d,[(W-w)/2-34,250,(W+w)/2+34,336],43,(*CLAY,242)); draw_center(d,266,lbl,44,WHITE)
    draw_center(d,468,cfg.get("left",""),88,WHITE,sw=2,sfill=(0,0,0,180))
    draw_center(d,612,cfg.get("vs","VS"),116,GOLD,sw=2,sfill=(0,0,0,180))
    draw_center(d,800,cfg.get("right",""),88,WHITE,sw=2,sfill=(0,0,0,180))
    if cfg.get("date"):    draw_center(d,1006,cfg["date"],48,(238,226,214),disp=False)
    if cfg.get("tagline"): draw_center(d,1228,cfg["tagline"],130,WHITE,sw=2,sfill=(0,0,0,180))
    img.save(path)

# ---------- scene render: gradient bg + centred footage strip + overlays ----------
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
        if len(buf)+len(p)<=16: buf+=p
        else:
            if buf: chunks.append(buf)
            buf=p
    if buf: chunks.append(buf)
    chunks=chunks or [sc["vo"][:16]]; n=sum(len(c) for c in chunks); t=0.0; out=[]
    for j,c in enumerate(chunks):
        seg=D*len(c)/n; a=t; b=(D if j==len(chunks)-1 else t+seg); t=b; out.append((c,a,b))
    return out

def _render_base(src, tin, dur, card, out):
    """bg(dark moving blur)+clay overlay+centred footage strip -> out (no chip/caps)."""
    bgdim=0.52 if card else 0.42; dim=0.40 if card else 0.04
    subprocess.run(["ffmpeg","-y","-loglevel","error",
        "-ss",f"{tin:.3f}","-t",f"{dur:.3f}","-i",src,
        "-loop","1","-t",f"{dur:.3f}","-i",os.path.join(PNG,"overlay.png"),
        "-filter_complex",
        f"[0:v]fps={FPS},split=2[bb][ff];"
        f"[bb]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=22:2,eq=brightness=-{bgdim}:saturation=0.45[blur];"
        f"[blur][1:v]overlay=0:0[bgt];"
        f"[ff]scale={W}:-2,eq=brightness=-{dim}:saturation=1.05[fg];"
        f"[bgt][fg]overlay=(W-w)/2:(H-h)/2[v]",
        "-map","[v]","-an","-r",str(FPS),"-c:v","libx264","-preset","medium","-crf","20",
        "-pix_fmt","yuv420p","-t",f"{dur:.3f}",out],check=True)

def render_scene(sc):
    sid=sc["id"]; D=DUR[sid]; card=sc["treat"].startswith("card:")
    base=os.path.join(SCN,f"_base_{sid}.mp4")
    clips=sc.get("clips")   # optional montage: [(stem,tin), ...] -> equal slices of D
    if clips:
        seg=D/len(clips); segfiles=[]
        for i,(cs,ct) in enumerate(clips):
            f=os.path.join(SCN,f"_seg_{sid}_{i}.mp4")
            _render_base(os.path.join(SRC,cs+".mp4"), ct, seg, card, f); segfiles.append(f)
        _concat(segfiles, base)
    else:
        _render_base(os.path.join(SRC,sc["src"]+".mp4"), sc["tin"], D, card, base)
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
    print(f"  scene {sid}: {D:5.2f}s  {os.path.getsize(outp)//1024}KB")

def _concat(files,out):
    lst=out+".txt"; open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,"-c","copy",out],check=True)

def _mux(vm,am,total):
    fo=max(total-0.7,0)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",vm,"-i",am,"-filter_complex",
        f"[0:v]fade=t=in:st=0:d=0.4,fade=t=out:st={fo:.2f}:d=0.7[v];[1:a]afade=t=out:st={fo:.2f}:d=0.7[a]",
        "-map","[v]","-map","[a]","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k","-movflags","+faststart","-shortest",OUT],check=True)
    print(f"\nFINAL: {OUT}  ({total:.1f}s)")

def assemble():
    _concat([os.path.join(SCN,s["id"]+".mp4") for s in SCENES],os.path.join(BUILD,"video_master.mp4"))
    _concat([os.path.join(AUD,s["id"]+".wav") for s in SCENES],os.path.join(BUILD,"audio_master.wav"))
    _mux(os.path.join(BUILD,"video_master.mp4"),os.path.join(BUILD,"audio_master.wav"),sum(DUR[s["id"]] for s in SCENES))

def assemble_voice(wav):
    vm=os.path.join(BUILD,"video_master.mp4"); _concat([os.path.join(SCN,s["id"]+".mp4") for s in SCENES],vm)
    total=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",vm]).strip())
    _mux(vm,wav,total)

if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else "all"
    if cmd=="assets":
        make_overlay(); make_results_card(os.path.join(PNG,"results.png")); make_poster_card(os.path.join(PNG,"poster.png")); print("bg+cards rendered")
    elif cmd=="scene": render_scene(next(s for s in SCENES if s["id"]==sys.argv[2]))
    elif cmd=="all":
        make_overlay(); make_results_card(os.path.join(PNG,"results.png")); make_poster_card(os.path.join(PNG,"poster.png"))
        for sc in SCENES: render_scene(sc)
    elif cmd=="assemble": assemble()
    elif cmd=="assemble-voice": assemble_voice(sys.argv[2])
