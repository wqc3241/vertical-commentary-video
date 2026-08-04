# -*- coding: utf-8 -*-
"""FINAL DELIVERY STEP (user standing rule, 2026-07-13): append the branded ending
(assets/ending.mov, 点赞收藏关注 card, native 1080x1920@30) to the assembled video and
re-encode the WHOLE deliverable to 1080p 60fps.

  python build/finalize_ending.py <assembled.mp4> [out.mp4]

- 9:16 input  -> ending used as-is (scaled 1080x1920), output 1080x1920@60
- 16:9 input  -> ending CENTER-CROPPED to 16:9 (crop=1080:608:0:738 holds avatar+CTA text), output 1920x1080@60
- out omitted -> replaces the input atomically (tmp encode + rename)
Run AFTER assemble_ambient.py (9:16) / assemble16.py (16:9). Idempotent: skips when the
format comment tag says finalized-with-ending.

NOTE (2026-07-13): single-pass filter_complex concat dies on this Mac's ffmpeg
("Could not open encoder before EOF", -22) — use the 3-step method: transcode both
parts to IDENTICAL specs, then concat demuxer -c copy. Don't refactor back."""
import os, sys, json, subprocess, tempfile

# 个人资产家 (品牌片尾属个人形象, 绝不入 git — 见 docs/ONBOARDING.md)
PERSONAL = os.environ.get("PERSONAL_ASSETS", "/Volumes/Storage/avatar-template/assets")
_CAND = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "ending.mov"),
         os.path.join(PERSONAL, "ending.mov")]
ENDING = next((p for p in _CAND if os.path.exists(p)), None)
# 片尾快速口播 (user rule 2026-08-03: "关注我，了解更多网球故事，网球知识" 以最快速度).
# 资产存在则自动混进片尾段 (卡片自带音轨压 0.5 让语音清晰); 不存在则行为与旧版完全一致.
ENDVOICE = next((p for p in (c.replace("ending.mov", "ending_voice.wav") for c in _CAND)
                 if os.path.exists(p)), None)

def no_ending_finalize(src, out, w, h):
    """新用户无片尾资产: 只做 1080p60 统一重编码, 提示走 ONBOARDING 录制."""
    print("⚠ 未找到片尾资产 ending.mov (个人品牌件, 不随仓库分发) — 跳过片尾, 仅统一 1080p60。")
    print("  制作自己的片尾: 见 docs/ONBOARDING.md 第3步; 就绪后放入 $PERSONAL_ASSETS 再重跑。")
    vf = ("scale=1920:1080" if w >= h else "scale=1080:1920") + ":flags=lanczos,fps=60,format=yuv420p"
    fd, tmp = tempfile.mkstemp(suffix=".mp4", dir=os.path.dirname(os.path.abspath(out)) or "."); os.close(fd)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",src,"-vf",vf,
        "-c:v","libx264","-preset","medium","-crf","17","-c:a","aac","-b:a","192k",
        "-metadata","comment=finalized-with-ending","-movflags","+faststart",tmp], check=True)
    os.replace(tmp, out)

def probe(p):
    j = json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "stream=codec_type,width,height","-show_entries","format=duration:format_tags=comment",
        "-of","json",p]))
    v = next(s for s in j["streams"] if s["codec_type"]=="video")
    return v["width"], v["height"], float(j["format"]["duration"]), (j["format"].get("tags") or {}).get("comment","")

def enc(src, vf, out):
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",src,
        "-vf",vf,"-c:v","libx264","-preset","medium","-crf","17",
        "-c:a","aac","-b:a","192k","-ar","48000","-ac","2",out], check=True)

def enc_ending(src, vf, out):
    if not ENDVOICE:
        return enc(src, vf, out)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",src,"-i",ENDVOICE,
        "-filter_complex",
        f"[0:v]{vf}[v];[0:a]volume=0.5[bg];[1:a]apad[vo];"
        f"[bg][vo]amix=inputs=2:duration=first:normalize=0[a]",
        "-map","[v]","-map","[a]","-c:v","libx264","-preset","medium","-crf","17",
        "-c:a","aac","-b:a","192k","-ar","48000","-ac","2",out], check=True)

def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv)>2 else src
    w,h,dur,tag = probe(src)
    if tag == "finalized-with-ending":
        print(f"SKIP: {src} already finalized"); return
    if ENDING is None:
        no_ending_finalize(src, out, w, h); return
    if w>=h:   # 16:9
        mvf = "scale=1920:1080:flags=lanczos,fps=60,format=yuv420p"
        evf = "crop=1080:608:0:738,scale=1920:1080:flags=lanczos,fps=60,format=yuv420p"
    else:      # 9:16
        mvf = "scale=1080:1920:flags=lanczos,fps=60,format=yuv420p"
        evf = "scale=1080:1920:flags=lanczos,fps=60,format=yuv420p"
    td = tempfile.mkdtemp(prefix="fin_")
    m, e, lst = os.path.join(td,"m.mp4"), os.path.join(td,"e.mp4"), os.path.join(td,"l.txt")
    enc(src, mvf, m); enc_ending(ENDING, evf, e)
    open(lst,"w").write(f"file '{m}'\nfile '{e}'\n")
    fd, tmp = tempfile.mkstemp(suffix=".mp4", dir=os.path.dirname(os.path.abspath(out)) or "."); os.close(fd)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,
        "-c","copy","-metadata","comment=finalized-with-ending","-movflags","+faststart",tmp], check=True)
    os.replace(tmp, out)
    for f in (m,e,lst):
        try: os.remove(f)
        except OSError: pass
    w2,h2,d2,_ = probe(out)
    print(f"FINAL 1080p60+ending: {out}  {w2}x{h2}  {d2:.1f}s (was {dur:.1f}s)")

if __name__ == "__main__":
    main()
