#!/usr/bin/env python3
"""「网球练习」账号封面渲染器 — 版式对齐 2026-08-17 用户拍板的 GPT 封面。

与 publish-xhs-douyin/scripts/make_covers.py 的区别(用户 2026-08-17 明确要求):
  · 左上角实心红棕圆角胶囊 + 白字, 不是顶部居中的小灰字
  · 标题 Songti SC Black 白字 + 深色描边, 紧字距铺满 94% 宽, 不是宽字距细明朝
  · 副标题金色 #F9E093 加粗, 紧贴标题下方, 中间没有分隔线
版式比例全部由 GPT 成稿逐像素量出(见下 SPEC 注释)。

用法:
  make_covers_practice.py --video 源.mp4 --t 93.3 --title "练习 vs UTR 6+" \
      --sub "复盘提高" --tag "网球练习" --outdir final/covers/ \
      --bias-v 0.51 --bias-h 0.0
"""
import argparse, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"
IDX_BLACK, IDX_BOLD = 0, 1

V_W, V_H = 1242, 1656          # 竖 3:4
H_W, H_H = 1440, 1080          # 横 4:3

# SPEC — 从 GPT 成稿 (1086x1448) 量得, 均为画布比例
CAP_X, CAP_Y, CAP_H = .028, .032, .057   # 胶囊左上角与高度
CAP_PAD_X, CAP_R = .055, .30             # 胶囊左右内边距(占胶囊高)、圆角(占胶囊高)
TITLE_Y, TITLE_H, TITLE_MAXW = .113, .137, .94
SUB_Y, SUB_H = .259, .052
C_CAPSULE = (120, 31, 21)
C_WHITE = (255, 255, 255)
C_GOLD = (249, 224, 147)
C_STROKE = (45, 45, 44)


def font(idx, size):
    return ImageFont.truetype(SONGTI, size, index=idx)


def fit(draw, txt, idx, target_h, max_w, H):
    """按目标字高起算, 再缩到不超过 max_w。GPT 稿的标题是铺满宽度的紧字距。"""
    size = int(target_h * H)
    while size > 24:
        f = font(idx, size)
        if draw.textlength(txt, font=f) <= max_w:
            return f
        size -= 4
    return font(idx, size)


def grad_top(img, strength=210, reach=.52):
    W, H = img.size
    g = Image.new("L", (1, H), 0)
    for y in range(H):
        t = max(0.0, 1.0 - y / (H * reach))
        g.putpixel((0, y), int(strength * (t ** 1.35)))
    veil = Image.merge("RGBA", (*[Image.new("L", (W, H), 0)] * 3, g.resize((W, H))))
    return Image.alpha_composite(img, veil)


def crop_to(src, rw, rh, bias):
    target = rw / rh
    if src.width / src.height > target:
        cw, ch = int(src.height * target), src.height
    else:
        cw, ch = src.width, int(src.width / target)
    x = int((src.width - cw) * bias)
    return src.crop((x, (src.height - ch) // 2, x + cw, (src.height - ch) // 2 + ch))


def render(src, W, H, title, sub, tag, out, bias):
    img = crop_to(src, W, H, bias).resize((W, H), Image.LANCZOS).convert("RGBA")
    img = grad_top(img)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    if tag:
        ch = int(CAP_H * H)
        ft = font(IDX_BOLD, int(ch * .52))
        pad = int(ch * CAP_PAD_X * 4)
        tw = d.textlength(tag, font=ft)
        x0, y0 = int(CAP_X * W), int(CAP_Y * H)
        d.rounded_rectangle([x0, y0, x0 + tw + pad * 2, y0 + ch],
                            radius=int(ch * CAP_R), fill=(*C_CAPSULE, 255))
        bb = ft.getbbox(tag)
        d.text((x0 + pad, y0 + (ch - (bb[3] - bb[1])) / 2 - bb[1]), tag,
               font=ft, fill=(*C_WHITE, 255))

    ftitle = fit(d, title, IDX_BLACK, TITLE_H, W * TITLE_MAXW, H)
    tw = d.textlength(title, font=ftitle)
    d.text(((W - tw) / 2, TITLE_Y * H), title, font=ftitle, fill=(*C_WHITE, 255),
           stroke_width=max(3, int(W * .0055)), stroke_fill=(*C_STROKE, 235))

    if sub:
        fsub = fit(d, sub, IDX_BOLD, SUB_H, W * .7, H)
        sw = d.textlength(sub, font=fsub)
        d.text(((W - sw) / 2, SUB_Y * H), sub, font=fsub, fill=(*C_GOLD, 255),
               stroke_width=max(2, int(W * .0025)), stroke_fill=(*C_STROKE, 210))

    Image.alpha_composite(img, ov).convert("RGB").save(out, "JPEG", quality=94,
                                                      subsampling=0)
    return out


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--video"); g.add_argument("--image")
    p.add_argument("--t", type=float, default=0)
    p.add_argument("--title", required=True)
    p.add_argument("--sub", default="")
    p.add_argument("--tag", default="网球练习")
    p.add_argument("--outdir", required=True)
    p.add_argument("--bias-v", type=float, default=.5)
    p.add_argument("--bias-h", type=float, default=.5)
    a = p.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    if a.video:
        tmp = os.path.join(tempfile.mkdtemp(), "f.png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(a.t),
                        "-i", a.video, "-frames:v", "1", tmp, "-y"], check=True)
        src = Image.open(tmp)
    else:
        src = Image.open(a.image)

    v = render(src, V_W, V_H, a.title, a.sub, a.tag,
               os.path.join(a.outdir, "封面图-竖3x4.jpg"), a.bias_v)
    h = render(src, H_W, H_H, a.title, a.sub, a.tag,
               os.path.join(a.outdir, "封面图-横4x3.jpg"), a.bias_h)
    for f in (v, h):
        print(f, Image.open(f).size, f"{os.path.getsize(f)//1024}KB")


if __name__ == "__main__":
    main()
