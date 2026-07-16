# -*- coding: utf-8 -*-
"""TEMPLATE for one video. Copy to <project>/build/scenes.py and fill in.
This is the ONLY file that changes per video; the engine scripts stay as-is.

A scene = one chunk of narration (`vo`) shown over footage (or a graphic card). The narration
length (durations.json) drives each scene's length.

NUMBERS — keep two forms in sync:
  - `vo` (SPOKEN, fed to the cloned voice): write numbers as CHINESE numerals (六比三, 二零二六),
    otherwise F5-TTS reads them as English digits.
  - `CAPTIONS` (DISPLAYED): the user's exact lines, numbers as DIGITS (6-3) — clearer to read.
  Each CAPTIONS line MUST be word-for-word the same as the spoken text (only numerals differ),
  or the word-exact alignment in caption_times.py will drift.
"""

OUTPUT_NAME = "output_9x16.mp4"          # final file, written to the project root
# THEME = dict(accent=(196,86,58), badge=(226,188,104))   # optional clay/gold tweak

SCENES = [
    # id | src (source/<src>.mp4) | tin (rough in-point; pick_ends snaps the END unless lock/override)
    # treat: "blur" | "card:results" | "card:poster" ;  chip: short headline (optional)
    dict(id="S1", src="01_clip", tin=160, treat="blur", chip="开场大字",
         vo="开场钩子，口语、有冲击力的一句。"),
    dict(id="S2", src="02_clip", tin=70,  treat="blur", chip="",
         vo="第二段旁白，数字写中文：六比三、二零二六年。"),
    # ... more footage scenes ...
    dict(id="S9", src="06_clip", tin=455, treat="card:results", chip="",
         vo="战绩卡这一段的旁白。"),

    # MONTAGE scene: play several footage segments in one scene (great for a post-win ending —
    # cup-raise, photo-with-runner-up, speech). Each clip gets an equal slice of the scene length.
    dict(id="S10", src="06_clip", tin=1, treat="blur", chip="收尾大字",
         clips=[("06_clip", 1148), ("06_clip", 843), ("06_clip", 1180)],
         vo="收尾旁白。"),
]

# DISPLAY captions = the user's exact line-breaks (one line per caption), DIGITS for numbers.
# Concatenation of each scene's lines must equal its spoken `vo` (only numerals differ).
CAPTIONS = {
    "S1": ["开场钩子，口语、有冲击力的一句。"],
    "S2": ["第二段旁白，数字写中文：6 比 3、2026 年。"],
    # "S10": ["收尾旁白。"],
}

RESULTS_CARD = dict(           # treat="card:results"; rows = (round, opponent, score) — DIGITS
    title="七战封后", pill="夺冠之路 · 只丢一盘",
    subtitle="一句副标题",
    rows=[("R1","对手","6-3 6-3"), ("决赛","决赛对手","6-3 6-2")],
    highlight_last=True,
)
POSTER = dict(label="赛事名 · TOURNAMENT", left="选手", vs="VS", right="对手",
             date="日期", tagline="拭目以待")   # treat="card:poster"

# --- optional per-project knobs (all read via getattr, safe to omit; 2026-07孙心然项目新增) ---
CARDS = {}            # {"key": dict(同RESULTS_CARD结构)} → treat="card:<key>" 用 card_<key>.png;
                      # 卡片规则: ≤3s 插片穿插比赛画面(整场景静置>3s掉粉);卡片 title="" 避免与场景 chip 重叠
MUTE_AMBIENT = set()  # {"ig_milan_champ",…} 原声强制静音的源(IG制作类reel的配乐≠现场声,必须静音)
FIT_WINDOWS  = []     # [("stem",tin),…] 跳过YOLO跟踪、整幅原图/原帧居中+模糊补边(裁不全人/主体被遮挡时用)
IG_EXCLUDE   = ()     # ("igx_e",) ig前缀但不走满屏cover-crop的源(裁切会切掉主体→回落模糊补边路径)
# PART_MAP = {"A":["S1","S2","S3"],…}  # 分段预览的分组(场景id不带段前缀时必填)
# 蒙太奇连续长镜头: clips=[("stem",100.0),("stem","+"),("stem","+")] — "+"=紧接上一片(REQUIRED TAIL解析),
# reframe_span.py 对整段只跑一次YOLO再切片,避免每片重新定位跳变。

# --- point-boundary / footage guidance ---
# END_OVERRIDES = {"S1": 729.0}      # force a scene to END exactly here (a clean win / chosen frame)
# AVOID_ENDS   = {"06_clip": [242.0]}# never end near these (opponent celebration / graphics / logo cards)
# Set a scene's tin + "lock": True to pin an exact hand-chosen window (pick_ends leaves it).
# WHO IS WHO: at a trophy ceremony the RUNNER-UP is presented & speaks FIRST — verify (kit colour)
# that ending/trophy footage is YOUR player, not the runner-up. Establishing shots (the court with
# the event logo) are filler, not match play — avoid them in round scenes.

# ----------------------------------------------------------------------------
# REQUIRED TAIL — resolves "+" contiguous tins from durations.json, then applies
# snapped/locked in-points on import. Do not remove.
import json as _json, os as _os
_d = _os.path.dirname(__file__)
_dp = _os.path.join(_d, "durations.json")
if _os.path.exists(_dp):
    _DUR = {x["id"]: x["dur"] for x in _json.load(open(_dp))}
    for _s in SCENES:
        _clips = _s.get("clips")
        if _clips and _s["id"] in _DUR:
            _seg = _DUR[_s["id"]] / len(_clips)
            _clips = [list(x) for x in _clips]
            for _i, _c2 in enumerate(_clips):
                if _c2[1] == "+":
                    _c2[1] = round(float(_clips[_i-1][1]) + _seg, 3)
            _s["clips"] = [tuple(x) for x in _clips]
_p = _os.path.join(_d, "proposed_tins.json")
if _os.path.exists(_p):
    _ov = _json.load(open(_p))
    for _s in SCENES:
        if _s["id"] in _ov and not _s.get("lock"): _s["tin"] = _ov[_s["id"]]  # locked scenes keep hand-set tin
_MANUAL = {}     # e.g. {"S3": 0.0} — hand-placed in-points win over everything
for _s in SCENES:
    if _s["id"] in _MANUAL: _s["tin"] = _MANUAL[_s["id"]]
