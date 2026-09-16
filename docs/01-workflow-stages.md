# 01 · 工作流阶段说明

每个阶段固定五问：**输入 → 处理步骤 → 输出（落到哪个文件的哪个字段）→ 依赖 → 跑偏检查**。

> 路径相对于项目根目录。本项目画幅固定 `16:9`，语言纯中文，分发抖音。

---

## S0 · 项目初始化

| 项 | 内容 |
|---|---|
| **输入** | 剧本 txt 文件 |
| **处理步骤** | 1) **一条命令铺骨架**：`python3 tools/bootstrap.py <剧本.txt> -o <项目目录>`，它做四件事——剧本原样复制进 `project/raw/`（**只读，任何情况下不修改原文**）、由文件名推导项目名、sha256 记指纹到 `meta.script_sha256`（防剧本被悄悄改动后资产失配）、建 `project/work/{assets,keyframes,clips,audio,edit}` 与空 `schema/`（CSV 表头抄复用层，避免两处对不上）；2) 顺手跑 `python3 tools/bootstrap.py --doctor` 确认工具链与登录态 |
| **输出** | 项目目录骨架 + 空 `schema/`；`story_bible.json` 的 `meta` 段（项目名、剧本路径、指纹、日期）填写完成 |
| **依赖** | 本地：`python3`（脚手架用它写文件）；**不需要任何 API 或密钥** |
| **跑偏检查** | `python3 tools/check_consistency.py --schema-dir <项目>/schema --draft` **0 错误**（草稿模式只把"题材还没识别"提示成警告）；`git status` 确认 `project/raw/` 未被修改 |

> **命名约定（要给仓库上 GitHub 就照这个来）**：**剧本文件保留原文件名**（它承载剧名，是素材，不改成拼音）；**项目目录用英文 slug**，由 `-o` 指定，例如 `-o ../projects/zhuangyuan-ep01`；**剧名写进 `meta.project_name` 与项目自带的 `README.md`**。这样仓库里全是 ASCII 路径，点开又能看到中文剧名。

```bash
python3 tools/bootstrap.py --doctor                     # 工具链 / 登录态 / skills 体检
python3 tools/bootstrap.py 剧本.txt                       # 铺项目（含剧本指纹），默认落 projects/<项目名>/
python3 tools/check_consistency.py --schema-dir projects/<项目名>/schema --draft   # G0：应 0 错误
```

---

## S1 · 剧本解析与结构化

| 项 | 内容 |
|---|---|
| **输入** | `project/raw/*.txt` 全文 |
| **处理步骤** | 1) **题材与时代识别**：读剧本首行与关键段落，判定题材、时代、是否跨时代、服装考据方向、语体，写进 `meta.theme` 并附原文出处 `evidence`——**这一步不做，后面 28 条提示词里的"古装写实"就没有来源**；2) 全文通读，逐条抽取五类实体：**人物 / 物体 / 建筑与场景 / 风格 / 服装造型**（风格锚由第 1 步的题材与时代推导）；3) 抽取**时间线**（时间点、跨度、闪回与插叙标记）；4) 抽取**剧情节点**（钩子、转折、高潮、结尾）；5) 为每个实体分配 ID（规则见 [02-consistency-control.md](02-consistency-control.md)）；6) 每个实体写 3–6 条**外观锚点**，必须是**可被图像检验**的具体特征；7) 给每个角色标 **`asset_level`**（`full` 完整定妆 / `silhouette` 只需逆光剪影 / `none` 不建资产）与 **`voice_need`**（音色海选的依据，写清性别 / 年龄感 / 气质）；8) **推导分集方案**（见下）；9) 不确定的地方写进 `open_questions`，**不猜** |
| **输出** | `schema/story_bible.json`：`meta.theme`、`meta.inputs_from_author`、`characters[]`（含 `asset_level` / `voice_need`）、`props[]`、`environments[]`、`styles[]`、`wardrobe[]`、`timeline[]`、`plot_beats[]`、`episode_plan`、`open_questions[]` |
| **依赖** | Codex 自身的推理能力（长文本抽取）。**不需要任何外部 API 或密钥。** |
| **跑偏检查** | ① `meta.theme` 的题材与时代非空且能指回剧本原文（场记核对 R13）；② `meta.theme.era_main` / `era_cross` 必须能在 `timeline[].label` 里找到对应时间线；③ 剧本里出现过的每个专有名词都必须能在 `story_bible.json` 找到对应条目，用 `rg` 反查；④ 每个实体至少 3 条外观锚点；⑤ 每个出场角色标了 `asset_level` 与 `voice_need`；⑥ `open_questions` 必须为空或已逐条确认；⑦ 分集方案必须能覆盖剧本全文，无遗漏段落 |

### 项目名、集数、单集时长的推导规则

这三个值不预设，由 S1 从剧本本身推导，并写进 `story_bible.json > meta`：

| 值 | 推导方式 |
|---|---|
| `project_name` | 取剧本文件名（去扩展名）。若文件名无意义（如 `新建文本文档`），改用剧本首行标题 |
| `episodes_planned` | 优先按剧本自带的章节 / 分集标记切分；没有标记时，按**剧情节点密度**切分：每个钩子与转折之间为一集，单集保留 1 个进入钩子 + 1 个结尾钩子 |
| `episode_duration_target_s` | 优先采用剧本中明确写出的时长；没有则按该集镜头数与镜头时长汇总估算（插入 2–4s、明确动作 4–7s、持续表演 8–12s） |

推导结果连同**推导依据**一起写进 `meta.derivation_notes`，便于你复核与推翻。

### 外观锚点的写法

```text
不可检验：女主很时尚
可检验：  发型=黑色微卷长发披肩 / 上衣=米白色宽松针织衫 / 下装=深蓝直筒牛仔裤
          随身物=左手腕细银手镯 / 体态=走路时右肩略低 / 年龄感=22-25
```

```bash
jq -r '.characters[].name' schema/story_bible.json   # 与剧本里的人名对表
jq '.meta.derivation_notes' schema/story_bible.json  # 复核分集推导依据
```

---

## S2 · 设定一致性确认

| 项 | 内容 |
|---|---|
| **输入** | `story_bible.json` 的五类实体 |
| **处理步骤** | 1) 按 `asset_level` 分级出图：`full` 出**定妆图三视图**（正面半身 + 侧面 + 全身），**可选再补 3/4 左、3/4 右、略仰，凑成"多角度参考图集"**（官方 Soul 训练指南要求的就是多角度：front / 3-4 左 / 3-4 右 / 略俯仰，见 [docs/02 第七节](02-consistency-control.md)）；`silhouette` 只出**一张逆光剪影**（面部不可辨即可，验收标准是轮廓与光位，不是五官），`none` 不出图；2) 每个场景生成**空镜参考图**（无人物、纯环境、光照方向明确），**首选 `soul_location`**（官方面向无人空景的最强模型，0.12 积分/张）；多人多出入口的戏**可再出一张俯瞰空景当调度图**，只用于排机位与走位、不当作挂载参考；3) 生成**风格锚图**（一张抽象风格板，统一全片调性；提示词从 `meta.theme` 的题材 / 时代 / 服装方向推导）；4) 逐张按分级标准比对锚点，不合格重生成；5) 定稿资产登记进 `assets.json`，写 `sha256` + `job_id` + `anchor_file` |
| **输出** | `project/work/assets/` 下的定妆图与参考图；`schema/assets.json` |
| **依赖** | **Skills**：`higgsfield-generate`（出图）；`imagegen`（需要精细位图编辑时）。**API**：场景用 `higgsfield generate create soul_location`（0.12 积分/张），角色与带参考图的编辑用 `nano_banana_pro`（2 积分/张）。单价与档位门槛见 [docs/10](10-account-plans-and-credits.md) |
| **跑偏检查** | ① 每张定妆图对照锚点逐项打勾（发型 / 服装 / 道具 / 体态 / 年龄感 / 气质），任一项不符就重生成；② 同一角色三视图之间五官必须一致；③ 场景图必须无人；④ 定稿后 `sha256` 写入 `assets.json`，后续引用都校验哈希未变 |

> **模型 ID 更正（实测）**：CLI v1.1.25 的模型目录里**没有 `nano_banana_2`**，实际 ID 是 `nano_banana_pro`（Nano Banana Pro）。官方 skills 文档里的 `nano_banana_2` 是旧 ID，照抄会报 unknown model。**一律以 `higgsfield model list` 为准。**

> **关于 Soul**：本账号实测为 **basic 套餐**，Soul 训练其实可用（`text2image_soul_v2`）。当前先用"定妆图三视图"锁定，等成片验证出一致性不足时，再把重点角色的 `identity_mode` 改为 `soul` 做升级重生成，资产 ID 不变。

```bash
higgsfield generate create nano_banana_pro \
  --prompt "{{角色外观锚点拼接成的中文提示词}}，角色设定图，正面半身，纯色渐变背景" \
  --aspect_ratio 16:9 --resolution 2k --wait --json
```

---

## S3 · 分集与分镜

| 项 | 内容 |
|---|---|
| **输入** | `story_bible.json`（含 `episode_plan`） |
| **处理步骤** | 1) **分集**：按 S1 的推导方案落表，每集留一个结尾钩子，写入 `episodes.csv`；2) **分场**：每集拆场次（每场一个地点 + 一个时间状态），写 `scene_id` 与 `script_ref`；3) **分镜**：每场拆镜头，**一个镜头只放一个主节拍**，单镜 2–4s（插入 / 反应）、4–7s（明确动作）、8–12s（持续表演）；4) 每镜填齐时长、景别 Z、运镜、**姿态起止、位置起止、朝向、视线**、动作起止、情绪起止、**`face_scale` 面部占比、`micro_beats` 节拍数**、**本镜道具清单、物理约束**、参考资产、中文提示词——**`face_scale` 与 `micro_beats` 要在写分镜时一次填完**，它们是 ME-006 / ME-009 的判据，空着就只能等镜头开工后才被拦下来；5) **按中心安全区构图**（见 02 文档），保证横转竖不丢主体；6) 检查相邻镜头运镜方向不冲突、轴线不跳 |
| **输出** | `schema/episodes.csv`、`schema/shots.csv` |
| **依赖** | Codex 自身推理能力；**Skill**：`seedance-prompt-skill`（运镜四维编码 Z/Y/X/F、25 格流水线、六套剪辑公式，见 03 文档）。**不需要任何外部 API 或密钥。** |
| **跑偏检查** | ① `script_ref` 覆盖率 100%；② 每镜 `refs` 里的资产 ID 必须存在于 `assets.json`；③ **台词时长预算**：`镜头时长 ≥ 台词字数 ÷ 4.4 + 0.5s`，超了就拆镜 / 精简台词 / 延长镜头（场记核对 R14，配音前就能拦住）；④ 镜头时长求和与单集目标偏差超 10% 需说明（R17，同时校验 `episodes.csv` 的 `shot_count` / `est_duration_s` 与实际分镜一致）；⑤ 相邻镜头不得连续 3 镜使用同一 Z 值（R18）；⑥ 每个镜头必须挂风格锚 `ST-###`（R19）；⑦ 每个镜头的主体落在中心安全区内；⑧ **同一批出镜角色的相邻镜头，姿态必须接得上**（R20 校验 `pose_end` → 下一镜 `pose_start`；缺 `pose_*`/`position_*`/`facing` 时对已开工镜头告警）；⑨ 物理约束已写、道具清单已列 |

关键约束（有实测数据支撑）：一镜塞太多表情节拍，模型会向"平均运动"收敛把表情全部抹平。同一场震惊戏的对照实验：单镜头 7 秒塞 9 个节拍，情绪峰值 PSNR 37–42 dB（等于定版帧，脸完全没动）；拆成三颗 2–3 秒各一个主节拍，22–23 dB（表情全部到位）。**拆镜头本身，就是表演。**

---

## S4 · 视频生成

| 项 | 内容 |
|---|---|
| **输入** | `shots.csv` 中 `status=todo` 的行与对应参考资产 |
| **处理步骤** | 1) **先出关键帧**：为每镜生成首帧，关键镜再生成尾帧，登记到 `project/work/keyframes/`；2) **再出视频**：首尾帧夹逼 + 角色 / 场景 / 风格参考图一起挂载（顺序见 02 文档）；3) 逐镜生成，`job_id` 回填 `shots.csv`；4) 生成后立刻做视觉六项校验，不合格重生成，**不将就**；5) 通过的片段归档为 `project/work/clips/<shot_id>_v001.mp4` |
| **输出** | `project/work/keyframes/*.png`、`project/work/clips/*.mp4`；`shots.csv` 的 `job_id` / `status` / `qa_*` |
| **依赖** | **Skill**：`higgsfield-generate`；**API**：`higgsfield generate create seedance_2_0 …`（**参数按档位给**：Basic 档只能 `--mode fast`（限 480p/720p）或用 `seedance_2_0_mini`；完整 2.0 std / 1080p 与 2.5 需 Pro，见 [docs/10](10-account-plans-and-credits.md)）、`higgsfield generate workflow draw_to_video`（单帧穿帮修复）；可选 `higgsfield generate create brain_activity`（钩子评分） |
| **跑偏检查** | 每镜按视觉十项核对：① 身份 ② 服装道具 ③ 场景环境 ④ 光线色温 ⑤ 屏幕方向与轴线 ⑥ 画幅与时长 ⑦ 安全区 ⑧ 跨镜连贯 ⑨ 物理合理 ⑩ 道具一致。任一项不符则 `qa_*=fail` 并重生成。用 Codex 原生识图完成，不额外调 API；**但素材必须先过 `python3 tools/eye.py`（≤300KB JPEG），禁止把 `keyframes/`、`assets/` 的 4–9MB 原图直接塞进上下文**（成因与实测见 [05 第二节](05-operations-and-orchestration.md)）。逐项判据与修复决策树见 [06-continuity-and-physics-checklist.md](06-continuity-and-physics-checklist.md) |

```bash
higgsfield generate create nano_banana_pro \
  --prompt "{{镜头画面描述}}，16:9 横版，主体位于画面中央安全区，{{风格锚点}}" \
  --image ./project/work/assets/CH-001_v001.png \
  --aspect_ratio 16:9 --resolution 2k --wait --json

higgsfield generate create seedance_2_0 \
  --prompt "{{动作与运镜描述}}" \
  --image ./project/work/assets/CH-001_v001.png \
  --image ./project/work/assets/EN-001_v001.png \
  --image ./project/work/assets/ST-001_v001.png \
  --start-image ./project/work/keyframes/EP01-SC02-SH003_v001.png \
  --duration 6 --resolution 1080p --aspect_ratio 16:9 --wait --json
```

> 本项目主力视频模型为 `seedance_2_0`：它是当前 CLI 文档中确认存在、且同时支持多图参考（最多 9 张，含首尾帧）与自带音频生成的模型。对白镜头加 `--generate-audio true` 即可让口型与台词一起生成。若 `higgsfield model list` 确认 `seedance_2_5` 存在，可整体升级。

---

## S5 · 配音与音频

| 项 | 内容 |
|---|---|
| **输入** | `shots.csv` 中带台词的镜头、`story_bible.json` 的角色设定 |
| **处理步骤** | 1) `higgsfield voices list` 列音色，**每个角色固定一个 `voice_id` 并写进 `assets.json`**（音色也是资产）；2) 逐句生成台词音轨；3) 旁白单独一条轨；4) 按镜头时长裁剪或微调语速，保证台词落在对应镜头内；5) 环境音与 BGM 单独生成并记录 |
| **输出** | `project/work/audio/<shot_id>_<line_no>_v001.mp3`、`narration.mp3`、`sfx/*`；`assets.json` 的 `voices[]` |
| **依赖** | **Skill**：`higgsfield-generate`；**API**：`higgsfield voices list --json`、`higgsfield generate create text2speech_v2 --variant <elevenlabs\|minimax\|seed_speech\|vibe_voice\|cozy_voice> --voice_type preset --voice_id <id>`、`higgsfield generate create seed_audio`（环境音 / 音效）、`higgsfield generate workflow voice-change`（换音色） |
| **跑偏检查** | ① 同一角色的所有台词必须是同一个 `voice_id`（场记核对检查）；② 每条台词时长不超过对应镜头时长；③ 口型见下方策略 |

口型策略：当前工具链**没有独立的 lip-sync 模型**。两条可行路线：

1. **生成时带音频**（`kling3_0 --sound on` / `wan2_7`）——口型质量最好，但台词必须写在提示词里，适合对白戏。
2. **先出无声镜头再配音**——灵活，但口型对不上，适合**旁白 / 独白型**。

S3 分镜阶段就按镜头性质选好路线，写进 `shots.csv` 的 `model` 列，不要留到剪辑才发现。

本项目语言为**纯中文**，不涉及多语言配音，因此不做 `dubbing` 环节。

---

## S6 · 剪辑与成片

| 项 | 内容 |
|---|---|
| **输入** | `project/work/clips/*.mp4`、`project/work/audio/*`、`shots.csv`（镜头顺序与时长） |
| **处理步骤** | 1) 按 `shot_id` 顺序拼装（`ffmpeg concat`）；2) **保持 `shots.csv` 的单镜时长**：`duration_s` 是字幕、台词与成片的共同时间基准，剪辑不得悄悄改变它（AI 运镜起止不稳时裁掉的量必须回写 `duration_s`，否则字幕会整体错位——场记核对 R16 会直接报出来）；3) 按剪辑公式组织节奏（呼吸式 / 心跳式 / 海浪式 / 子弹时间 / 脉冲式 / 静默锤击）；4) 转场以硬切为主，动作连贯处用匹配剪辑；5) **统一调色**，以风格锚图为基准逐段校准；6) 混音优先级：台词 > 环境音 > BGM；7) 字幕烧录或外挂 SRT（改过 `duration_s` 必须重跑 `python3 tools/make_srt.py`）；8) 片尾定格 + 钩子；9) **生成 9:16 分发版**（抖音用） |
| **输出** | `project/work/edit/EP{{NN}}_16x9_v001.mp4`（母版）、`EP{{NN}}_9x16_v001.mp4`（分发版）、`EP{{NN}}.srt` |
| **依赖** | **Skill**：`ffmpeg-skill`（42 个剪辑/交付工具，本项目不自造 ffmpeg 命令）+ `higgsfield-generate`；**本地**：`ffmpeg-full 9.0.1`（**必须**——普通 ffmpeg 不含字幕/文字滤镜）、`python3`、`ImageMagick`。调用规范见 [rules/FF-editing-and-delivery.md](../rules/FF-editing-and-delivery.md) |
| **跑偏检查** | ① `check.py --platform tiktok` 必须 **0 failed**（FF-006）；② 复盘 `tools/eye.py` 出的 QA 拼图，9:16 分发版主体未被裁（FF-008 / FF-009）；③ 无黑帧、无音画不同步；④ 时长符合单集目标；⑤ 抽 5 帧与风格锚图比对色温偏差 |

```bash
S=~/.agents/skills/ffmpeg-skill
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"     # FF-001：不加这行字幕与文字叠加全废

# 1) 先读规格再规划（FF-002）
python3 $S/scripts/probe.py project/work/edit/EP01_16x9_v001.mp4

# 2) 横转竖 + 定帧率；主体偏心时加 --crop-x（FF-009）
python3 $S/scripts/fit.py project/work/edit/EP01_16x9_v001.mp4 \
  --aspect 9:16 --fit crop --width 1080 --fps 24 \
  -o project/work/edit/EP01_9x16_v001.mp4

# 3) 响度归一化，真峰值留 0.5dB 余量（FF-007）
python3 $S/scripts/loudness.py project/work/edit/EP01_9x16_v001.mp4 \
  -I -14 --tp -1.5 --sample-rate 48000 \
  -o project/work/edit/EP01_9x16_v002.mp4

# 4) 字幕（SRT 由 tools/make_srt.py 从 shots.csv 生成）
python3 tools/make_srt.py
python3 $S/scripts/caption.py project/work/edit/EP01_9x16_v002.mp4 \
  --mode burn --srt project/work/edit/EP01.srt --platform tiktok \
  -o project/work/edit/EP01_9x16_v003.mp4

# 5) 交付合规检查（必须 0 failed）与看图验收
python3 $S/scripts/check.py project/work/edit/EP01_9x16_v003.mp4 --platform tiktok
python3 tools/eye.py project/work/edit/EP01_9x16_v003.mp4 --tiles 3x2   # 出 ≤300KB 拼图再看，别喂原片
```

---

## S7 · 交付与归档

| 项 | 内容 |
|---|---|
| **输入** | 成片（两个版本）、字幕、封面、全部 `schema/` |
| **处理步骤** | 1) 成片按命名规范落 `project/delivery/`；2) 生成封面（`higgsfield-youtube-thumbnail`，同时出 16:9 与 9:16）；3) 导出**资产清单**（标注哪些资产可跨集 / 跨项目复用）；4) 生成**归档包**（`schema/` + 提示词 + 资产索引，不含大文件）；5) 打 git tag |
| **输出** | `project/delivery/` 完整交付物 + `archive_<PROJECT>_<YYYYMMDD>.tar.gz` |
| **依赖** | **Skill**：`higgsfield-youtube-thumbnail`；**本地**：`tar`、`git tag` |
| **跑偏检查** | ① 交付物命名与清单一致；② 归档包解压后能通过 `tools/check_consistency.py`；③ 所有 `status=done` 的镜头 `qa_identity=pass` |
