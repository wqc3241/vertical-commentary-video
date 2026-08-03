# -*- coding: utf-8 -*-
"""IndexTTS-2 配音引擎 (2026-08-02 黄泽林 bake-off 后成为默认; F5 regen_tts.py 退为后备).

bake-off 实测(同参考同稿盲听, 用户判"更清晰"):
  句末连读 9 vs F5 13 (同口径) / ATP 逐字母单稿全对(F5 十稿全废) / 全片 ~35min vs F5 111min.
用法:
  /Volumes/Storage/indextts2/.venv/bin/python build/regen_tts_itts.py           # 全部场景
  /Volumes/Storage/indextts2/.venv/bin/python build/regen_tts_itts.py S3,S9    # 指定场景(其余保留)
输出与 F5 版完全同接口: build/audio/<id>.wav (48k stereo loudnorm) + durations.json
=> caption_times / render / preview / assemble 全部无改动直接用.

设计要点(每条都是实战换来的):
1. **逐句合成 + 程序化句间停顿(默认, 不可关)** — 两代引擎都会吞 。？！ 停顿
   (F5 13处 / ITTS 9处, "二百五十。八强"被连成"258"是用户耳朵抓的). 句子分开合成、
   句间插 0.30s 本段室内底噪 + 10ms 余弦融合, 该类缺陷整类消失.
2. **16G Mac 一律 CPU** — MPS 有泄漏, 每进程只能出 1 段就顶到水位; CPU 50-80s/段
   RSS~2G 整机无感. 驱动照旧分组独立进程(4-6段/组)+nohup&disown.
3. **拼音硬纠正** — 难字在 scenes.py 加 `PINYIN = {"昺": "BING3"}`, 合成文本按表替换
   (字幕不动). 语法=行内大写拼音+声调数字, 合法音节见 indextts2/checkpoints/pinyin.vocab.
   前后鼻音(林LIN2/玲)这类标了也可能仍偏 — 标注后让用户终审, 不要空耗稿数.
4. **语速** — 原生偏快, 默认 atempo=SPEECH_TEMPO(0.96; 0.93曾被用户嫌慢, 2026-08-03校准); scenes.py 可覆盖.
5. **whisper 验证门** (F5 四重门裁剪版: 无参考泄漏问题, 保留 相似度/幻觉插入/缩写逐字母):
   假警报照旧=繁体/同音/数字归一 — 但 **数字紧挨句号的 digit-diff 不是假警报**(258 教训).
6. **相似度在拼音平面比对** (2026-08-03 伊埃拉实战加): 人名密集的稿子(伊埃拉/佩古拉/斯瓦泰克)
   whisper 同音漂移(强→墙/坂→阪/贯→关)会把汉字 sim 压穿 0.80, 每场白烧满稿. lazy_pinyin
   无声调折叠后同音=相同, 一稿直过. 幻觉插入检测仍在汉字平面(不受影响).
7. **句尾残渣 (vocoder尾巴)**: ITTS 偶发在句尾吐 ~80ms/2kHz 擦音残片("zh"一声), 逐句拼接后
   以"静音包围的孤岛"形式存在句界处; 停顿越短越显耳. 合成后跑 `clean_clicks.py` 清一遍
   (频谱鉴定+贴身小窗+纯静音源替换, 时长零变化). ⚠替换源必须"窗峰值<0.012"验证过的纯底噪,
   宽窗就近取样会把弱人声克隆进停顿 (whisper 曾听出幽灵音节"阿满贵").
"""
import os, sys, json, re, subprocess, tempfile, shutil, difflib, wave, time
import numpy as np

BUILD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUILD)
from scenes import SCENES, CAPTIONS
PINYIN = {}
try:
    from scenes import PINYIN            # 可选难字表
except Exception:
    pass

ITTS_HOME = os.environ.get("ITTS_HOME", "/Volumes/Storage/indextts2")
VOICE_REF = os.environ.get("VOICE_REF", "/Volumes/Storage/voice-clone/voice_ref_tennis_backup.wav")
WHISPER = os.environ.get("WHISPER_BIN", "whisper")   # Homebrew CLI, 与 F5 管线同款
SPEECH_TEMPO = float(os.environ.get("SPEECH_TEMPO", "0.96"))
AUD = os.path.join(BUILD, "audio"); os.makedirs(AUD, exist_ok=True)
PAUSE = 0.20          # 句间停顿 (2026-08-03 伊埃拉预览用户校准: 0.30听感太长)
FADE = 0.010
MAX_TRIES = 3
SENT_SPLIT = re.compile(r"([。？！])")

TARGETS = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None

# ---------- 文本 ----------
_D = {'0':'零','1':'一','2':'二','3':'三','4':'四','5':'五','6':'六','7':'七','8':'八','9':'九'}
_TRAD = str.maketrans(
    "後沒來還學裡歲產馬蘭勝負績轉業職圓夢寫歷萬億圖書館開關門東車貝見長問間們幾點無爲為與獎讓誰請謝運動員專屬網絡續約錄擊敗數據隊師賽場館歐陽對這時實強輸給亞結卻過線練維園親魯闖進贏個迴爾頓庫兩屆",
    "后没来还学里岁产马兰胜负绩转业职圆梦写历万亿图书馆开关门东车贝见长问间们几点无为为与奖让谁请谢运动员专属网络续约录击败数据队师赛场馆欧阳对这时实强输给亚结却过线练维园亲鲁闯进赢个回尔顿库两届")
def clean(s):
    s = s.translate(_TRAD)
    s = s.replace("一零零", "一百")
    return re.sub(r'[^0-9A-Za-z一-鿿]', '', s)
d2c = lambda s: "".join(_D.get(ch, ch) for ch in s)

def apply_pinyin(text):
    for ch, py in PINYIN.items():
        text = text.replace(ch, py)
    return text

def sentences(vo):
    parts, buf = [], ""
    for tok in SENT_SPLIT.split(vo):
        buf += tok
        if tok in "。？！":
            if clean(buf): parts.append(buf)
            buf = ""
    if clean(buf): parts.append(buf)
    return parts

# ---------- 音频拼接 (与 insert_pauses v2 同源, 已实测接缝零跳变) ----------
def rd(p):
    w = wave.open(p, 'rb'); sr, ch = w.getframerate(), w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch).astype(np.float64)
    w.close(); return a, sr, ch

def wr(p, a, sr, ch):
    w = wave.open(p, 'wb'); w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(np.clip(np.round(a), -32768, 32767).astype(np.int16).tobytes()); w.close()

def room_tone(a, sr, need):
    mono = np.abs(a).mean(axis=1)
    n = int(need * sr); step = int(0.05 * sr)
    if len(mono) <= n: return np.zeros((n, a.shape[1]))
    bi, bv = 0, None
    for i in range(0, len(mono) - n, step):
        v = float(mono[i:i + n].mean())
        if bv is None or v < bv: bv, bi = v, i
    return a[bi:bi + n].copy()

def join_sentences(wavs):
    arrs = [rd(p) for p in wavs]
    sr, ch = arrs[0][1], arrs[0][2]
    tone = room_tone(arrs[0][0], sr, PAUSE)
    nf = int(FADE * sr)
    ramp = 0.5 * (1 - np.cos(np.linspace(0, np.pi, nf)))[:, None]
    t2 = tone.copy(); t2[:nf] *= ramp; t2[-nf:] *= ramp[::-1]
    out = []
    for i, (a, _, _) in enumerate(arrs):
        a = a.copy()
        if i > 0 and len(a) >= nf: a[:nf] *= ramp
        if i < len(arrs) - 1 and len(a) >= nf: a[-nf:] *= ramp[::-1]
        out.append(a)
        if i < len(arrs) - 1: out.append(t2.copy())
    return np.concatenate(out), sr, ch

# ---------- whisper 门 ----------
def whisper_text(wav):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    tmp = tempfile.mkdtemp(prefix="witts_")
    r = subprocess.run([WHISPER, wav, "--language", "Chinese", "--model", "small",
                        "--output_format", "json", "--output_dir", tmp,
                        "--fp16", "False", "--verbose", "False"],
                       capture_output=True, text=True, env=env)
    jp = os.path.join(tmp, os.path.splitext(os.path.basename(wav))[0] + ".json")
    out = json.load(open(jp))["text"] if (r.returncode == 0 and os.path.exists(jp)) else ""
    shutil.rmtree(tmp, ignore_errors=True)
    return out

try:
    from pypinyin import lazy_pinyin
    _fold = lambda s: "".join(lazy_pinyin(s))
except ImportError:                      # 缺包时退回汉字平面 (人名多的稿子会多烧稿, 不致错)
    _fold = lambda s: s

def gates(heard, want_vo):
    """返回 (ok, sim, problems). want_vo=已去斜杠未注拼音的原念白. sim在拼音平面(要点6)."""
    h, w = clean(d2c(heard)), clean(d2c(want_vo))
    sim = difflib.SequenceMatcher(None, _fold(w), _fold(h)).ratio()
    probs = []
    # 幻觉插入: >=4 连续汉字的纯插入
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, w, h).get_opcodes():
        if op == "insert" and (j2 - j1) >= 4 and not re.search(r'[A-Za-z]', h[j1:j2]):
            probs.append(f"insert[{h[j1:j2][:8]}]")
    # 缩写逐字母完整 (顿号拼写的 A、T、P 每个字母都要被听到)
    flat = re.sub(r'[^A-Za-z]', '', heard).upper()
    for m in re.finditer(r'(?:[A-Z]、)+[A-Z]', want_vo):
        letters = m.group(0).replace("、", "")
        if letters not in flat:
            probs.append(f"acronym[{letters}]")
    ok = sim >= 0.80 and not probs
    return ok, sim, probs

# ---------- 主流程 ----------
os.chdir(ITTS_HOME)
from indextts.infer_v2 import IndexTTS2
t0 = time.time()
tts = IndexTTS2(cfg_path="checkpoints/config.yaml", model_dir="checkpoints",
                device="cpu", use_fp16=False, use_deepspeed=False)
print(f"MODEL LOADED {time.time()-t0:.0f}s device=cpu", flush=True)

manifest = []
for sc in SCENES:
    sid = sc["id"]
    fin = os.path.join(AUD, sid + ".wav")
    if TARGETS and sid not in TARGETS:
        if os.path.exists(fin):
            d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
                "format=duration","-of","csv=p=0",fin]).strip())
            manifest.append({"id": sid, "dur": round(d, 3)})
        else:
            print(f"{sid}: MISSING and not targeted!", flush=True)
        continue
    vo = sc["vo"].replace("/", "")
    sents = sentences(vo)
    best = None      # (score_tuple, path, sim, probs)
    for t in range(1, MAX_TRIES + 1):
        tdir = tempfile.mkdtemp(prefix=f"itts_{sid}_")
        parts = []
        for i, s in enumerate(sents):
            p = os.path.join(tdir, f"p{i}.wav")
            tts.infer(spk_audio_prompt=VOICE_REF, text=apply_pinyin(s),
                      output_path=p, verbose=False)
            parts.append(p)
        joined, sr, ch = join_sentences(parts)
        rawp = os.path.join(tdir, "joined.wav")
        wr(rawp, joined, sr, ch)
        cand = os.path.join(AUD, f"{sid}_try{t}.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", rawp,
                        "-af", f"atempo={SPEECH_TEMPO},loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar", "48000", "-ac", "2", cand], check=True)
        shutil.rmtree(tdir, ignore_errors=True)
        heard = whisper_text(cand)
        ok, sim, probs = gates(heard, vo)
        print(f"{sid} try{t}: sim={sim:.3f} probs={probs}", flush=True)
        score = (len(probs), -sim)
        if best is None or score < best[0]:
            if best: os.remove(best[1])
            best = (score, cand, sim, probs)
        else:
            os.remove(cand)
        if ok: break
    os.replace(best[1], fin)
    d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","csv=p=0",fin]).strip())
    manifest.append({"id": sid, "dur": round(d, 3)})
    print(f"{sid}: PICK sim={best[2]:.3f} probs={best[3]} dur={d:.2f} sents={len(sents)}", flush=True)

json.dump(manifest, open(os.path.join(BUILD, "durations.json"), "w"), indent=2)
print("DONE (durations.json updated)", flush=True)
