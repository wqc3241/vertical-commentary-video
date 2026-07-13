# -*- coding: utf-8 -*-
"""照片 -> 15.3s 1080x1920 Ken-Burns 竖屏片, PIL 仿射亚像素采样(无 zoompan 整数抖动)。"""
import os, subprocess
from PIL import Image
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH=os.path.join(ROOT,"source","photos"); SRC=os.path.join(ROOT,"source")
W,H,FPS,NF=1080,1920,30,460
JOBS=[
 ("ig_ph_rakety",   "bf_rakety.jpg",        None,               0.45),
 ("ig_ph_strom",    "bf_strom.jpg",         None,               0.60),
 ("ig_ph_2016",     "childhood_2016_hi.jpg",None,               0.30),
 ("ig_ph_zed",      "bf_zed.jpg",           None,               0.50),
 ("ig_ph_taska",    "bf_taska.jpg",         None,               0.52),
 ("ig_ph_momlinda", "mom_inset.jpg",        (0.175,0.28,0.345,0.780), 0.50),
 ("ig_ph_rg2021",   "rg2021_trophy.jpg",    (0.44,0.0,0.92,1.0), 0.52),
 ("ig_ph_berlinlake","berlin_lake.jpg",     None,               0.50),
]
for stem,fn,pre,cx in JOBS:
    out=os.path.join(SRC,stem+".mp4")
    im=Image.open(os.path.join(PH,fn)).convert("RGB")
    if pre:
        w,h=im.size; im=im.crop((int(pre[0]*w),int(pre[1]*h),int(pre[2]*w),int(pre[3]*h)))
    w,h=im.size
    cw=int(h*9/16)
    if cw<=w:
        cx_px=int(cx*w); l=max(0,min(w-cw,cx_px-cw//2)); box=(l,0,l+cw,h)
    else:
        ch=int(w*16/9); t=max(0,(h-ch)//2); box=(0,t,w,t+ch)
    im=im.crop(box)
    # upscale once for quality headroom (2x output max)
    if im.width < 2*W: im=im.resize((2*W, 2*H), Image.LANCZOS)
    sw,sh=im.size
    p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
        "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-t",f"{NF/FPS:.3f}","-an",
        "-vf","eq=saturation=1.03","-c:v","libx264","-preset","medium","-crf","15","-pix_fmt","yuv420p",out],
        stdin=subprocess.PIPE)
    for i in range(NF):
        z=1.0+0.13*(i/(NF-1))
        vw=sw/z; vh=sh/z
        ox=(sw-vw)/2.0; oy=(sh-vh)/2.0
        a=vw/W; e=vh/H
        fr=im.transform((W,H), Image.AFFINE, (a,0.0,ox, 0.0,e,oy), resample=Image.BICUBIC)
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    assert p.returncode==0, stem
    print("built",stem)
print("PHOTOS DONE (subpixel)")
