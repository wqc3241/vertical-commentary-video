#!/usr/bin/env python3
"""cover_bust.py — 把 GPT 补全的本人半身形象抠像、裁到"胸部及以上"、加奶油描边, 贴到双封面左下角(贴底)。

用法 (在项目根目录):
  python3 scripts/cover_bust.py --figure final/covers/upper_body_raw.png \
      --v final/covers/封面图-竖3x4_无头像.jpg --h final/covers/封面图-横4x3_无头像.jpg

输入:
  --figure  GPT 出的半身正面图 (纯白背景, 3:4)。无 alpha 时自动用 macOS Vision 抠像 (figure_tool cutout);
            已是透明 PNG 时直接用。
  --v/--h   不带人物的竖版 3:4 / 横版 4:3 插画封面 (任一可省; GPT raw PNG 直接给, 自动缩放/居中裁到 1242×1656 / 1440×1080)。
            首次会存 final/covers/*_无头像.jpg 作权威底图, 之后从备份合成; 换新底图加 --refresh-backup。
输出 (默认写到 --out-dir=当前目录, 并同步到 final/covers/):
  封面图-竖3x4.jpg / 封面图-横4x3.jpg ; 原图另存 *_无头像.jpg (不存在才写, 不覆盖旧备份);
  final/covers/upper_body_cut.png (抠像结果, 复用/复查)。
裁切规则 (2026-09-04 用户拍板"只要胸部及以上、放大"):
  chest_y = 人脸框底边 + CHEST_K × 人脸框高 (CHEST_K=1.22, 由拍板样张反算);
  找不到脸时退到 bbox 高度的 52%。--chest-y N 绝对像素 / --chest-frac F 手动覆盖。
版式常量 (拍板值): 竖版人物高 620px, x=30; 横版 470px, x=40; 描边 7px 奶油色 (250,243,225); 贴底。
"""
import argparse, os, shutil, subprocess, sys
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_SCRIPTS = os.path.expanduser("~/.claude/skills/vertical-commentary-video/scripts")
TARGET = {"v": (1242, 1656), "h": (1440, 1080)}   # 小红书竖 3:4 / 横 4:3
CHEST_K = 1.22          # 胸线 = 脸底 + 1.22 × 脸高 (拍板样张: 脸 y=123,h=287 → 胸线 760)
CHEST_FRAC_FALLBACK = 0.52
STROKE_PX = 7
STROKE_RGBA = (250, 243, 225, 255)
LAYOUT = {  # (目标高, x 偏移)
    "v": (620, 30),   # 1242×1656 竖版
    "h": (470, 40),   # 1440×1080 横版
}


def figure_tool():
    """返回 Vision 工具路径; 缺二进制时用 swiftc 现编 (需要 Xcode CLT)。"""
    env = os.environ.get("FIGURE_TOOL")
    if env and os.path.exists(env):
        return env
    # 脚本可能被 cp 到 <project>/build/, .swift 只在 skill 目录 → 两处都找
    base = HERE if os.path.exists(os.path.join(HERE, "figure_tool.swift")) else SKILL_SCRIPTS
    binp = os.path.join(base, "figure_tool")
    src = os.path.join(base, "figure_tool.swift")
    if not os.path.exists(src):
        sys.exit(f"[cover_bust] figure_tool.swift not found in {HERE} or {SKILL_SCRIPTS}")
    if not os.path.exists(binp) or os.path.getmtime(binp) < os.path.getmtime(src):
        print("[cover_bust] compiling figure_tool.swift …")
        subprocess.run(["xcrun", "swiftc", "-O", src, "-o", binp], check=True)
    return binp


def cutout(src_png, dst_png):
    r = subprocess.run([figure_tool(), "cutout", src_png, dst_png], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[cover_bust] cutout failed: {r.stderr.strip()}")
    print(f"[cover_bust] cutout {r.stdout.strip()} -> {dst_png}")


def face_rect(png):
    r = subprocess.run([figure_tool(), "face", png], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    x, y, w, h = map(int, r.stdout.split())
    return x, y, w, h


def with_stroke(im, px=STROKE_PX, color=STROKE_RGBA):
    a = im.getchannel("A")
    dil = a.filter(ImageFilter.MaxFilter(px * 2 + 1))
    ring = Image.new("RGBA", im.size, color)
    ring.putalpha(dil)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(ring)
    out.alpha_composite(im)
    return out


def fit_cover(im, key):
    """raw 底图等比缩放到目标尺寸; 比例差 >1% 时先居中裁到目标比例 (GPT 3:4/4:3 直出通常刚好)。"""
    tw, th = TARGET[key]
    if im.size == (tw, th):
        return im
    ar, tar = im.width / im.height, tw / th
    if abs(ar - tar) / tar > 0.01:
        if ar > tar:
            nw = round(im.height * tar); im = im.crop(((im.width - nw) // 2, 0, (im.width - nw) // 2 + nw, im.height))
        else:
            nh = round(im.width / tar); im = im.crop((0, (im.height - nh) // 2, im.width, (im.height - nh) // 2 + nh))
        print(f"[cover_bust] {key}: aspect {ar:.3f}->{tar:.3f} center-cropped")
    return im.resize((tw, th), Image.LANCZOS)


def compose(cover_path, out_path, bust, target_h, x, anchor, key):
    im = fit_cover(Image.open(cover_path).convert("RGBA"), key)
    W, H = im.size
    s = target_h / bust.height
    q = bust.resize((max(1, round(bust.width * s)), target_h), Image.LANCZOS)
    pad = STROKE_PX + 3
    canvas = Image.new("RGBA", (q.width + 2 * pad, q.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(q, (pad, pad))
    q2 = with_stroke(canvas)
    if anchor == "right":
        x = W - x - q.width
    im.alpha_composite(q2, (x - pad, H - q2.height + pad))   # 贴底: 人物底边=画布底边, 描边溢出被裁
    im.convert("RGB").save(out_path, quality=93)
    print(f"[cover_bust] {out_path}  {W}x{H}  bust {q.width}x{q.height} @x={x}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--figure", required=True, help="GPT 半身图 (白底) 或已抠像 RGBA PNG")
    ap.add_argument("--v", help="竖版 3:4 无人物封面")
    ap.add_argument("--h", help="横版 4:3 无人物封面")
    ap.add_argument("--out-dir", default=".", help="成品输出目录 (项目根)")
    ap.add_argument("--chest-y", type=int, help="胸线绝对像素 (覆盖自动)")
    ap.add_argument("--chest-frac", type=float, help="胸线 = bbox 顶 + F×bbox 高 (覆盖自动)")
    ap.add_argument("--v-height", type=int, default=LAYOUT["v"][0])
    ap.add_argument("--v-x", type=int, default=LAYOUT["v"][1])
    ap.add_argument("--h-height", type=int, default=LAYOUT["h"][0])
    ap.add_argument("--h-x", type=int, default=LAYOUT["h"][1])
    ap.add_argument("--anchor", choices=["left", "right"], default="left")
    ap.add_argument("--force-cutout", action="store_true", help="即使输入已有 alpha 也重新抠像")
    ap.add_argument("--refresh-backup", action="store_true", help="用本次 --v/--h 覆盖 final/covers/*_无头像.jpg (换了新底图时)")
    a = ap.parse_args()

    out_dir = os.path.abspath(a.out_dir)
    covers_dir = os.path.join(out_dir, "final", "covers")
    os.makedirs(covers_dir, exist_ok=True)

    fig = Image.open(a.figure)
    cut_png = os.path.join(covers_dir, "upper_body_cut.png")
    if fig.mode == "RGBA" and not a.force_cutout and fig.getchannel("A").getextrema()[0] == 0:
        cut = fig
        if os.path.abspath(a.figure) != cut_png:
            fig.save(cut_png)
    else:
        src = a.figure
        if not src.lower().endswith(".png"):
            src = os.path.join(covers_dir, "upper_body_raw.png")
            fig.convert("RGB").save(src)
        cutout(src, cut_png)
        cut = Image.open(cut_png).convert("RGBA")

    bb = cut.getchannel("A").getbbox()
    if not bb:
        sys.exit("[cover_bust] empty alpha after cutout")
    if a.chest_y:
        chest_y = a.chest_y
    elif a.chest_frac:
        chest_y = int(bb[1] + a.chest_frac * (bb[3] - bb[1]))
    else:
        fr = face_rect(cut_png)
        if fr:
            x, y, w, h = fr
            chest_y = int(y + h + CHEST_K * h)
            print(f"[cover_bust] face x={x} y={y} w={w} h={h} -> chest_y={chest_y}")
        else:
            chest_y = int(bb[1] + CHEST_FRAC_FALLBACK * (bb[3] - bb[1]))
            print(f"[cover_bust] no face found, fallback chest_y={chest_y}")
    chest_y = max(bb[1] + 50, min(chest_y, bb[3]))
    bust = cut.crop((bb[0], bb[1], bb[2], chest_y))
    bust.save(os.path.join(covers_dir, "upper_body_bust.png"))
    print(f"[cover_bust] bbox={bb} chest_y={chest_y} bust={bust.size}")

    for key, cover in (("v", a.v), ("h", a.h)):
        if not cover:
            continue
        name = "封面图-竖3x4" if key == "v" else "封面图-横4x3"
        backup = os.path.join(covers_dir, f"{name}_无头像.jpg")
        if a.refresh_backup or not os.path.exists(backup):
            fit_cover(Image.open(cover).convert("RGB"), key).save(backup, quality=95)
            print(f"[cover_bust] backup -> {backup}")
        target_h, x = (a.v_height, a.v_x) if key == "v" else (a.h_height, a.h_x)
        out = os.path.join(out_dir, f"{name}.jpg")
        compose(backup, out, bust, target_h, x, a.anchor, key)   # 永远从权威底图合成
        shutil.copyfile(out, os.path.join(covers_dir, f"{name}.jpg"))


if __name__ == "__main__":
    main()
