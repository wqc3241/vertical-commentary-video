# HyperFrames 动态演示卡 (2026-08-09 用户拍板引入)

动态示意图/数据卡/流程演示的默认生产方式：用 HyperFrames (HTML+GSAP → headless Chrome 逐帧
→ MP4) 生成**竖版 1080×1920 无声动态卡 stem**，作为普通素材嵌进现有管线。静态 PIL 卡体系
(`make_results_card`/`treat="card:"`) **原样保留不删**——战绩卡等 ≤3s 插片仍可走老路；
HyperFrames 负责"要动起来才讲得清"的内容：弹跳轨迹、数据条生长、数字滚动、对比演示、流程图。
选型判据：画面是**演示一个过程/对比**→HyperFrames；画面是**一屏静态数据**→老 PIL 卡也行。

## 一次性前置（已装好, 2026-08-09）
- Node 22+（本机 v24）。HyperFrames 官方 agent skills 已装进 `~/.claude/skills/`
  （hyperframes 路由 + core/animation/cli 等 8 个核心 + motion-graphics 工作流）。
- 缺失/过期时：`npx hyperframes skills update`（核心集）/ `npx hyperframes skills update motion-graphics`。
- 写组合 HTML 前必读 `/hyperframes-core`（组合契约）；本文只记本管线的集成规矩，不复述其契约。

## 账号样式 — frame.md 冻结（对应封面"四区冻结模板"的动效版）
模板与样式规范在 skill 仓库 `assets/hyperframes-card-template/`：
- `frame.md` — 冻结色板/字体/组件语法（CLAY `#C4563A`/GOLD `#E2BC68`/暖白 `#F8F6F3`/暖黑底/
  Hiragino Sans GB W6/胶囊 chip/行条面板）。每张新卡从这里继承，不要每期重新发明配色。
- `index.html` — 已验证的工作样例（三场地弹跳对比卡：轨迹 MotionPath+描线留存+同步重放+条形生长），
  换数据/换版面直接改它。
- `shot-plan.json` — motion-graphics 工作流的 IR 样例。

## 每期生产流程
```bash
cd "$PROJ" && npx hyperframes init hf-cards --non-interactive --example=blank --skill=motion-graphics
cp ~/.claude/skills/vertical-commentary-video/assets/hyperframes-card-template/{index.html,shot-plan.json} hf-cards/
# 改数据/版面/时长 → 三连门禁：
(cd hf-cards && npm run check)                        # lint+runtime+layout+contrast 全绿才继续
(cd hf-cards && npx hyperframes snapshot --at <首,标志动作,尾>)   # Read 每帧: 逐字校验文字+版面
(cd hf-cards && caffeinate -i nice -n 15 npx hyperframes render . -f 60 -q high -w 2 -o renders/<name>.mp4)
cp hf-cards/renders/<name>.mp4 "$PROJ/source/hf_<name>.mp4"      # 当普通素材 stem 用
```
M4 实测：10s@60fps 600 帧 ≈21s, 峰值 ≈0.5G——很轻，但仍守串行纪律（不与 TTS/reframe/数字人/
总渲染并行；`-w 2` 封顶）。

## 嵌入管线的硬规矩（每条都对应一次实踩）
1. **时长 = 念白槽位时长。** 根节点 `data-duration` 写成该 scene（或 montage slice）的精确秒数；
   编排动画时**末段留 ≥0.8s 可读稳定态**。任何时长变化（重录 TTS/插停顿）→ 改 `data-duration`
   重渲染重放入——规则 5"时长变了必重扫"对动态卡同样生效。
2. **给字幕带和 chip 让位。** 成片会在卡上叠加念白字幕（底部 ~1440-1620px 区）和场景 chip
   （顶部 ~148-230px 区）：卡内关键内容保持在 y≈260-1400 之间；**站内用的卡不要自带标题
   chip/tagline/脚注**（demo 卡的「网球小知识」胶囊和底部两行是独立发布版式，进片前删掉），
   scene 设 `title=""` 或让位给场景 chip——与规则 13"卡文案不与 chip 相撞"同源。
3. **接入方式 = 普通 source stem**（默认）：`source/hf_*.mp4` 是原生 1080×1920 → render.py 的
   blur 路径 `scale=1080:-2` 后天然满屏，叠 overlay 暗化顶底正好托字幕——零代码改动。scenes.py
   里当普通 clip/montage slice 引用（`("hf_bounce",0)`），`lock: True`。反 scrim 的进阶用法：按
   `build/reframed/<stem>_<tin:.3f>_<dur:.3f>.mp4` 命名直塞 reframed 键位（render.py 优先取用，
   注意 3 位小数必须与切片时长逐位一致）。reframe 系脚本对竖版 stem 本就跳过，无需 FIT_WINDOWS。
4. **无声即正确。** 动态卡不带音轨，`assemble_ambient.py` 对无声源自动补静音（规则 10 的既有
   机制），不要给卡配音效。
5. **QC 同素材同权。** 步骤 7 的抽帧检查覆盖动态卡窗口（首/中/尾帧）：文字逐字准确（同封面
   标准）、数字与事实清单一致、无越界/截断。`check` 的 contrast 门是机器保障，但中文逐字校验
   仍要人眼 Read 帧。
6. **确定性红线**（`/hyperframes-core` 契约，lint 会抓大部分但写对省一轮）：单条 paused GSAP
   timeline 挂 `window.__timelines`；禁 `repeat:-1`/`Math.random`/时钟；CSS transform 初值与 GSAP
   同属性 tween 冲突用 `fromTo` 解；隐藏元素的 fromTo 目标要显式写 `opacity:1`（冷 seek 陷阱）；
   系统字体要 `@font-face { src: local("Hiragino Sans GB") }` 声明。

## 沉淀
可复用的新卡型（对比卡/时间线卡/地图卡…）做完就把 HTML 存回
`assets/hyperframes-card-template/` 并在 frame.md 登记组件——和封面模板一样滚雪球。
首个实证：`/Volumes/Storage/Documents/剪视频/hyperframes_demo/`（A/B 对比 + tennis-bounce-card 工程）。
