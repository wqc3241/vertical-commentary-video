---
name: vertical-commentary-video
description: >-
  Build a ready-to-post 9:16 narrated commentary or highlight video for Xiaohongshu, Douyin,
  Reels, TikTok, or Shorts. Use for 竖屏解说视频、高光集锦、网球人物故事, or any topic narrated
  over real footage. Runs the staged pipeline: research and oral Chinese script, script and
  footage approval gates, identity-verified sourcing, IndexTTS-2 narration in the user's voice,
  word-exact captions, low-memory rendering, scene previews, subject/audio/timeline QC, branded
  ending, environment-routed AI dual covers, publish copy, and chapters. Trigger even when the user only gives
  a topic and approximate duration.
---

# Vertical Commentary Video Builder

Produces a ready-to-post **9:16 / 1080×1920** narrated video: real footage centred over a
**dark, heavily-blurred moving fill** of itself, **word-exact** burned-in Chinese captions, headline
"chips," a stats/results card, and a closing poster — timed to a voiceover in **the user's own
cloned voice**.

Playbook + engine. The `scripts/` are proven and reusable; each new video is a new project folder
where you copy the scripts, write one `scenes.py`, fetch footage, and run the pipeline. Read the
`references/` file when you reach the step it covers.

## The mental model

A video is a list of **scenes**. Each scene = one chunk of narration + footage (or a graphic card)
+ an optional chip + auto-timed captions. A scene can also be a **montage** (`clips=[(stem,tin),…]`)
that plays several footage segments in sequence — ideal for a post-win ending (cup-raise → speech →
photo). Everything is data in `build/scenes.py`.

Hard-won quality rules — the user cares about these, don't regress them:
1. **Cuts land on completed points — and a few frames BEFORE the camera cut.** Never end mid-rally.
   `detect_shots.py`+`pick_ends.py` snap each END to a real cut, then back off `EDGE_MARGIN` (~0.17s):
   a detected boundary is the *first frame of the next shot*, so ending exactly on it flashes one frame
   of crowd / reaction / handshake at the cut (the user notices). Hand-set/`_MANUAL` tins must subtract
   the margin too: `tin = boundary - 0.17 - dur`.
2. **Footage is real match play.** Avoid establishing/branding shots (court + event logo), slow-mo
   beauty close-ups, changeovers, and crowd cutaways in round scenes — pick the rally shots.
3. **Identity is correct — verify EVERY clip, including the hook/intro.** Anchor your player's kit
   colour from a *known-champion* shot (trophy lift / match-winning collapse), then match it everywhere.
   **Celebration / fist-pump close-ups are very often the OPPONENT** (a pumped player ≠ your player —
   check the colour). At a trophy ceremony the **runner-up is presented FIRST**. Single most common mistake.
   **Kit colour ALONE is not enough** — it fails at Wimbledon (all white) and whenever both players wear
   the same colour family (Beijing '25: BOTH in red; the user caught the wrong subject TWICE, 2026-07).
   Escalation ladder when colour is ambiguous, in order of reliability:
   a. **Equipment brand** — racquet/bag/kit logos are unambiguous (Nosková=Yonex vs Nike/adidas; a YONEX
      bag behind the bench settled a coin-flip). Zoom the frame until you can read a logo.
   b. **Kit construction + headwear** — one-piece dress vs top+skirt; visor vs headband vs cap; shoes.
   c. **Scorebug server-highlight / stadium screen** — the highlighted row serves; big-screen graphics name
      who's shown.
   d. **Physique** (height/build) and handedness.
   Protocol: build a per-source **identity anchor table** at footage-gate time (player = brand+kit+headwear
   per event); verify every **single-subject close-up at FULL resolution** (320px tiles lie — that's how both
   misses happened); and probe **BOTH ends of every window** — a camera cut mid-window can swap the subject
   (a window that STARTS on your player can END on the opponent). Post-final walking/waving/hugging footage
   is winner-dense: in a lost final that's the opponent. **YOLO-tracked crops need the same check on the
   TRACKED OUTPUT, not just the source** (2026-07): the tracker locked onto a standing spectator behind her
   while she sat crying, and onto the opponent at fixed-camera events where the near end swaps each game —
   extract frames from `build/reframed/*.mp4` and confirm the crop follows YOUR player for the whole window;
   if the subject is occluded/ambiguous, add the window to `FIT_WINDOWS` (full frame centered) instead.
4. **Show the exact moment the line asks for.** A round result / "he won" → that match's **match point**
   (the deciding rally ending on the winning shot), found by scanning the reel's tail; the climactic
   caption must land on the winning frame. A long `shots.json` "shot" can secretly merge rally+celebration+
   graphic — eyeball it. No clean window of your player? Use a `clips=[…]` montage. → `footage-sourcing.md`.
5. **Surface/venue consistency.** Don't drop indoor-hardcourt B-roll into a red-clay story.
6. **NO logo / title / graphic CARDS inside any window — ever.** Trailers and tribute reels splice in
   full-screen brand cards (the Netflix "N" reveal, sponsor logos, a "MAY 29" date card, "LEGEND"/
   "CHAMPION" graphics, the Roland-Garros logo bumper). These are NOT brightness/flash outliers, so the
   luma check will pass them — you must **visually scan every scene's window** (start + mid + EACH montage
   clip's start, on the rendered video) and replace any that land on a card. A small **corner watermark**
   baked into the source (e.g. "NETFLIX" top-right on every doc frame) is fine and unavoidable; only the
   full-screen CARDS are the problem. The user has caught these repeatedly — scan for them every build.
7. **Every clip must be factually true to its line.** The footage has to match what the words actually
   say: the "2022 Australian Open" line uses the *real* 2022 AO match (Nadal–Medvedev), not a look-alike
   hard-court match from another year; a "foot injury / 穆勒-魏斯综合症" line shows medical/X-ray footage,
   not a family shot; "his rivals praised him" shows the rivals, not an unrelated interviewee; "戴维斯杯"
   uses Davis Cup footage. When the user names a source/clip, use THAT one. Wrong-but-pretty ≠ acceptable.
8. **尽量不用重复素材 — but SLICE long sources into distinct moments (user rule 2026-07-16).** Every
   scene gets a DISTINCT, non-overlapping footage window (audit `[tin, tin+dur]` per source — no two
   scenes may share a window; run a programmatic overlap audit before rendering). Re-using the SAME
   moment twice is the violation; one long source containing DIFFERENT scenes (rally / bench / ceremony /
   interview) SHOULD be cut into several windows used in different places — that's how you stretch a thin
   footage pool without repeats. Spread usage across sources; don't over-lean on one reel. The deliverable
   is **full-screen, edge-to-edge** — no inset border/frame drawn by the overlay. → `footage-sourcing.md`.
9. **Static photos: PURE STATIC, ≤3s each, NO effects (user standing rule 2026-07-16 — supersedes the
   old Ken-Burns default).** "一张图出现在那儿就可以" — no zoom, no push, no pan; build stills with
   `ffmpeg -loop 1 -t <seg> -i photo.png` at native size. Photo rules, each one user-enforced:
   a. **≤3 seconds per photo/graphic** — in a montage a photo takes exactly 1 slice; longer beats use a
      VIDEO or a multi-photo montage, never one lingering still.
   b. **特写/already-tight photos are used AS-IS — never re-crop a close-up.** Second-pass cropping of an
      already-framed photo cuts heads/limbs (捧橘子照 beheaded twice).
   c. **If a 9:16 crop can't contain the whole person → show the FULL ORIGINAL image centered** (blur
      letterbox via `FIT_WINDOWS` / a `ph_*_wide` still). Do NOT iterate cx guesses hunting the subject —
      the user's exact words after two failures: "你要是不知道怎么截到整个人,你就放原图".
   d. **Every still must carry readable information — a subject's face/body or concrete numbers.** A
      zoomed fragment with no person and no legible data (the unintelligible zoomed scoreboard: "什么玩意儿")
      is worse than nothing; show the full graphic, or replace it, or extend the PREVIOUS video clip to
      fill the slot (user-preferred fix).
   e. `build_photos.py` Ken-Burns exists but is OFF by default now — only when the user explicitly asks
      for motion; ffmpeg `zoompan` stays banned always (integer-rounding jitter).
10. **The deliverable always carries 轻原声 (light ambient) — final gain 0.15 (user 2026-07-16: 0.30
   压配音,"再调小一半").** Segment previews may run 0.30 for review, but the FINAL assembly =
   `assemble_ambient.py <voice_master> 0.15` unless the user sets another value — the cloned voice must
   stay clearly on top. Voice-only `render.py assemble` is a draft, not the deliverable. Photo/silent
   sources get auto-silence. Speech-bearing windows (victory speech, on-court interview) are a feature —
   let the real voice breathe underneath.
11. **Every deliverable ends with the user's branded ending + ships as 1080p 60fps (standing rule
   2026-07-13).** After assemble_ambient/assemble16, ALWAYS run `finalize_ending.py <deliverable>`:
   appends the personal ending card `$PERSONAL_ASSETS/ending.mov` (点赞收藏关注, native 1080×1920;
   个人品牌件不随仓库分发, 见 docs/ONBOARDING.md 第3步; 缺失时自动跳过片尾仅统一1080p60) — kept vertical for 9:16, center-
   cropped (`crop=1080:608:0:738`) for 16:9 — and re-encodes the whole file to 1080p@60fps. Idempotent
   (skips if the `finalized-with-ending` tag is present). Single-pass filter_complex concat dies on this
   Mac's ffmpeg — the script's 3-step method (transcode both parts to identical specs → concat -c copy)
   is deliberate, don't refactor. If the user hands you a NEW ending clip, replace `$PERSONAL_ASSETS/ending.mov`.
12. **Produced IG reels' music is NOT venue sound — mute it.** Ambient under the narration must be REAL
   现场声 (ball strikes / crowd / broadcast); an edited reel's music bed or added SFX is not ("背景音
   不是视频背景音"). List those stems in `scenes.py` `MUTE_AMBIENT = {"ig_milan_champ", …}` — honored by
   BOTH `preview_parts.py` and `assemble_ambient.py`. Landscape 横屏 with an uncertain/two-player subject:
   fit the full frame centered (blur letterbox), do NOT zoom in guessing.
13. **Cards (战绩卡 etc.) are ≤3s INSERTS woven between match footage, never a parked full scene** (a
   16s static card loses viewers). Use per-scene `CARDS`+`treat="card:<key>"` slices inside a montage.
   Card text must not collide with the scene chip — give inserted cards `title=""` (the chip IS the
   title); if a chip covers a face, drop the chip for that scene.
14. **人物专题实行“目标人物零容忍” (2026-08-04 大坂直美复盘).** 除非念白正在明确讲另一个人,
   每个视频窗、照片和数字人底图都必须是目标人物; 对手的庆祝、走场、近景和观众 cutaway 不能拿来
   “补画面”。在 `scenes.py` 旁维护逐场景主体清单 `Sx → target / intentionally-other / reject`,
   预览也按具体秒段验人。任何一帧身份不确定就换素材, 不把猜测留给用户审片。
15. **用户指定静态图节奏时, 精确时长覆盖通用 ≤3s 规则.** 例如“5 张图每张 1.5 秒”必须写成
   5 个独立 `(stem,tin,dur=1.5)` slice, 成片按帧核对; 若用户说“混剪结束后都换成视频”, 最后一张
   静态图之后严禁再出现任何 still/card。不要把总时长均分后四舍五入成近似值。
16. **念白、字幕、TTS 只有一个 canonical source.** 用户审批后的 `scene.vo` 是唯一真源; TTS 输入、
   断句字幕、预览脚本和发布文案中的引用都从它派生。修一句要同时改源数据并重生对应音频/字幕,
   禁止 TTS 阶段临时润色、同义改写或拿旧音频拼回去。最终逐 scene 对听文字, 必须逐字一致。
17. **片尾是“两句连续交接”, 不能漏 CTA.** 正文最后一句必须是能激发评论的开放式问题; 随后把
   `关注我，了解更多网球故事和知识。` 作为独立尾音轨接入品牌片尾。CTA 可单独加速到刚好覆盖
   ending.mov, 但不能提前塞进上一场、被品牌声盖住或因时长不足直接删除。交付前耳听确认问题句结束
   后 CTA 才开始, 且 CTA 与品牌动画同起同落。
18. **网球文案固定口径:** 标题首字符是 `🎾`; 口语化、像真人讲故事, 少用“不是…而是…”模板对比;
   结尾用开放提问; 当人物经历很多但仍年轻时, 明确说出年龄/“依然很年轻”来托住“未来仍有可能”的落点。
19. **精确反馈只做外科修复.** 用户指出“预览 B 4–7 秒人物错了”时, 只替换该窗口、重渲对应 scene
   和受影响 preview, 再对这段的首/中/尾帧做身份复核; 不无故整片重跑。反馈确认后要主动继续下一门禁,
   每个耗时阶段都明确说明“正在运行的进程/产物/下一检查点”, 不能把尚未启动说成“正式制作中”。
20. **最终交付是完整五件套, 不是只给一个 MP4.** 必须包含: ① 完整成片; ② 小红书标题;
   ③ 小红书发布正文+tags; ④ 竖版 `3:4 1242×1656` 封面; ⑤ 横版 `4:3 1440×1080` 封面。
   视频 ≥1 分钟时另附章节列表。五件套全部落到实际项目目录并检查可打开后才算 deliverable 完成。
21. **动态演示内容默认用 HyperFrames 出竖版动态卡 (2026-08-09 用户拍板, A/B 对比后引入).**
   示意图/数据演示/对比讲解这类"要动起来才讲得清"的画面, 用 HyperFrames (HTML+GSAP→MP4) 生成
   1080×1920 无声 stem 当普通素材嵌入; 账号样式从 `assets/hyperframes-card-template/frame.md`
   继承(色板/字体/组件冻结, 对应封面"四区冻结"的动效版); `npm run check` 全绿 + snapshot 逐字
   校验后才渲染; 站内卡让位字幕带与 chip、时长=念白槽位、无声即正确。完整规矩
   → `references/hyperframes-dynamic-cards.md`。静态 PIL 卡体系(战绩卡 `treat="card:"`)保留不删,
   一屏静态数据仍可走老路。

## Approval gates — NEVER one-shot the whole video (the user requires this, 2026-07)
Build in stages and STOP for sign-off **twice**. Do NOT run TTS / render / assemble until BOTH gates pass —
the user asked for this explicitly ("不要一次性生成所有成片…我同意了再合成视频"). Re-running voice + reframe +
render is the expensive part; the gates exist so the user never pays for a full build of the wrong script or clips.
1. **Script gate.** After harvesting the 解说词 from ChatGPT and mapping it to `scenes.py`, PRESENT the full
   per-scene script (每个 scene 的 vo + 断句字幕, plus 标题/正文/tags) and WAIT for explicit approval / edits.
   The user's own rewrite IS the quality bar — expect edits; do not proceed to footage on your own.
2. **Footage gate.** After you've chosen every scene's clip (window + which player + full-bleed vs blur), PRESENT
   the plan — one line per scene, e.g. `S2 老德对拉(ESPN 704,跟踪)→小黑握拳特写(02_W_TB 352)→…`, backed by the
   contact-sheet frames you actually verified — and WAIT for approval before generating voice + rendering.
Only after the footage gate is approved do you run steps 3→7. (A tiny tweak the user requests mid-build — swap one
clip, fix one line — doesn't need a fresh gate; a new script or a new footage set does.)
3. **Segment-preview checkpoint (the user's standard review flow, 2026-07).** After rendering, do NOT deliver a
   one-shot final: assemble **per-part previews** (`preview_parts.py 0.30` → 预览_A..E.mp4, each = that part's
   scenes + voice + ambient at final quality), send them, and WAIT for segment feedback ("D3 不要卡" / "预览通过").
   Only then concat the full deliverable. Parts target ~1 MINUTE each — part count = ceil(runtime/60s),
   split at scene boundaries (user rule 2026-07-17: a ~2-min video = 2 parts, NOT one part per story
   beat; five ~20s files is over-splitting). The checkpoint stays regardless of length. Fixes after preview are surgical: re-render the named scene(s),
   rebuild only the affected part previews (`preview_parts.py 0.30 BCD`), then final-assemble.

## Workflow (in order)

### -1. 新用户开箱门禁 (仅首次) — 别人复用这条流水线从这里进
本仓库**零个人数据**: 声音参考/数字人模板/品牌片尾都属于使用者本人, 只存在本机
(`personal.env` 指定, 已被 .gitignore 挡在库外)。**第一次使用前必须先录自己的三件套**
(①两段自己的语音: 音色参考+情感参考 ②自己的数字人模板视频 ③可选品牌片尾) —
完整步骤见 `docs/ONBOARDING.md`, 录制规范见 `docs/数字人模板录制指南.md`。
```bash
bash scripts/check_personal_assets.sh   # 全绿才开工; 缺项会指到 ONBOARDING 对应步骤
```
⚠ 助手执行铁律: 发现个人资产缺失时, **先带用户完成录制, 再开始做片**; 任何情况下
不得把 *.wav / *.mov / 模板视频提交进 git (.gitignore 已设防, 不要绕过)。

### 0. Setup
```bash
PROJ="/Volumes/Storage/Documents/<name>"
mkdir -p "$PROJ/source" "$PROJ/build"
cp ~/.claude/skills/vertical-commentary-video/scripts/*.py ~/.claude/skills/vertical-commentary-video/scripts/*.sh "$PROJ/build/"
```

### 1. Lock the script (TEXT FIRST — get sign-off before building visuals)
- **FACT-CHECK GATE — applies to every topic, not only breaking news.** Before writing, make a compact
  fact sheet covering every checkable claim that may enter the narration or screen: dates, age, scores,
  opponents, titles, records, quotes, rules, brands and event/venue. Prefer an official/primary source;
  use a second independent source for consequential or disputed claims. Recent/ongoing events must be
  verified live and post-cutoff facts are unknown until checked. Put only verified facts into the GPT
  prompt; remove or explicitly flag anything unverified, and preserve the source URLs/notes in the project.
  Names and numbers appear on screen, so approximate memory is not acceptable.
  **省 token 三则 (2026-08-02 实测标定, 前期约占全会话 10–15%):**
  ① **WebFetch 黑名单**: `atptour.com` / `scmp.com` / `rappler.com` 一律 403 — 别撞, 用 WebSearch
  综述或维基; ② **系列/成对选题合并核查**(两人一轮查完, 实测省近半); ③ 中英文各查一遍是**必要**的
  (中文维基与英文维基冲突正是这么发现的), 但同一事实别换关键词反复搜。
- **MANDATORY — generate the 解说词 in the USER'S OWN ChatGPT via their browser; never just write
  it yourself.** The user has had to correct this repeatedly — skipping it is the #1 process
  mistake on this skill. Follow `~/.claude/skills/xhs-personal-vlog/references/copy-generation.md`:
  Claude-in-Chrome → **直接导航到用户自己的文案项目主页
  `$GPT_PROJECT_URL`**(在 personal.env 配置一次, 形如 https://chatgpt.com/g/g-p-<你的项目ID>/project;
  ID 固定, 别再"开首页→截图→翻侧栏→查 DOM 拿 href" — 那套多花两张截图和三四次调用) → send ONE single-line
  prompt (newlines auto-send!) that includes the topic, the VERIFIED facts, spoken length, ≤20-char
  sentences, numbered scenes, and asks for 标题/正文/tags too — **and REQUIRE a fact-check first**:
  prompt 里明确写「先逐条核对我给出的事实清单再写稿;只使用清单内的事实,任何清单外或不确定的
  说法要标注出来,不要写进正文」(2026-07-22 rule; GPT 曾把「仅入学前奖金放开」写成「取消奖金限制」
  被用户抓出 — 政策/规则类表述必须精确到适用范围) → wait 30–60s(轮询用
  `document.querySelector('button[data-testid="stop-button"]')` 判 streaming, 别截图) →
  **harvest 只取最后一条 assistant 消息**: `[...document.querySelectorAll(
  '[data-message-author-role="assistant"]')].pop().innerText` — `get_page_text` 会把你自己 1900 字的
  提示词整个回读一遍(付两遍 token, 实测约占收稿量一半)。Canvas mode often stalls mid-stream: ask for
  纯文本对话回复 not canvas, and reload the page to see server-side truth before assuming failure.
  Save the publish copy to `<project>/小红书发布文案.md`.
- **Copy-style rules the user requires — put these IN the ChatGPT prompt AND enforce when you map to captions
  (2026-07 feedback):**
  1. **数字一律用阿拉伯数字**(比分 3-6、时间 5小时15分、纪录 第15次、25冠),**不要中文数字**。
     ⚠️ 用户口中的「罗马数字」= 阿拉伯数字(西文数字 0-9),不是真的 Roman numerals — 别写成 XII。
     (念白 `vo` 仍要中文数字给 F5-TTS,见下条;GPT 出稿用阿拉伯数字,你在 CAPTIONS 里保留数字、在 `vo` 里转中文。)
  2. **语句通顺自然、口语化,不要浮夸 / 过度夸张的说法。**
  3. **少用「不是…而是…」这类转折句式**(以及其它生硬的对比转折)。
  4. **英文大写缩写**:字幕/文案保留原文 (NCAA/TCU/ATP),念白 `vo` 写成顿号逐字母 `N、C、A、A`(见 step 3)。
  5. **人名用该账号惯用的中文译名;用户点名的昵称优先**(例:Learner Tien = 钱学生, 2026-07-22)。
  6. **开头 2–3 句必须形成 hook:** 尽快给出人物、反差/悬念或本期最值得看的问题, 让用户知道为什么
     要继续看; 只能使用已核实事实, 禁止“震惊、封神、所有人都没想到”式夸张和无依据吊胃口。
  7. **最后一句必须是开放式提问:** 问法要与故事落点直接相关、没有标准答案, 让用户愿意留言或分享
     自己的看法; 不能用“你觉得呢”这种空泛占位, 也不能在问题后再补新的正文结论。
- Treat the output as a DRAFT. **→ SCRIPT GATE: present the full script (per-scene vo + 断句 + 标题/正文/tags,
  with any factual/style fixes you made) and WAIT for the user's approval before touching footage.** Only if the
  browser/ChatGPT is genuinely unavailable may you draft the script yourself — and say so explicitly when presenting.
- **After** the script is approved, map it to `build/scenes.py` from `scenes_template.py`. Per scene: `vo`
  (spoken, **Chinese numerals** 六比三 so TTS doesn't read English digits — convert the GPT digits here) +
  a `CAPTIONS[id]` list of the **display lines** (the user's own 断句, **阿拉伯 digits** 6-3). Each caption
  line must equal the spoken words (only numerals / the 比↔- score separator differ) or caption timing drifts;
  keep every caption line **≤13 chars** so it never overflows (render.py wraps at 820px as a backstop). Fill
  `RESULTS_CARD`/`POSTER`. Then move to footage — the **next** stop is the Footage gate, not the render.
- **脚本通过后才设计画面和搜索素材.** 逐 scene 根据已批准念白写清“这句话需要看到什么”以及搜索词,
  再搜索相符的视频/图片; 优先级为原生竖版视频 → 竖版真实图片 → 横版视频跟踪裁切 → 横版完整画面
  blur-letterbox。不能先囤一批漂亮镜头再反过来改文案迁就素材; 每个画面必须服务对应念白。

### 2. Source footage — VERTICAL-FIRST → `references/vertical-footage-and-instagram.md`
**DEFAULT: use真·竖屏 footage wherever possible — the user has emphasised this repeatedly; the
dark-blur letterbox is the FALLBACK, not the look.** Per scene, in order of preference:
1. **Native-vertical Instagram / TikTok reel** — search the user's logged-in IG in their browser
   (Claude-in-Chrome): keyword search (`<player> match point / forehand / celebration / edits`),
   plus official accounts' Reels tabs (@rolandgarros, @wimbledon, @atptour, the players). Pull
   `/reel/` permalinks from the DOM, download `yt-dlp --cookies-from-browser chrome`, wire in via
   `build_ig.py` (→ `build/reframed/` keys). Most reels are 720×1280 — upscale lanczos; tell the
   user which scenes are IG-720p vs 1080 so they can choose.
2. **Full-bleed tracked crop** of a landscape reel (`reframe_scenes.py`, video-autoreframe skill) —
   for beats that only exist in broadcast footage (e.g. THE match point of a specific round):
   download the official YouTube reel per `references/footage-sourcing.md`, then crop-track it.
   **Montage slices from one continuous take → `reframe_span.py`**: mark them `("stem",t),("stem","+"),…`
   and it runs ONE YOLO pass over the whole span then splits into per-slice keys — per-slice tracking
   re-centers at every cut and visibly jumps. Verify the tracked output per quality-rule 3.
3. **Classic blur-letterbox landscape** ONLY where neither works (ambiguous 2-player wide rally the
   tracker can't follow, subject occluded by crowd, or the user prefers the broadcast frame) — declare
   the window in `FIT_WINDOWS` so reframe skips it (**implemented for real since 2026-08-02**: v2
   reframe_scenes 读表跳过并撤下误裁的旧文件; 之前只有文档没有实现, 标了 7 个窗口全被白裁一轮),
   and say which scenes fell back and why when presenting. This is also the mandated treatment for
   uncertain-subject 横屏 (rule 12) and can't-crop-the-whole-person photos (rule 9c): full frame/image
   centered, never a zoom guess.
Mix per scene; `lock: True` every full-bleed/IG scene. Verify each clip's resolution and **eyeball
frames** (`contact_sheet.py`) — content, surface, and which player is which. Match every scene's
clip to its `vo` (round result → that match's **match point**, scanned from the reel's tail) and
**confirm the player by kit colour** anchored to a known-champion shot — `footage-sourcing.md`
covers match-point/identity/montage selection in detail; identity checks apply to IG clips too
(search returns look-alikes and fan edits with baked-in text cards — reject those).
**Token economy — 身份复核建表一次, 不重复读图 (2026-08-02, 黄泽林项目 113 张检查图约半数是重复
确认同一批源):** 每个源只做一次全分辨率身份确认, 结论写进 scenes.py 头部的 IDENTITY ANCHORS 注释
(我方=品牌+球衣+头饰, 对手=…, 陷阱时间点=卡片/画中画/对手庆祝), 之后同源的每个新窗口**对表**,
只有单人特写/表上没有的存疑帧才再开图。全分辨率那一次不能省 — 两次差点用错人(吴易昺的握拳、
莱赫奇卡的背影)都是缩略图看不出、原始分辨率才认出来的。
**2b. 动态演示卡 (HyperFrames) — 规则 21 的生产步骤.** 念白在"演示/对比/讲原理"而没有对应真实
画面的 scene, 不硬凑素材也不停在静态图: 按 `references/hyperframes-dynamic-cards.md` 用
HyperFrames 出动态卡 stem (`source/hf_*.mp4`, 原生竖版自动满屏, `lock: True`, reframe 自动跳过,
assemble 自动补静音)。模板+账号 frame.md 在 `assets/hyperframes-card-template/`; `check` 全绿 +
snapshot 逐字校验后渲染 (60fps `-w 2`, 与其它重任务串行)。动态卡也进 footage-gate 清单, 标注
"HF动态卡: <演示什么>" 并附 snapshot 帧。
**→ FOOTAGE GATE: present the per-scene clip plan (with the contact-sheet frames you verified) and WAIT for
approval before step 3.** Montage note: clips are sliced **equally** (`D/n`), so a caption beat can spill onto the
next clip — order clips so the important line (the punchline / the named player) lands on the RIGHT clip, and say
so if a minor spill remains.

### 3. Voiceover → `references/voice-and-audio.md`
**Default engine = IndexTTS-2 情感整段模式 (2026-08-04 起, 伊埃拉情感 bake-off 用户拍板):**
2026-08-02 黄泽林 bake-off 定引擎(更清晰/字母单稿全对/35min vs F5 111min), 2026-08-04 情感升级 —
用户反馈"清晰但缺情感、F5 更贴本人", 根因=只喂音色参考、`emo_audio_prompt` 情感槽位空置吃了
内置中性向量。现默认: **整段场景文本一次合成 + 用户自己的富情感录音当情感参考 + α1.0 + 原生语速**,
模型自己安排句间呼吸(0.2-0.46s 自然变化), 零拼接零裁剪(逐句拼接的句界刀口在情感模式下修不干净,
半截音三轮实证)。安装家 `/Volumes/Storage/indextts2/`(repo+checkpoints+venv, ~12G;
重装: git clone index-tts/index-tts → uv sync → hf download IndexTeam/IndexTTS-2 --local-dir checkpoints)。
```bash
# 单进程即可(CPU RSS≈2G); nohup&disown 脱离会话; 16G Mac 一律 CPU(见下)
caffeinate -i nice -n 15 /Volumes/Storage/indextts2/.venv/bin/python \
   "$PROJ/build/regen_tts_itts.py"           # -> audio/<id>.wav + durations.json (与F5同接口)
# 旋钮(env): EMO_REF=情感参考wav  EMO_ALPHA=1.0  EMO_MODE=0(退回逐句拼接后备)  SPEECH_TEMPO=1.0
```
引擎内建(每条都是实战换来的, 别关):
**数字。数字 邻接自动改写为 数字，数字**(258 七个月悬案 2026-08-04 定案: TextNormalizer 把中文
句号规整成英文句点, "二百五十.八强"被当**小数点**连读成 258, 整段模式 ~50% 概率复发;
逗号规整成"," 不并数, 6/6 全过 — prep_vo() 只动这类危险邻接, 其余句号原样, 字幕不受影响) ·
**digitmerge 专项门**(对每个危险邻接, 听写里查"左尾2字+右首字"连体如"五十八" — 命中即废稿重掷) ·
**拼音硬纠正**(难字在 scenes.py 加 `PINYIN={"昺":"BING3"}`, 行内大写拼音+声调数字, 合法音节见
checkpoints/pinyin.vocab; 前后鼻音如 林LIN2 标了也可能仍偏 — 标注后交用户终审, 别空耗稿数) ·
**whisper 门**(拼音平面相似度≥0.80 + 幻觉插入 + 缩写逐字母)。
**16G Mac 内存规矩: 一律 device=cpu** — MPS 有泄漏, 每进程只能出 1 段就顶到水位(0.5/0.7 都试过);
CPU 整段~35-60s/场 RSS≈2G。**默认低影响串行:** `nice -n 15`, 一次只跑 1 个重任务; TTS、reframe、
数字人、ffmpeg 总渲染、视觉 QC 不得并行; 小批次出完主动释放模型/进程后再进下一阶段。开跑前用
`vm_stat`/`ps` 看水位, 运行中抽查 RSS; 内存压力升高就暂停下一批, 不靠 swap 硬顶。首次失控裸跑
曾把系统挤崩 — 任何新引擎上线前先小样测 RSS 并定上限, 不能影响用户正常使用电脑。
**情感参考升级路径**: 现用跑步 vlog 参考(音高起伏0.41 最活); 用户补录 20-30s"给朋友讲球"状态
的自然语音后换 EMO_REF, 天花板更高。高潮/温情场可 per-scene 换不同情感参考(scenes.py 加字段, 未接线)。

**F5 后备通道**(用户点名要旧音色/对比时): the ANTI-LEAK wrapper (never bare `clone.py scenes` — the
default reference clip deterministically leaks its tail phrase "尤其是他的叔叔托尼" into clip starts,
and the padded variant does NOT fix it; 7 recurrences as of 2026-07):
```bash
VOICE_SPEED=0.85 /Volumes/Storage/voice-clone/venv/bin/python \
   "$PROJ/build/regen_tts.py"     # tennis_backup ref + per-clip whisper verify + retry<=4 -> audio/<id>.wav + durations.json
python "$PROJ/build/check_tts.py" # standalone report; homophones/traditional-script/number-normalization are FALSE alarms — eyeball diffs
```
**断句/语气 audit — MANDATORY before captions (this made the 2026-07 build "完成度非常高"; the user
had previously flagged 断句奇怪 like "深圳|女孩"):** F5-TTS sometimes inserts a prosody break MID-phrase.
Whisper word-gap timestamps CANNOT detect these — audit acoustically:
```bash
/Volumes/Storage/voice-clone/venv/bin/python "$PROJ/build/fix_pauses.py"        # audit + auto-regen flagged scenes
/Volumes/Storage/voice-clone/venv/bin/python "$PROJ/build/regen_fix.py" S3,S7   # targeted re-takes if any remain
```
Method (in `fix_pauses.py`/`fix_pauses_lib.py`): ffmpeg `silencedetect` (-34dB / 0.24s, tightened
2026-07-21) finds real pauses → whisper word positions + difflib `SequenceMatcher` map each pause onto
the caption-line 断句 boundaries (survives digit/homophone drift; exact ±0 boundary match — a ±1
tolerance masked a real "李慧|说" break once). A pause AT a line boundary is correct prosody; a pause
INSIDE a line is a break → regenerate that scene and re-pick takes until ZERO intra-line pauses
(gaps whose context contains a latin letter are exempt — 顿号-spelled acronym letters pause legitimately).

**SECOND direction — 句末"该停没停" (added 2026-07-30, 选拍指南系列; user caught it by ear, the whole
existing audit missed it):** `fix_pauses.py` only finds pauses in the WRONG place. F5-TTS ALSO **swallows
the pause at a 。？！ boundary**, running two sentences together ("平衡多选择头轻。挥重按…" → 0.0s gap,
user: 「"轻，挥"在台词里连上了」). Audit + fix:
```bash
/Volumes/Storage/voice-clone/venv/bin/python "$PROJ/build/check_boundaries.py"   # 全场景; -> boundary_audit.json
/Volumes/Storage/voice-clone/venv/bin/python "$PROJ/build/insert_pauses.py" S1,S4  # 修被标记的场景
```
Three findings that cost a full debug cycle — don't repeat them:
1. **Do NOT measure gaps from whisper word timestamps.** Chinese word timestamps are contiguous
   (`end[i]==start[i+1]`), so the gap is ~0 by construction → 46/54 scenes falsely flagged. `check_boundaries.py`
   uses ffmpeg `silencedetect` and maps each caption-line boundary to a TIME, then asks "is there a silence
   within ±0.28s of it".
2. **Only 。？！ boundaries need a pause.** A caption line split at a ，(or at no punctuation at all) is a
   DISPLAY break, not a breath — requiring silence there flags ~80% of all boundaries. Classify each boundary
   by looking up the punctuation in `vo` (map cap-space→vo-space with difflib + a ±3-char window; a naive
   char-count map breaks because captions use 阿拉伯 digits and vo uses 中文数字: "97"=2 chars vs "九十七"=3).
   Real defect rate on a clean 7-episode build: **24 defects / 54 scenes**, i.e. it happens constantly.
3. **Regenerating the scene does NOT fix it — insert the pause surgically instead.** Each F5 take randomly
   swallows a DIFFERENT 句号 (measured: original take 1 bad boundary, 3 fresh takes 3-4 bad each; the
   original was the best take). `insert_pauses.py` (v2, rewritten 2026-08-02) splices 0.22s into the
   EXISTING wav — the rest of the take is untouched, so 音色/语气/其他停顿 are preserved.
   **v1 曾把静音硬切进字中间 — 用户听出「强」字被劈开、整批撤销返工 (~1h)。v2 的三条硬规则:**
   ① 切点必须落在 whisper 边界 ±0.25s 内的 **20ms-RMS 最低谷**; 低谷仍 >0.02 满幅 = 字没说完 →
   **SKIP 该边界(宁可连读也不切字)** — 输出里的 `SKIP … 字未说完` 是特性不是失败;
   ② 插入的是**本段自身最安静 0.22s 的克隆(室内底噪)**, 不是数字零 — 纯零在有底噪的语音里是可听见的"洞";
   ③ 两端 10ms raised-cosine 淡入淡出 — 接缝采样跳变 >0.01 满幅就能听见"咔哒"。
   修完自动用 boundary_report 复核 + durations.json 同步; whisper-based re-check can false-alarm on
   繁体 transcription (原则→原則 shifts the word mapping).
After fixing, durations change (+0.22s per accepted insert) → re-run `caption_times.py`, re-render those
scenes, rebuild previews.
**vo 写法 (2026-07-21/22 定稿):** clauses ≤20 chars separated by ,。 — **NEVER put "/" in `vo`**:
F5 vocalizes each slash as an audible junk syllable (one scene grew 14 extras; regen_tts strips "/"
defensively but don't write them). **ALL-CAPS acronyms = 顿号逐字母** in vo (NCAA→`N、C、A、A`,
TCU→`T、C、U`; user ear-tested — hanzi phonetics and glued NCAA both rejected), CAPTIONS keep latin
NCAA; regen_tts's acronym gate verifies every letter is heard. 读音有争议时:`clone.py say` 生成 3-4 个
候选读法试听 wav 放项目根目录让用户点选 — 你没有耳朵,不要盲猜。用户报"生硬/音调不对"= 韵律问题:
把 regen 提前收稿阈值 sim 0.88→0.95 强制满 5 稿择优。If scenes are regenerated AFTER previews,
rebuild `audio_master.wav` before final assembly (stale-master bug, 2026-07). 16G Mac 上 F5 连续跑会
死机重启:必须加 `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7`(故意让 MPS 初始化失败回落 CPU — 慢但整机稳,
不要"修复") + `caffeinate -i nice -n 10`,驱动脚本 `nohup … & disown` **分组独立进程 — 每进程 4 段**
(`for g in "S1,S2,S3,S4" "S5,S6,S7,S8" …; do python regen_tts.py "$g"; done`; regen_tts 本就接受逗号列表
且 keep-existing 可断点续跑)。**不要逐段一进程**: 模型每次加载 ~1.5min, 24 段 = 24 次加载 ≈35min 纯浪费
(黄泽林项目实测 111min 总时长里 1/3 是重载, 4段/组 = 6 次加载, 音质零差别; 崩了最多损失 1 组)。
完成标志文件监控(启动前先 rm 旧标志防误报);TCC 中途撤销卷授权时改走 Desktop Commander。详见 voice-and-audio.md。
Or the user records one take → `align.py` (see reference).

### 4. Word-exact captions  → `references/voice-and-audio.md`
```bash
python "$PROJ/build/caption_times.py"     # whisper each scene's audio -> build/captions.json
```
Aligns each caption line to the actual spoken words (fixes "captions out of sync / bunched up").
It auto-re-transcribes when you re-record (staleness check). If you skip this, render falls back to
proportional timing.

### 5. Snap cuts to completed points (a few frames BEFORE the cut)
```bash
python "$PROJ/build/detect_shots.py"      # -> shots.json
python "$PROJ/build/pick_ends.py"         # -> proposed_tins.json + verify_ends.png  (auto EDGE_MARGIN ~0.17s)
```
**Look at `verify_ends.png`** (now shows each scene's TRUE last frame) — every ending is a rally, never
the opponent / a replay / a logo / a 1-frame crowd-reaction flash. Fix via `END_OVERRIDES`/`AVOID_ENDS`/
`lock`+manual tins; re-run. For a **match-point** ending or a user-given window, hand-set the tin with
the margin baked in: `tin = boundary - 0.17 - dur`, locked via `_MANUAL`. `shots.json` can merge a
rally+celebration+graphic into one long "shot" — eyeball the window, never trust its duration alone.

### 6. Render → SEGMENT PREVIEWS → final assemble  (only after BOTH gates are approved)
```bash
python "$PROJ/build/render.py" all        # overlay + cards + per-scene 9:16 (montage-aware)
# 6a. SELF-QC the rendered scenes (see step 7 checks) BEFORE showing the user anything.
# 6b. SEGMENT PREVIEWS — the user's standard flow: per-part files at final quality, then WAIT for feedback:
python "$PROJ/build/preview_parts.py" 0.30           # -> 预览_A..E.mp4 (part scenes + voice + ambient@0.30)
# ... user reviews; fix named scenes; rebuild affected parts: preview_parts.py 0.30 BCD
# 6c. FINAL — always WITH ambient (rule 10, final gain 0.15). TTS voice: concat build/audio/<id>.wav
#     in scene order first (REBUILD it if any scene was regenerated after previews — stale-master bug):
python build/assemble_ambient.py build/audio_master.wav 0.15    # TTS voice master + ambient -> $PROJ/<OUTPUT_NAME>
# recorded take instead: python build/assemble_ambient.py build/voice/full48k.wav 0.15
# (voice-only render.py assemble / assemble-voice = drafts only, not the deliverable)
# 6d. ALWAYS finish with the branded ending + 1080p60 re-encode (rule 11):
python build/finalize_ending.py "$PROJ/<OUTPUT_NAME>"
# 6e. 右下角口播数字人 (user standing rule 2026-08-03, 伊埃拉起默认加) — wav2lip-onnx-256:
caffeinate -i nice -n 15 bash build/avatar_corner.sh "$PROJ/<OUTPUT_NAME>" build/audio_master.wav 0
```
**数字人 (6e)**: 用户真人模板 + 克隆声口播 → 对嘴 → **186px** 圆头像叠右下角 (834,1634 —
2026-08-03 用户按手机屏幕圆角/进度条校准, **勿改回旧的 280px/(772,1616)**; 不压字幕带)。
脚本自含全部路径/参数注释 — 引擎在 /Volumes/Storage/wav2lip-onnx-256,
模板+遮罩在 /Volumes/Storage/avatar-template/assets (模板 126.5s, 音频更长时引擎自动循环帧,
**不要自己做倒放回文** — ffmpeg reverse 整段进内存会崩 16G 机器)。耗时 ~8-9min/分钟口播 (CPU),
必须 caffeinate 包着跑防睡眠断工。数字人只覆盖口播段 0..V, 结尾卡保持无头像。头像盖在战绩卡上
是正常效果, 预览时照常检查。
**⚠ 音轨空洞自检 (2026-08-04 选拍指南 7 集全部中招后立的规矩)**: avatar_corner 的音轨是从成片
`-c:a copy` 继承的, 而最终合装链路可能产出"稀疏时间戳"音轨 (音频包在场景边界附近整段缺失,
每集缺 3-18s, 听感=中间突然没声; 分段预览是好的所以审片听不出)。**交付前必查**:
`ffprobe -v error -select_streams a:0 -show_entries packet=dts_time -of csv=p=0 <成片> | \
  python3 -c "import sys; ts=[float(x.strip().rstrip(',')) for x in sys.stdin if x.strip()]; \
  g=[1 for i in range(len(ts)-1) if ts[i+1]-ts[i]>0.05]; print('holes:',len(g),'span:',round(ts[-1]-ts[0],1),'content:',round(len(ts)*1024/48000,1))"`
holes>0 或 span≠content → 用 build/audio_master.wav + build/ambient_master.wav 按 assemble_ambient
配方 (loudnorm 人声 + volume 0.15 + afade + amix normalize=0) 重混整轨, 尾段用 $PERSONAL_ASSETS/ending.mov
原声, 再 remux 换轨 (video -c copy)。注意 csv 尾逗号和 AAC 首包负 dts (priming) 是正常现象。
**16:9 landscape variant** (the user often wants this too): `render16.py` reuses the SAME `scenes.py`,
`durations.json` and `captions.json` and renders 1920×1080 (footage fills the frame, cards re-laid-out);
`assemble16.py` muxes the same voice + ambient. So one project yields both 9:16 and 16:9 — run
`finalize_ending.py` on that output too (it auto-detects 16:9 and crops the ending to landscape).

### 7. Verify + deliver — LOOK at every scene, not just a 14-frame sweep
`contact_sheet.py video <out.mp4> 14` → Read it. Confirm chips, captions in sync, card **scores +
names**, the win/trophy is YOUR player, the poster. For recorded takes, sync-spot-check (reference).
**Then run the FIVE checks the user keeps catching (see `footage-sourcing.md`):**
0. **先读 `build/subject_report.json`(reframe v2 自动产出, 零成本)** — YOLO 检测顺手统计每个跟踪
   窗口的有人帧占比 + 主体高占比; `⚠ 主体存疑` 的窗口(没人/远景/整屏卡片/画中画都会命中 —
   阈值 85%/0.13 用黄泽林项目用户实抓的 3 处缺陷标定)**必须人工开图确认**, 其余窗口检查 1 和 4
   的看图量可以大幅收窄到"每场景抽 1 帧"级别。这不取代人眼, 是给人眼排优先级。
1. **Logo/card scan** — tile a frame from every scene's start + mid + each montage clip start, Read it,
   and replace any window that lands on a Netflix/sponsor/title/date CARD (luma checks miss these).
2. **Flash-free** — luma-profile each source (`signalstats`) and confirm no window has a near-black or
   spike frame (`pick_clean.py`); fix the reported ones AND the ones they didn't spot.
3. **Distinct + factual** — no two scenes share a window; every clip is literally true to its line.
4. **Identity re-check on the RENDERED output** — for every single-subject window (close-up, bench,
   walk, celebration): full-res frames at BOTH ends of the window; confirm subject via the rule-3
   escalation ladder (brand logo > kit construction > scorebug), not colour alone. A window can start
   on your player and end on the opponent after an in-window camera cut — probe the last second.
5b. **数字人版三帧抽查** (有 6e 时) — 中段一帧 (圆圈在+嘴型自然)、口播结束前 1s 一帧 (圆圈仍在)、
   结尾卡一帧 (圆圈已消失); 数字人版时长必须 = 原成片时长 (±1帧)。加上上面的音轨空洞自检一起跑。
5. **Re-scan after EVERY duration change** — re-recording even ONE scene's voice changes all montage
   slice lengths and shifts every window: after any re-assembly, re-extract frames and repeat checks
   1+4 on the shifted windows. A full-screen "COACH" title card drifted into frame TWICE this way
   (2026-07-22) — the previous QC pass does not protect the new cut.
6. **Subject manifest audit** — 把最终 timeline 每个 scene/montage slice 与主体清单逐项勾销; 对每个
   窗口抽首/中/尾三帧, 尤其复查用户曾点名的秒段。对手或身份不明帧 = fail, 不能因其余画面正确放行。
7. **Voice/text/end audit** — 逐 scene 对照 canonical `vo` 听写, 字幕同步同源; 检查全片无音轨空洞;
   最后开放问题句完整, `关注我，了解更多网球故事和知识。` 清楚可闻且加速同步品牌片尾。
8. **Still/video boundary audit** — 对所有照片核对精确时长; 若项目约定静态混剪后只用视频, 抽取
   boundary 前后帧并确认此后零静态图。三项门禁(人物、声音文字、时间线/片尾)全绿才算可发布成片。
Deliver the MP4. Re-render only changed scenes (`render.py scene <ID>` / `render16.py scene <ID>`).

**最终五件套核验:** 完整成片 + 小红书标题 + 发布正文/tags + 竖版3:4封面 + 横版4:3封面。
逐项给出项目内绝对路径; 视频用 `ffprobe` 验证可播放, 双封面读回尺寸, 标题/正文检查完整且与成片一致。

**内容章节 — the 4th standard deliverable (user standard 2026-07-16), alongside 成片/封面图/发布文案:**
a chapter list with timestamps + themes, appended to `小红书发布文案.md`.
- **This list feeds the PLATFORM chapter features at publish time — it must NOT be pasted into the
  XHS note body** (user rule 2026-07-23): XHS = 内容设置→添加章节, set during the FIRST publish
  (locked afterwards — unlocking requires re-uploading the video); douyin = 章节功能 (智能章节 or
  manual). See the `publish-xhs-douyin` skill.
- **Chapter count ≤ the video's length in minutes** (6-min video → ≤6 chapters, 5-min → ≤5; round the
  runtime UP). With more scenes than that, MERGE adjacent scenes into one chapter per story beat
  (起步→夺冠→爆发…), don't emit one chapter per scene.
- Timestamps = cumulative scene durations from `build/durations.json` (scene renders equal their audio
  length; the branded ending only adds tail time). Format `mm:ss`, floor to the second.
- **Frame-verify 3-4 boundaries before delivering**: extract a frame just after each claimed timestamp
  and confirm the scene chip/content matches the chapter title — never ship unchecked arithmetic.
- Titles follow the copy-style rules (Arabic digits, natural phrasing, no hype).

### 8. 双平台封面图 — deliver WITH the 发布文案, every video (updated 2026-08-04)
**先按当前运行环境选生成入口, 这是硬分流规则:**
- **由 Codex 制作** → 使用 Codex 内置 Image 2 / `image_gen`; 不为了生成图片另外打开 Web ChatGPT。
- **由 Claude 制作** → 使用用户自己的 Web 版 GPT 项目生成; 保留原来的浏览器上传 reference +
  网页取回流程, 不改用 Claude 本体画图。
- 这条分流适用于封面、示意图和流程中所有需要 AI 生成的视觉素材; 用户在**当前项目明确指定另一种
  入口**时才覆盖。真实比赛视频和真实照片仍按素材来源规则搜集, 不用 AI 冒充。

网球人物故事必须把用户提供或已验证身份的真实照片作为 reference image; 目标是保留同一个人的真实
身份特征并完成固定排版, 不是凭空画一个相似人物。Local `make_cover.py` 不是默认替代方案, 只有当前
环境对应的 Image 2/Web GPT 多轮文字失败且用户明确同意时才用。

**一次独立生成两版, 禁止互裁:** 竖版 `3:4 1242×1656` + 横版 `4:3 1440×1080`; 横版必须重新构图,
不能从竖版裁出来。竖版标题/副标题全部位于**画面上半部分**, 下半部分留给人物和完整服装; 横版文字
放左侧、人物放右侧, 同样保证人脸、手和服装不被字压住。两版存入 `<project>/final/covers/`, 并复制
`封面图-竖3x4.jpg`、`封面图-横4x3.jpg` 到**实际项目根目录**供 macOS 文件选择器直接上传; 不得只留在
Codex 临时输出目录。保存后用 `identify`/`sips` 读回尺寸并逐字检查标题。

One consistent cover style across the account. The account typography is FROZEN — four text zones,
only the 【】 slots vary per video:
> 大标题「【主标,≤6字,压缩自小红书标题】」厚重宋体衬线白字深色描边 · 其下金色副标题「【副标,≤10字】」·
> 左上角红棕圆角胶囊白字「网球故事」(不压标题) · 底部居中白字「【主人公人名】」两侧金色小圆点 ·
> 竖版3比4 · 所有汉字逐字准确 · 除四处文字外无任何其他文字/水印/logo

**封面选型 — 按内容类型选,不要一律套人物模板 (user rule 2026-07-22):**
- **人物专题**(单一主角的故事)→ 上面的四区冻结模板原样用(胶囊+主标+副标+人名)。
- **话题片/群像/盘点**(如「NCAA 的魔力」这类多人主题)→ **多位主角头像特写拼版**(2-4 人竖条并排,
  人脸取自已验证身份的素材帧或官方照片),**只保留主标+副标 — 不要「网球故事」胶囊、不要人名**,
  字体可以换(现代粗黑体等)。拼版自己合成好再注入 GPT(留出标题头部空间、避开路人/新闻条;
  `ffmpeg -map_metadata -1` 剥掉 XMP 再 b64 分块注入)。
- GPT 项目会惯性沿用老模板:prompt 必须显式写「这期不要胶囊、不要人名」;若它仍套错,不要重新生成,
  用「基于你上一张生成的封面图修改:…」来纠正(重出图会连底图一起换掉)。

**系列/示意图类封面 — 仍按运行环境分流生成 (2026-08-04):**
封面主体是图表/示意图(非真人照片)时, **不要走 MODE A 的底图注入** —— 把版式和每张的图形内容用文字描述清楚,
Codex 用内置 Image 2 / `image_gen`; Claude 在 Web GPT 中用一条 prompt 生成整套风格统一的封面。
底图注入(压缩→b64→分片)每张要 10+ 次
调用且分片会被静默截断, 只在必须保留真人实拍时才值得。
**成图取回本地 — 用 `cover_bridge.py`, 三个条件缺一不可 (2026-07-30 实测定论):**
① 页面内 `fetch(img.src)`→FileReader→dataURL (图片是同源要 cookie 的 backend-api URL, 服务端 curl 拿不到);
② `<form>` **顶层提交, 不带 target** —— `target=_blank` 被弹窗拦、`target=<iframe>` 被 CSP frame 限制挡,
   两者都**静默失败**(submit 不报错但文件不落盘), 只有顶层提交能过 `form-action`;
③ 桥**返回 204 No Content** —— 返回 200+body 会让页面跳转到 127.0.0.1, ChatGPT 页面和 JS 状态全丢;
   返回 204 浏览器停在原页面, 于是能在一个 JS 调用里 for 循环把 7 张全下完。
(`a.download` 在 in-app 浏览器被沙箱吃掉; `file_upload` 白名单拒绝项目文件; 取 accessToken 本地 curl 会被
harness REDACT —— 这三条确实不通, 但**不要**因此断言"图取不回来"。)

**MODE A — 真实照片 reference + 环境对应生成器 (网球人物故事默认):**
1. **Find the real photo**: the subject's IG / official collab posts (@wta·@wimbledon×player "champion"
   posts are gold) / a full-res frame from own footage. Prefer 竖版, high-emotion 夺冠特写 (捧杯/举杯/
   泪目). Identity-verify via the rule-3 ladder. Download: IG scontent → hidden-form POST the signed URL
   to `scripts/cover_bridge.py` (server-side fetch works for IG, unlike oaiusercontent).
2. **Codex 路径:** 直接调用内置 `image_gen` 编辑 reference image。Prompt 必须明确锁住人物的脸型、
   五官、肤色、发型、体型、原照片服装/姿势与场景, 只允许为适应版式做背景延展和文字设计。生成后
   全分辨率比对脸、服装和手; 人物变成“像她的另一个人”就定点编辑/重生, 绝不交付。
3. **Claude 路径 — 必须使用 Web ChatGPT, 首选 window.name 接力 (2026-08-02 实证, 见 memory
   `cover-inject-window-name-relay`)**: 图所在目录起 `python3 -m http.server` → 新标签开
   `http://127.0.0.1:<port>/<img>` 并在页内 fetch→FileReader→`window.name=dataURL` → **同一标签**导航到
   chatgpt.com(window.name 跨域存活; CSP 挡的是 chatgpt 去 fetch localhost, 不挡 localhost 页自己 fetch)
   → 读 window.name→atob→File→DataTransfer→对 `#prompt-textarea` 派发 paste 事件。旧法(压缩 ≤20KB →
   base64 → **3200-char chunks** 分片注入, ~16 次调用)只留作 window.name 被占用时的后备:
   (`window.__P+='...'`, verify cumulative length EVERY call — longer self-authored literals silently
   truncate) → `atob`→`Uint8Array` (check JPEG magic 0xFFD8) → `new File`→`new DataTransfer` →
   dispatch `ClipboardEvent('paste',{clipboardData:dt})` on the focused `#prompt-textarea` → confirm
   the attachment thumbnail appears (screenshot). ~10 tool calls.
4. **Prompt** (one line, insertText): 「以我附上的这张她本人的真实夺冠照片为封面底图:保留照片里真实的
   人物、姿势和球场背景,不要重绘、替换或美化人物,只在这张照片上做封面排版——【四处文字模板】;画面按
   竖版3比4输出,主标题和副标题完整放在画面上半部分,可在上下用照片的虚化延展补足空间,所有汉字必须
   逐字准确。」横版另起一次生成: `4:3, 文字左、人物右`, 不复用竖版裁切。
5. **逐字+身份校验 (MANDATORY):** download/read the result (Web 路径用 in-page
   `fetch(img.src)`→b64→form-POST to the bridge; async JS must write to `window.__r`, direct await
   returns `{}`), crop the four text zones at FULL resolution, Read them, check EVERY character, then
   compare the face/outfit with the reference. Any wrong/extra/missing char or identity drift → targeted
   edit/regenerate. 输出双封面到项目目录并与 `小红书发布文案.md` 一起交付。

**MODE B — 全AI直出 (fallback when no usable real photo exists):** 生成入口仍严格按环境分流
(Codex=`image_gen`; Claude=Web GPT), then use the same four-text-zone template plus
人物主体描述【外形+本片高光瞬间特写】+ 写实电影感【光线/场景】+ 人物占中下2/3、头顶不碰副标题。
高光瞬间 = the video's emotional peak (夺冠=举杯, 逆转=怒吼, 告别=背影…). Pose language must be
PRECISE (高举过头顶≠捧起≠端着 — "捧起" rendered as 端盘子 once). Pose/composition fixes = EDIT the
previous image (「基于你上一张生成的封面图修改:【改动】,其余全部不变」), never re-prompt from scratch.

**MODE C — ONLY with the user's explicit approval, never on your own initiative (demoted 2026-07-16):**
if 4o repeatedly mangles text after regeneration attempts, ASK the user; only if they approve, request
the art 不带任何文字 + 顶部1/4负空间, then burn typography locally with `scripts/make_cover.py <base>
封面图.jpg "主标" ["副标"] ["人名"] [角标]` (Songti SC Black/Bold, gold sub, tracked name + gold dots,
#C4563A pill, 1242×1656).

**Composer gotchas (each one happened):** `computer type` can silently DROP characters (「21」+parens
vanished) and cmd+A-delete can fail so text ACCUMULATES → always `javascript_tool` with
`execCommand('selectAll')+('delete')+('insertText',P)`, VERIFY key substrings in `#prompt-textarea`
innerText, then JS-click `button[data-testid="send-button"]`. Newlines auto-send — ONE line only.

### 9. 发布 — when the user asks to publish, use the `publish-xhs-douyin` skill
Both platforms' web backends are handled through the environment-specific authenticated browser:
**Codex uses its in-app Browser; Claude uses Claude for Chrome.** Keep that browser path for the whole
publish run and reuse the user's logged-in tabs; do not switch to a new/headless browser.
video upload via the window.name relay + `publish_bridge.py`, title/body/tags, chapter features,
declarations, custom cover, and 定时发布. The complete dual-platform playbook (step order, injection
snippets, per-platform quirks, timezone semantics, white-screen recovery) lives in the separate
**`publish-xhs-douyin`** skill — invoke it; do not improvise from memory. Non-negotiable user rules
enforced there: 🎾 title prefix (tennis); XHS = chapters via 添加章节 **at first publish** (locked
after; never in the body text) + 原创声明 ON; douyin = 自主声明「内容为个人观点或见解」+ chapters
(智能章节 or manual) + last-tag trailing space. Default schedule slot: Beijing 19:00 (XHS picker IS
Beijing time; douyin picker is browser-local — convert).

## Why it looks the way it does
- **Dark moving blur fill**: the footage is scaled-to-cover, blurred, and **darkened ~0.42** behind
  the centred 16:9 strip, with a clay overlay darkening top/bottom for text. Dynamic (not a static
  card) but ad boards never read as text. (`make_overlay` + `_render_base` in render.py.)
- **All text is PIL → PNG → ffmpeg overlay** (this ffmpeg lacks drawtext/subtitles). Font: clean
  heavy **Hiragino Sans GB W6** (`index=2`) — legible is the priority.
- Captions: word-exact from `captions.json`; else proportional. Montage scenes concat per-clip bases
  then overlay chip/caps across the full scene.

## Engine scripts (`scripts/`, copied into `build/`)
`scenes_template.py` (config; incl. optional `CARDS`/`MUTE_AMBIENT`/`FIT_WINDOWS`/`IG_EXCLUDE`/`PART_MAP`
knobs + "+" contiguous-slice markers) · `detect_shots.py` · `pick_ends.py` · `align.py` (align a recording) ·
`caption_times.py` (word-exact captions) · `render.py` (`all`/`scene <ID>`/`assemble`/`assemble-voice`/
`assets`; per-scene cards via `treat="card:<key>"`) · `tts_say.py` (robotic draft) · `contact_sheet.py` ·
`shotsheet.py` · `pick_clean.py` (flash-free window finder from `/tmp/lum_*.txt` signalstats profiles) ·
`assemble_ambient.py` (FINAL assembler: voice + each clip's real audio — final gain 0.15, rule 10; honors
`MUTE_AMBIENT`; silent sources → auto-silence) · `finalize_ending.py` (LAST step, rule 11: append
`$PERSONAL_ASSETS/ending.mov` + re-encode 1080p60; auto 9:16/16:9; 缺资产自动降级跳片尾) · `regen_tts_itts.py` (**默认配音引擎** IndexTTS-2 情感整段模式: emo参考+整段直出+数字邻接逗号改写+digitmerge门+拼音纠正+whisper拼音平面门, CPU-only, 原生语速, 输出与F5同接口; EMO_MODE=0 退逐句后备) ·
`regen_tts.py` (F5 后备: QUADRUPLE-GATE cloned TTS: anti-leak probe + junk-insert
detection + acronym-completeness + zero intra-line pauses per take, 5 takes, best-of; strips "/" from vo;
TARGETS-resumable) · `check_tts.py` (transcript-check report) ·
`check_boundaries.py` (句末该停没停 audit: silencedetect + 边界时间映射 → boundary_audit.json) ·
`insert_pauses.py` (外科式修复 v2: RMS 低谷选切点+GATE 拒切字中间+室内底噪+余弦融合, 不重新合成 — F5 重生成会随机吞掉别的句号; v1 硬拼纯零曾把「强」字劈开被用户听出) ·
`fix_pauses.py`/`fix_pauses_lib.py`/`regen_fix.py` (断句 audit: silencedetect + difflib line-boundary
mapping → regen mid-line-pause scenes; the step-3 prosody pass) · `preview_parts.py` (per-part
预览_A….mp4, voice+ambient, `PART_MAP`-aware — the segment-preview checkpoint) · `build_photos.py`
(photo→video Ken-Burns via PIL subpixel affine — user-request ONLY now, rule 9: stills default to pure
static `-loop 1`; zoompan always banned) ·
`make_cover.py` (小红书封面本地排版 — MODE C, explicit user approval only) · `cover_bridge.py`
(localhost 图片下载桥, ChatGPT/IG 签名URL专用) · `publish_bridge.py` (发布桥: 本地文件服务器喂
成片/封面给创作者后台上传控件, CORS+PNA 头齐全 — the publish workflow itself lives in the
`publish-xhs-douyin` skill) ·
`render16.py` + `assemble16.py` (16:9 / 1920×1080 variant from the same scenes/timing/captions) ·
`reframe_scenes.py` (full-bleed: crop landscape→9:16 tracking the player, via video-autoreframe; v2 读 FIT_WINDOWS 真跳过 + 产 subject_report.json 主体在场预筛) ·
`reframe_span.py` (contiguous montage slices: ONE YOLO pass per span split into per-slice keys; skips
vertical stems + `FIT_WINDOWS`) ·
`build_ig.py` (native-vertical + `ig_ph_*` clips → `build/reframed/` keys; cover-crop scale so non-9:16
never stretches; respects `IG_EXCLUDE`).
render.py prefers a `build/reframed/<stem>_<tin>_<dur>.mp4` if present (full-bleed) else blur-fill — see
`references/vertical-footage-and-instagram.md`.
动态演示卡不走 `scripts/` — 引擎是外置的 HyperFrames CLI (npx), 账号模板+frame.md 在
`assets/hyperframes-card-template/`, 集成规矩在 `references/hyperframes-dynamic-cards.md` (rule 21)。

Voice cloning lives at `/Volumes/Storage/voice-clone/` (venv + `clone.py` + the user's reference clip;
`VOICE_SPEED` env controls pace). Recreate per `references/voice-and-audio.md` if missing.
