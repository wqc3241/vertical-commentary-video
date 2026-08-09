# frame.md — 账号动效图文冻结规范 (vertical-commentary-video)

动态卡与成片图文同族：来源是 render.py 的账号视觉体系。每张新卡从此表继承；换色/换字体
属于"动账号视觉"，需用户确认。

## 色板（与 render.py 常量逐一对应）
| token | 值 | 用途 | render.py 出处 |
|---|---|---|---|
| clay | `#C4563A` | 胶囊/强调/红土语义 | `CLAY=(196,86,58)` |
| gold | `#E2BC68` | 分隔线/数字强调 | `GOLD=(226,188,104)` |
| white | `#F8F6F3` | 主文字 | `WHITE=(248,246,243)` |
| muted | `#D8CDC0` | 次级文字 | subtitle (238,226,214) 族 |
| ink-bg | `#201310 → #0A0605` 纵向渐变 + 顶部 clay vignette (16%) | 卡底 | `make_overlay` clay 暗化 + `_scrim` |
| panel | `rgba(255,255,255,0.07)` + 1px `rgba(255,255,255,0.08)` 边, r24 | 行条/面板 | rows `(255,255,255,30)` |
| ball | optic yellow 径向渐变 `#F4FF86→#D9EC2F→#AEBD1E` | 网球 | — |

场地语义色（科普卡用）：红土=clay 本色 `#C4563A` · 硬地 `#3D7FBF` · 草地 `#4C9160`
（真实场地色，饱和度/明度压到与暖黑底同档）。

## 字体
`font-family: "Hiragino Sans GB", "PingFang SC", sans-serif; font-weight: 600`（= PIL 的 W6 index 2）。
必须声明 `@font-face { font-family:"Hiragino Sans GB"; src: local("Hiragino Sans GB"); }`（渲染器要求）。
字号档：大标题 80 / 面板名 56 / 胶囊·正文 30-40 / 次级 28。

## 组件语法
- **胶囊 chip**：全圆角、clay 底 95%、白字、微 text-shadow —— 同 `make_chip_png` 形制。
- **面板行条**：panel 底 + 左侧 14px 语义色 spine（r24 只圆外侧）。
- **数据条**：track `rgba(255,255,255,0.12)` h14 r7；fill 语义色，`scaleX` 从 0 生长（origin left）。
- **金色分隔线**：320×8 r4 gold，`scaleX` sweep 入场。

## 动效语气（稳重科普感，不炸裂）
入场 `power3.out` 0.5s；胶囊/标签 `back.out(1.6-1.7)` 微回弹；逐字标题 stagger 0.045；
轨迹类：MotionPath + 同径 SVG 描线（dashoffset）留存轨迹；对比类保留"同步重放"节拍。
禁：`repeat:-1`、随机、闪烁高频动效。

## 站内版式约束（进成片的卡）
关键内容 y≈260-1400；顶部 148-230 让给场景 chip、底部 1440+ 让给字幕带；
**不自带标题胶囊/tagline/脚注**（独立发布版才加）。末段 ≥0.8s 稳定可读态。

## 已沉淀卡型
- `index.html` — 三面板对比卡（轨迹演示 + 数据条 + 同步重放，独立发布版含自带胶囊/tagline）。首用：A/B 对比 demo (2026-08-09)。
- `cards/scale.html` — 刻度分级卡（1→5 横轴 + 语义色胶囊落位 + 引线；「多数」限定语小字）。首用：ITF 场速分级，场地弹跳讲解 P2。
- `cards/layers.html` — 剖面层叠卡（自下而上逐层生长 + 顶层高亮脉冲 + 侧标注 + 金色深度括号）。首用：红土五层结构 P4。
- `cards/clay.html` / `cards/grass.html` / `cards/hard.html` — 单面板弹跳演示卡（大轨迹 MotionPath + 描线留存 + 落点 FX + 双数据条；三张互为参数化变体，clay 为母版）。首用：P5/P7/P8。
- `cards/replay.html` — 三面板同步重放卡（轨迹预绘 + 三球同发对比，无描线动画）。首用：收尾开放问题 P9。
- 以上站内版均已按规矩让位字幕带/chip 区；时长按念白槽位改根节点 data-duration 后重渲染即可复用。
