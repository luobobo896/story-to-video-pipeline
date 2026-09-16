# Story-to-Video Pipeline · 影视制作流水线（复用层 · 短剧 / 影视 / 动画通用）

**English**: A reusable AI video production pipeline. You put in a script or a novel, you get out a finished cut you can publish. Short dramas, TV/web series, film, animation and anime all run the same 13 steps; rules, tools, docs and the orchestration skill are installed once and shared.

规则、脚本、文档和编排 skill 都放这一层，装一次，短剧、网剧、影视、动画、漫剧共用同一条工序链。具体剧本的数据只落在 `projects/<项目名>/`，项目状态写在该项目自己的 `README.md` 里。这份文件是总清单：环境、依赖、skill、组件、工序各是哪些。

## 它解决什么问题

丢一份剧本 txt 进去，按 N0–N12 走一遍，出来的是一集可以直接发的成片。过程中的状态全写在文件里，每一步过不过由脚本判，所以能随时停、随时换人接手，对话重开也不受影响。

| 常见翻车 | 这里怎么处理 |
|---|---|
| 人物的脸、场景、风格越做越不像 | 定妆图三视图、场景空镜、风格锚图先定稿再进分镜；锚点带 `sha256` 记进台账，每镜挂同一套参考图 |
| 对话一重开，进度就丢 | 状态只从磁盘上的 `schema/` 读 |
| 悬浮、匀速漂移、表情崩 | `rules/PH` 11 条、`rules/ME` 10 条，阈值都是实测出来的 |
| 台词比镜头长，字幕对不上 | N7 写分镜时先算台词预算，N9 用实测音频时长回填，R8 / R16 会拦 |
| ffmpeg 一条命令白干 | 字幕走 `ffmpeg-full`；`rules/FF` 11 条管响度、转场和镜头时长 |
| 积分不知不觉烧完 | 单价和档位门槛在 [docs/10](docs/10-account-plans-and-credits.md)，R21 拦越档模型 |
| 4–9MB 的图把上下文顶爆 | 先过 `tools/eye.py` 压到 300KB 以内再看 |
| 交片之后说不清怎么做的 | 台账、验收关、归档包、git tag 都在，解压后能重新跑一遍校验 |

工序 13 道（N0–N12），验收关 8 道（G0–G7，其中 3 道要停下来等人点头），校验规则 R0–R21，规则库 5 篇 50 条（COMP 12 · ME 10 · PH 11 · VD 6 · FF 11），脚本 7 个且只用标准库，每个项目一套 `schema/` 台账。

样张（来自示例项目 [`projects/zhuangyuan-ep01`](projects/zhuangyuan-ep01/)，点图看大图）：

| 角色定妆图（三视图） | 场景空镜（镇北侯府·厅堂） |
|---|---|
| <img src="projects/zhuangyuan-ep01/docs/images/01-character-sheet-CH001.jpg" width="420"> | <img src="projects/zhuangyuan-ep01/docs/images/02-scene-EN001.jpg" width="420"> |
| 风格锚图（材质板，统一全片调性） | 成片截帧（9:16 分发版 demo） |
| <img src="projects/zhuangyuan-ep01/docs/images/03-style-anchor-ST001.jpg" width="420"> | <img src="projects/zhuangyuan-ep01/docs/images/05-final-cut-9x16-demo.jpg" width="420"> |

G2 定妆关的评审拼图，4 张资产一次过目，人就在这里停下来拍板：

<img src="projects/zhuangyuan-ep01/docs/images/04-g2-review-sheet.jpg" width="720">

> 5 张都是 `tools/eye.py` 压过的看图版，加起来 724KB；4–9MB 的原始 PNG 留在 `project/work/`，不入库。

## 一、快速开始

```bash
python3 tools/bootstrap.py --doctor            # 体检：工具、CLI 登录、skills，缺什么它会说
python3 tools/bootstrap.py 剧本.txt            # 铺出一个独立项目（-o 也可以放到仓库外）
python3 tools/check_consistency.py --schema-dir projects/<项目名>/schema   # 随时查状态
```

第二步之后交给编排 skill：说一句「按 story-to-video 跑」，它按 N1 → N12 推，每步记进 `schema/` 台账并跑一次场记核对，三处人工验收关会停下来等你。

换机的环境安装、注册、登录、验证见 [docs/09](docs/09-toolchain-setup.md)；工序依赖总图与验收关定义见 [docs/08](docs/08-pipeline-overview.md) 和 [docs/04](docs/04-risks-and-verification-gates.md)。

---

## 二、系统环境（本机实测，2026-09-16）

| 项 | 值 |
|---|---|
| 系统 | macOS 15.7.5（arm64），Homebrew `/opt/homebrew` |
| 工作目录 | `~/work/个人文档/v-pr/`（本仓库 + 项目实例 + 第三方 skill 源码） |
| Agent | Codex（`~/.codex/skills/`），Claude Code 也能用（`~/.claude/skills/`） |
| Node 管理 | fnm（`~/.local/share/fnm`） |
| 凭证 | `~/.config/higgsfield/` 下的登录态，没有别的 apikey |

---

## 三、依赖与 CLI 清单

### 3.1 系统二进制

| 依赖 | 版本 | 安装 → 验证 | 干什么 |
|---|---|---|---|
| `python3` | 3.14.6 | `brew install python@3` → `python3 -V` | 本仓库全部脚本（场记核对、脚手架、字幕、回填、看图限流） |
| `node` / `npx` | v25.9.0 / 11.19.1 | `fnm install --lts` → `node -v` | 跑 `shuohao-skills` 的 `.mjs` 脚本（要求 ≥18）；`npx` 装 `ffmpeg-skill` |
| `jq` | 1.8.2 | `brew install jq` → `jq --version` | 查 `schema/*.json`，确认项目参数 |
| `git` | 2.39.5 | `xcode-select --install` → `git --version` | `schema/` 与文档的版本管理、rename 追踪 |
| `magick` | 7.1.2-27 | `brew install imagemagick` → `magick -version` | 图片规格统一、拼版、帧差测量（`rules/ME` 的测量方法） |
| `tar` / `shasum` | 系统自带 | 不用装 | 归档包、剧本指纹与资产哈希（`assets.json.sha256`） |

### 3.2 ffmpeg：必须装两个

只有 `ffmpeg-full` 带字幕滤镜，系统那套没有；两者 keg-only，互不覆盖。

| 二进制 | 能力 | 干什么 |
|---|---|---|
| `ffmpeg` / `ffprobe`　9.0.1 · `/opt/homebrew/bin/` | 无 libass / freetype / vidstab | 规格核对（`ffprobe`）、基础拼接与转码 |
| `ffmpeg-full`　9.0.1 · `/opt/homebrew/opt/ffmpeg-full/bin/` | 有 `subtitles` / `drawtext` / `vidstabdetect` | 字幕烧录、文字叠加、防抖、带时间码的 QA 拼图 |

```bash
brew install ffmpeg ffmpeg-full          # keg-only，互不覆盖
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"   # 每次调用前，必须（FF-001）
ffmpeg -hide_banner -filters | grep -E "subtitles|drawtext"   # 两条都要有输出
```

报 `No such filter` 就是 PATH 没生效（`ffmpeg-skill` 用 `shutil.which("ffmpeg")` 找二进制）。

### 3.3 higgsfield CLI 与账号（唯一要花钱的依赖）

| 项 | 值 |
|---|---|
| 版本 / 路径 | 1.1.25（build 2026-09-14）· `/usr/local/bin/higgsfield` |
| 安装 | `curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh \| sh` |
| 登录 | `higgsfield auth login`（设备码 → 浏览器授权），凭证落 `~/.config/higgsfield/credentials.json`（600） |
| 账号 | 已登录，basic 套餐。余额随时在变，以 `higgsfield account status` 为准 |
| 模型名 | 以 `higgsfield model list` 为准，文档会滞后；实测出图真名是 `nano_banana_pro` |

要花钱的活，单价如下（档位门槛、月费与一集预算见 [docs/10](docs/10-account-plans-and-credits.md)）：

| 用途 | 模型 | 单价 |
|---|---|---|
| 出图 · 场景空镜 | `soul_location` | 0.12 积分/张 |
| 出图 · 角色 / 带参考图 | `nano_banana_pro`（≤14 张参考图） | 2 积分/张 |
| 出视频 | Basic 只有 `seedance_2_0 --mode fast`（≤720p）与 `seedance_2_0_mini`；完整 2.0 / 2.5 需 Pro | 3.5 / 2.5 积分/秒 |
| 配音 | `text2speech_v2` | 0.1 积分/句 |
| 横转竖 | `generate workflow reframe`（默认不用，改用 ffmpeg 裁切） | ≈9.3 积分/秒 |

用不上的两个：`soul-id`（真人脸训练要付费档，这里改用定妆图三视图）、`generate workflow dubbing`（只做中文，不需要配音出海）。

---

## 四、Skills 清单

### 4.1 本仓库自带（`skills/`，软链到 `~/.codex/skills/`）

| Skill | 版本 | 干什么 |
|---|---|---|
| `story-to-video` | 1.0.0 | 编排层。丢进剧本就按 N0–N12 走，管验收关和停机待审，状态记进台账；规则不复制一份，直接用 `rules/` |

### 4.2 外部安装（源码在仓库外，软链进 `~/.codex/skills/` 或 `~/.agents/skills/`）

| Skill | 版本 / 来源 | 干什么 | 工序 |
|---|---|---|---|
| `novel-outline` | 1.2.0 · [shuohao-skills](https://github.com/eternityspring/shuohao-skills)（Apache-2.0） | 小说 → 大纲五件套（改编说明 / 人物表 / 爽点表 / 分集梗概 / 资产清单），14 道质量门 | N1、N4 |
| `novel-characters` | 1.11.0 · 同上 | 角色设定集：画像、形象提示词、音色提示词、设定图 | N2、N5、N6 |
| `novel-art` | 1.2.0 · 同上 | 美术设定集：场景与道具锚点、光照变体、白底提示词，11 道质量门 | N3、N6 |
| `novel-script` | 1.2.0 · 同上 | 剧本：场次 + 节拍流，时长按语速折算，10 道质量门 | N7 |
| `novel-storyboard` | 1.3.0 · 同上 | 分镜三层：段（≤15s）→ 分镜（2–5s）→ 分镜图，17 道质量门 | N7、N8 |
| `ffmpeg-skill` | 1.17.3 · `kajisho5/ffmpeg-skill`（MIT，42 个工具） | 全部剪辑与交付：裁剪 / 拼接 / 横转竖 / 字幕 / 响度 / QA 看图 | N11、N12 |
| `seedance` | `MapleShaw/seedance2.0-prompt-skill`（MIT） | 运镜四维编码 Z/Y/X/F、25 格流水线、剪辑公式 | N7、N11 |
| `higgsfield-generate` | 0.12.0 · [higgsfield-skills](https://github.com/higgsfield-ai/skills)（同仓库共 9 个） | 出图 / 出视频 / 出音频，30+ 模型统一入口 | N6、N8、N9 |

装法（上面几个仓库各装一次；走软链装的，之后 `git pull` 即生效）：

```bash
# shuohao-skills：短剧前段五件套（novel-*），自带脚本软链进 agent 的 skills 目录
git clone https://github.com/eternityspring/shuohao-skills.git && cd shuohao-skills && ./scripts/install.sh

# higgsfield 官方 9 个 skill（含 higgsfield-generate）；顺带装好 CLI，装完跑 higgsfield auth login
npx skills add higgsfield-ai/skills       # 等价：gh skill install higgsfield-ai/skills

# seedance / ffmpeg：源码放在仓库外，用软链引进来，之后 git pull 就生效
ln -s <seedance 仓库根> ~/.agents/skills/seedance-prompt-skill
npx ffmpeg-skill --codex            # → ~/.agents/skills/ffmpeg-skill

# 本仓库自带的编排 skill
ln -s <本仓库根>/skills/story-to-video ~/.codex/skills/story-to-video

ls ~/.codex/skills ~/.agents/skills | grep -E "novel-|higgsfield-|ffmpeg-skill|seedance"   # 验证
# higgsfield 自检：在 agent 里说「用 higgsfield 出一张最小测试图」，它应调 higgsfield-generate 并返回图片 URL
```

本机实际位置：`higgsfield-skills/`、`shuohao-skills/`、`seedance-prompt-skill/` 都在仓库的上一级 `~/work/个人文档/v-pr/`，`ffmpeg-skill` 直接装在 `~/.agents/skills/`。逐条的验证命令与登录态排查见 [docs/09](docs/09-toolchain-setup.md)。

### 4.3 Codex 内置（按需）

| Skill | 干什么 |
|---|---|
| `imagegen` | 位图生成与编辑（`novel-*` 出设定图也走它），N6 |
| `spreadsheets` / `excel-xlsx` | 资产清单、分镜表导出 XLSX，N12 |
| `visualize` | 节奏曲线、时间线可视化，N7 / N11 |

### 4.4 明确不装

| Skill | 原因 |
|---|---|
| `higgsfield-soul-id` | 要 Basic 以上套餐，这里用定妆图三视图代替 |
| `higgsfield-video-explainer` / `brandkit` / `product-photoshoot` / `marketplace-cards` | 解说片与电商向，短剧不需要 |
| `create-storyboard-skill` / `cinematic-storyboard-skill` / `h3-storyboard-skill` | 分镜已经统一用 `novel-storyboard`，同类的不再装 |

---

## 五、组件清单（仓库里有什么）

| 组件 | 路径 | 是什么 |
|---|---|---|
| 规则库 | `rules/` | 与剧本、模型无关的硬约束（人写）：`COMP` 12 项 · `ME` 10 条 · `PH` 11 条 · `VD` 6 条 · `FF` 11 条，阈值分 `[硬]` / `[软]` |
| 通用文档 | `docs/01–06`、`08–10` | 01 阶段说明 · 02 一致性控制 · 03 依赖与凭证 · 04 风险与验收关 · 05 运行与编排 · 06 连贯性与物理检查清单 · 08 工序依赖总图 · 09 工具链安装 · 10 账号档位与积分 |
| 脚本 | `tools/` | 7 个零依赖脚本，见下表 |
| 骨架模板 | `templates/schema/` | 新项目 `schema/` 的骨架，`bootstrap.py` 的唯一来源 |
| 项目实例 | `projects/<项目名>/` | 每个剧本一套（Codex 写）：`schema/`（台账）、`project/`（素材）、`docs/07`（实测记录）、`README.md`（状态） |
| 凭证 | `~/.config/higgsfield/` | Higgsfield 登录态，按密钥对待 |

### 脚本清单

| 脚本 | 干什么 |
|---|---|
| `bootstrap.py` | 入口脚本。`--doctor` 体检工具链、登录和 skills；给剧本就铺项目骨架（入库 + 指纹 + 空 `schema/`） |
| `check_consistency.py` | 验收关。查引用完整性、编号规范、台词预算、字幕对齐、QA 十项等 R0–R21；`--delivery` 另审交付完整性 |
| `make_srt.py` | `shots.csv` → SRT，时间轴跟实测音频，单行 ≤20 字 |
| `tts_batch.py` | 按台词 + 音色批量 TTS，回填实测 `audio_duration_s` |
| `record_shot.py` | 把生成结果（`job_id` / `clip_file` / `qa_*`）回填到指定镜头行 |
| `eye.py` | 把素材压成 ≤300KB 的 JPEG 再看，防止上下文被撑爆（413） |
| `_project.py` | 项目定位（显式路径 > `projects/` 下唯一项目 > 报错列候选），被上面几个脚本 import |

```bash
python3 tools/bootstrap.py --doctor                  # 体检：缺什么它会说装什么
python3 tools/bootstrap.py 剧本.txt                  # 铺出一个项目骨架
python3 tools/check_consistency.py --schema-dir projects/<项目名>/schema
python3 tools/make_srt.py                            # 项目不唯一时统一加 --schema-dir
python3 tools/tts_batch.py --dry-run
python3 tools/record_shot.py --shot EP01-SC01-SH001 --set status=done
python3 tools/eye.py <图或视频> --tiles 3x2
```

### 每个项目的 `schema/` 四件套（场记台账）

| 文件 | 内容 | 填于 |
|---|---|---|
| `story_bible.json` | `meta`（项目名 / 指纹 / 画幅 / 题材与时代 / 作者指定参数）、`characters[]`、`props[]`、`environments[]`、`styles[]`、`wardrobe[]`、`timeline[]`、`plot_beats[]`、`episode_plan[]`、`open_questions[]` | N1–N4 |
| `assets.json` | `assets[]`（定妆图 / 场景图 / 风格锚 + `anchor_file` + `sha256` + `job_id`）、`voices[]`（`VC-###` 音色绑定） | N5 / N6 |
| `episodes.csv` | 集 → 场次 → 镜头 三级索引 + 剧本映射 + 预估时长 | N7 |
| `shots.csv` | 分镜表（48 列：时长 / 姿态 / 位置 / 视线 / 道具 / 物理 / 提示词 / 参考资产 / `job_id` / QA 十项 / 版本） | N7–N10 |

---

## 六、每一步干什么（N0 → N12）

阶段代号 S0–S7 是粗的，工序 N0–N12 是细的：S1 拆成 N1–N4，S5 拆成 N5 和 N9。每一步的输入、判据和规则编号在 [docs/01](docs/01-workflow-stages.md) 和 [docs/08](docs/08-pipeline-overview.md) 里写全了，下面这张表只留主干。

| 工序 | 干什么（工具） | 产出（记进台账） | 关卡 |
|---|---|---|---|
| N0 初始化 | 剧本入库、推项目名、算 sha256、建 `project/work` 五个目录和空 `schema/`（`bootstrap.py`） | 项目目录、`meta.script_sha256` | G0 筹备关 |
| N1 题材与时代 | 判题材、时代、是否跨时代，定服装考据方向和语体，每条附剧本原文（`novel-outline`） | `meta.theme` | R13 |
| N2 人物与服装 | 抽人物，写 3–6 条能拿图检验的外观锚点，标 `asset_level` 和 `voice_need`，拆服装造型 `WD-###`（`novel-characters`） | `characters[]`、`wardrobe[]` | G1 剧本过会 |
| N3 场景与物件 | 抽场景（带 `time_of_day` 和光照方向）与道具（带尺度和状态变体）（`novel-art`） | `environments[]`、`props[]` | G1 |
| N4 剧情与分集 | 标钩子、转折、高潮、结尾，排时间线，推集数与单集时长并写明依据（`novel-outline`） | `plot_beats[]`、`episode_plan` | G1 |
| N5 音色绑定 | 列候选音色，拿同一句台词海选试听，定稿后一角色一个 `VC-###`（`higgsfield voices list`） | `assets.json.voices[]` | R15、VD-001 / VD-005 |
| N6 资产出图 | 角色三视图（剪影级只出一张逆光剪影）、场景无人空镜、一张风格锚图；逐张比对锚点，不合格重生成（`soul_location` / `nano_banana_pro`） | `assets/*`、`assets.json.assets[]` | G2 定妆关（人过目） |
| N7 分集与分镜 | 拆场次、拆镜头（一镜一个主节拍），填时长、景别、姿态、视线、道具、物理、中心安全区和中文提示词，顺手把台词预算算掉（`novel-script` / `novel-storyboard` / `seedance`） | `episodes.csv`、`shots.csv` | G3 分镜关 |
| N8 视频生成 | 先出关键帧，再挂参考图生成视频，参数按账号档位给；逐镜做视觉十项 QA，不合格重生成（`seedance_2_0`、`eye.py`、`record_shot.py`） | `keyframes/`、`clips/`、`qa_*` | G4 过片关（人抽 3–5 镜） |
| N9 配音 | 逐句 TTS，量出真实时长回填；台词比镜头长就报错（`tts_batch.py`） | `audio/*.mp3`、`audio_duration_s` | G5 配音关 |
| N10 字幕 | 生成 SRT，时间轴跟实测音频，单行不超过 20 字（`make_srt.py`） | `edit/EP**.srt` | R16 |
| N11 剪辑成片 | 拼接、转场、调色、混音（台词 > 环境音 > BGM）、烧字幕，出 16:9 母版和 9:16 分发版；单镜时长不许改（`ffmpeg-skill` + `ffmpeg-full`） | `EP**_16x9_v001.mp4`、`EP**_9x16_v001.mp4` | G6 定剪关（人通看） |
| N12 交付归档 | 命名归档、出横竖封面、导资产清单、打归档包和 git tag（`imagegen` / `youtube-thumbnail`、`tar`） | `delivery/*`、`archive_*.tar.gz` | G7 交片关 |

并行关系：N1–N4 可以三路一起走，N5 和 N6 可以一起走，N9 不用等 N8。
关键路径：N0 → N1 → N6 → N7 → N8 → N10 → N11 → N12。

---

## 七、两条铁律

从剧本到成片，最容易走样的是五类信息：人物、道具、建筑、场景、风格。这里不指望模型记住它们，而是写进台账，每步对着改。

1. 状态以台账为准。任何阶段、任何一次重开对话，只读磁盘上的 `schema/`，不靠上下文记忆。
2. 资产先于镜头。定妆图、场景参考图、风格锚图没定稿，不进分镜，不出视频。

### 16:9 还是 9:16

抖音主流是 9:16 竖屏全屏，16:9 横屏在信息流里会被留黑边或缩成小窗，完播率更差。所以 16:9 作制作母版，9:16 作分发版。

| 版本 | 用途 | 怎么来 |
|---|---|---|
| 16:9 母版 | 保底、复用、二次剪辑、其他平台 | N11 直接出 |
| 9:16 分发版 | 抖音主发 | 剪辑时按安全区裁切（`reframe` 约 9.3 积分/秒，一般不用） |

横转竖会裁掉两侧，所以 N7 分镜阶段就得按中心安全区构图：横向只保留中间约 56%，主体、关键道具、字幕放中央，两侧留给可以牺牲的环境信息。规则见 [docs/02](docs/02-consistency-control.md)。

---

## 八、目录结构

```
story-to-video-pipeline/                        ← 复用层：不含任何具体剧本的数据
├── README.md                      本文件（总清单）
├── skills/
│   └── story-to-video/      编排 skill（软链到 ~/.codex/skills/）
├── docs/                          通用文档 01–06 / 08 / 09 / 10（项目实测记录在项目自己的 docs/07）
├── rules/                         规则库：COMP / ME / PH / VD / FF
├── tools/                         脚本：bootstrap / check_consistency / make_srt / tts_batch / record_shot / eye / _project
├── templates/schema/              新项目骨架（bootstrap 的唯一来源）
└── projects/                      项目实例区（-o 也可指向仓库外）
    └── <项目名>/
        ├── README.md              项目状态写这里
        ├── schema/                场记台账：story_bible / assets / episodes / shots
        ├── docs/07-project-calibration-notes.md
        └── project/{raw,work,delivery}/
```

rules 和 tools 不往项目里复制。复制就是分叉，两处早晚对不上；项目只带 `schema/`、`project/`、自己的 README 和实测记录。

---

## 九、维护约定

| 要改什么 | 改哪里 | 注意 |
|---|---|---|
| 加一条通用规则 | `rules/<前缀>-*.md` | 必须带依据（实测数据 / 物理常数 / 可查证实测），并尽量落进场记核对 |
| 加一条可自动检查的约束 | `tools/check_consistency.py` | 同时补 `--selftest` 负例，否则等于没加 |
| 改 schema 列 | `templates/schema/` + 现有项目的 `schema/` | 列数变化会被 R0 抓到；两处都要改，别只改一处 |
| 加一个项目 | `python3 tools/bootstrap.py 剧本.txt` | 不要复制本仓库任何目录 |
| 升级模型 / 参数 | 不改文档，先跑 `higgsfield model list` | 文档会滞后，CLI 输出为准 |
| 升级依赖 | 见 [docs/09](docs/09-toolchain-setup.md) | 版本变化后重跑 `--doctor` 与 `--selftest` |

---

## 十、术语对照（影视行话 ↔ 仓库里的文件 / 工具）

流程描述用影视行话，文件名和命令保持原样（那是工具的实际名字）。两边对照如下：

| 影视行话（文档里这么写） | 对应的文件 / 工具 | 说明 |
|---|---|---|
| 场记台账 | `schema/`：`story_bible.json`、`assets.json`、`episodes.csv`、`shots.csv` | 现场只认这一份记录。任何阶段、任何一次重开对话，都从它读 |
| 场记核对（连戏检查） | `tools/check_consistency.py`（规则 R0–R21） | 自动查引用、编号、台词时长预算、字幕对齐、连戏与道具一致 |
| 验收关 | 阶段落点 G0–G7 | 八道：筹备关、剧本过会、定妆关、分镜关、过片关、配音关、定剪关、交片关。哪一关没过，不进下一道工序 |
| 停机待审 | 没有对应文件，是流程要求 | 要等作者或导演点头的地方：定妆定稿、过片抽查、定剪通看、批量开拍前报预算、未决问题 |
| 记入台账 | 写入 `schema/` 下的文件 | 每道工序干完就写一次，写一次跑一次场记核对 |
| 工序 | 流程编号 N0–N12 | 从丢进剧本到交片，拆出 13 道 |
| 过片 | 逐镜视觉十项质检（`qa_*`） | 每镜生成后逐项核对，不合格重拍，不带病进剪辑 |
| 定版 | `assets.json` 的 `status: locked`、素材 `_v00N` 命名 | 版本只追加不覆盖，随时能回到上一版 |
| 返工范围 | [docs/04 第五节](docs/04-risks-and-verification-gates.md) | 改了某处，要重做哪些镜头/资产 |
| 通告单 | [docs/05 第四节](docs/05-operations-and-orchestration.md) | 单集照单执行的命令清单 |
