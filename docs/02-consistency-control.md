# 02 · 一致性控制

整份文档只回答一件事：**怎么让第 37 个镜头看起来和第 1 个镜头是同一部戏。**

---

## 一、五类资产与 ID 规则

一致性从"每样东西都有唯一名字"开始。任何会在画面上重复出现的东西，必须先有 ID 才能进分镜。

| 前缀 | 类型 | 说明 | 示例 |
|---|---|---|---|
| `CH-###` | character | 人物（含配角、群演模板） | `CH-001` |
| `PR-###` | prop | 物体、道具、随身物 | `PR-007` |
| `EN-###` | environment | 建筑、场景、地点 | `EN-003` |
| `WD-###` | wardrobe | 服装造型（同一角色不同造型分不同 ID） | `WD-002` |
| `ST-###` | style | 视觉风格锚（色调、渲染倾向、镜头质感） | `ST-001` |
| `VC-###` | voice | 角色音色绑定 | `VC-001` |

编号规则：**三位零填充、全局唯一、永不复用**。资产废弃时标 `status: archived`，不删行，也不把 ID 让给新资产。

---

## 二、三级锁：从文字到图到模型

单个资产要经历三次收紧，每一级都记入台账留痕：

```text
① 文字锁   story_bible.json 里的 3-6 条外观锚点（可被图像检验）
               ↓ 生成定妆图并逐条比对
② 图像锁   assets.json.anchor_file + sha256（定稿参考图，后续全部复用同一张）
               ↓ 真人脸额外训练
③ 模型锁   assets.json.soul_reference_id（Soul 训练的 reference_id）
```

**关键：一致性来自"反复引用同一张参考图"，不来自"希望模型自己记住角色"。** 任何绕开 `anchor_file`、直接用文字提示词描述角色的做法都会漂。

| 场景 | 锁定方式 | 注意 |
|---|---|---|
| **本项目：全部角色** | 定妆图三视图作参考图集，每个镜头挂载 | 无训练成本，但一致性弱于 Soul，S2 验收与 S4 漂移检测需更严格 |
| 升级选项（待购 Basic 后） | `higgsfield soul-id create` 训练，5–20 张照片（8–12 最佳） | 需 Basic 以上套餐；15–45 分钟；资产 ID 不变，做一次升级重生成 |
| 群演 / 背景人 | 不建 ID，直接写"背景人群虚化" | 避免引入额外一致性负担 |

---

## 三、镜头编号规则

```text
EP{两位}-SC{两位}-SH{三位}

EP01-SC02-SH003
 │     │     └─ 镜头序号，全场次内三位递增
 │     └─────── 场次序号，全集内两位递增
 └───────────── 集序号
```

1. 镜头号**一经分配不再变更**。删除镜头时保留空号，**不重排**，否则已生成资产、剪辑表、映射表会全部错位。
2. 同一镜头的多次生成用 `_v001`、`_v002` 区分，通过的版本号写进 `shots.csv.version`。
3. 素材命名：`<shot_id>_v<###>_<yyyy-mm-dd>.<ext>`，例：`EP01-SC02-SH003_v002_2026-09-16.mp4`。

---

## 四、分镜与剧本的双向映射

防跑偏最有效的机制：**每个镜头都必须能指回剧本，每一段剧本都必须有镜头覆盖。**

| 方向 | 落点 | 检查方式 |
|---|---|---|
| 分镜 → 剧本 | `shots.csv.script_ref`（剧本行号或段落 ID） | 覆盖率必须 100% |
| 剧本 → 分镜 | `episodes.csv.script_ref` 段落区间 | 剧本段落必须被至少一个镜头覆盖 |
| 场次 → 环境 | `episodes.csv.location_env_id` → `assets.json` | 引用必须存在 |
| 镜头 → 资产 | `shots.csv.refs`（`CH-001;EN-003;ST-001`） | 引用必须存在 |
| 台词 → 音色 | `shots.csv.voice_id` = 该角色在 `assets.json.voices` 绑定的 `VC-###` | 同角色必须同音色 |

以上五条全部由 `tools/check_consistency.py` 自动校验。

---

## 五、每镜参考图挂载契约

生成任何镜头时，参考图挂载顺序固定，不允许每次随意：

```text
1. 角色定妆图   CH-###（每个出场角色一张，多人镜按台词量降序）
2. 关键道具     PR-###（仅当道具是本镜叙事焦点，如刀的特写）
3. 场景参考图   EN-###
4. 风格锚图     ST-###（每个镜头都挂，防色调漂移）
5. 服装造型     WD-###（仅当同一角色在本集内需要换装）
6. 首帧 / 尾帧  本镜关键帧（用于动作夹逼）
```

**槽位上限**：总张数不得超过所选模型的 `image_references` 上限。`seedance_2_0` 为 9 张（含首尾帧）。本片 EP01 最坏情况是三人同框（CH×3 + EN + ST = 5 张，加首尾帧 7 张），仍在安全区。第 1、3、5 项按需挂载，不是每镜都要挂满。

对应到命令：

```bash
higgsfield generate create seedance_2_0 \
  --prompt "{{中文提示词}}" \
  --image ./project/work/assets/CH-001_v001.png \
  --image ./project/work/assets/EN-001_v001.png \
  --image ./project/work/assets/ST-001_v001.png \
  --start-image ./project/work/keyframes/EP01-SC02-SH003_v001.png \
  --duration 6 --resolution 1080p --aspect_ratio 16:9 --wait --json
```

> 模型选择说明：`seedance_2_0` 是当前 CLI 文档中确认存在、且同时支持多图参考（最多 9 张）与自带音频生成的模型，因此作为本片主力。`seedance_2_5` 在官方 skills 里被标为默认视频模型但 CLI 的 `MODELS.md` 查不到，**必须以 `higgsfield model list` 的实际输出为准**；若确认存在，可整体升级。

> **待实测**：`seedance-prompt-skill` 使用即梦的 `@图片1` 命名引用语法，Higgsfield CLI 走的是有序 `--image-references` 传参。**挂载顺序即引用顺序**是本方案的约定，`@图片N` 语法能否直接透传需要实测确认（见 [04-risks-and-verification-gates.md](04-risks-and-verification-gates.md) 的 R-01）。

---

## 六、中心安全区（16:9 母版 → 9:16 分发）

本项目用 16:9 拍摄，用 9:16 上抖音。横转竖会裁掉左右两侧各约 22% 的画面，所以**构图从 S3 分镜阶段就要按安全区来**：

```text
16:9 画框（1920×1080）
┌──────────────────────────────────────┐
│  两侧可牺牲区  ┌──────────────┐  两侧 │
│  （环境、背景、│  中心安全区  │  可牺牲│
│   虚化人群）   │  9:16 输出区 │   区   │
│                │  约 607×1080 │       │
│                └──────────────┘       │
└──────────────────────────────────────┘
        ← 横向保留中间约 56% 宽度 →
```

规则：

1. **人物主体、关键道具、面部特写、字幕**必须落在中心安全区内。
2. 两侧只放可牺牲的信息：环境、虚化人群、氛围光。
3. 多人同框时，关键人物沿中心轴纵向或紧凑排列，**不要横向摊开**（横排的人在竖版里会被裁掉）。
4. 提示词里显式写明"主体位于画面中央、两侧留出可裁切空间"。
5. S6 输出 9:16 分发版后**必须复检**：主体没被裁、字幕完整、无关键信息缺失。

---

## 七、场景与角色要不要"俯视图"？—— 查证结论

> 起因：一个常见说法是"场景和人物的参考图，加个俯视图会更好"。查了一圈一手来源，结论是**要拆成两件事看**，别混。

### 1. 角色：要的是**多角度**，不只是俯视 —— 有一手依据

官方 Soul ID 训练的照片指南写得最直白（`higgsfield-skills/higgsfield-soul-id/references/photo-guide.md`）：

> Variety: Higher variety = better identity capture.
> - **Multiple angles: front, 3/4 left, 3/4 right, slight up/down.**
> - Different lighting / different expressions / different distances (head shot → full body)
> Avoid: **Same pose repeated.**

同文件还给了量：**最少 5 张、最多 20 张，8–12 张是甜点区**。

行业侧对得上：model sheet（角色设定图）的定义就是"把角色的头与身体**画在多个角度**（这个过程叫 model rotation），并附手、脚与几种基础表情"（[Model sheet · Wikipedia](https://en.wikipedia.org/wiki/Model_sheet)）。

**落到本项目**：现有做法是"定妆图三视图"（正面半身 + 侧面 + 全身），方向正确；如果要再堵漂移，加的是**3/4 侧与略俯/略仰**这两种角度，而不是"俯视图"这一个。参考图上限足够：`nano_banana_pro` 最多 **14 张**参考图（`higgsfield-generate/references/media-inputs.md:37`），一张定妆图 + 两个 3/4 侧 + 一个仰角完全放得下。

### 2. 场景：俯视图不是**参考图**规范，但它是**调度图**的正解 —— 用途不同

官方对"场景该用什么"给的答案是**选模型**，不是选视角：

> **Locations / environments / no-people scenes → Soul Location. Best in class — nothing else matches.**（`higgsfield-generate/references/model-catalog.md:26`、`:110`）

社区侧的中文短剧 skill（`shuohao-skills` 的 `novel-art`）把场景资产的 11 道质量门定在：一致性锚点 3–5 条、**光照时段变体**、**空景**（无人无手）、变体机制、道具状态变体、**尺度参照**、白底可抠——**也没有"俯视图"这一条**。

那"俯视图"在哪儿有用？在**影视的场面调度**里。previsualization 的经典定义就是"在实拍前可视化场景、规划**机位角度与 staging**"（[Previsualization · Wikipedia](https://en.wikipedia.org/wiki/Previsualization)），blocking 是"演员位置的精确排布"（[Blocking · Wikipedia](https://en.wikipedia.org/wiki/Blocking_(stage))），而俯视的平面图（floor plan / overhead plan）是这套调度工作的载体。

**关键区别**：平面调度图是**给人看的**——用来推演机位与走位、防越轴；**生成模型不吃它**（它只吃参考图与首尾帧）。把平面图当参考图挂上去，模型不会因此更懂空间。

### 3. 怎么落地（三条建议，按性价比排）

| 建议 | 怎么做 | 为什么 / 成本 |
|---|---|---|
| ① **角色出多角度参考图集** | 定妆图之外补 3/4 左、3/4 右、略仰三张，一起挂载 | 官方训练指南的同一逻辑：角度多样性 = 身份捕获更稳；出图 0.12–2 积分/张 |
| ② **场景出一张俯瞰空景当"调度图"** | `soul_location` 出 21:9 或 1:1 俯瞰空景，**只用于分镜排机位与走位**，不当作挂载参考 | 官方面向无人空景的最强模型，**0.12 积分/张**；多人同框、多个出入口的戏收益最大 |
| ③ **一致性照旧靠锚点 + 同图挂载** | 每镜挂同一张场景空景 + 风格锚；走位用 `position_start/end`、`axis_note`、`props_in_frame` 写成文字 | 这是唯一被验证有效的机制（docs/02 第三节），俯瞰图替代不了它 |

**别做的**：为每个场景都出俯视图并指望模型据此保持空间一致——没有依据；同一空间里如果一定要挑一个"多出来的角"，优先补**反打角度**（正打/反打各一张），它直接决定越轴是否穿帮。

---

## 八、漂移检测：视觉十项

每个镜头生成后，用 Codex 原生识图对照下列十项逐项核对，结果写回 `shots.csv`：

| # | 检查项 | 判定依据 | 字段 |
|---|---|---|---|
| 1 | 身份 | 五官、脸型、发型与 `anchor_file` 一致 | `qa_identity` |
| 2 | 服装道具 | 与 `WD-###` / `PR-###` 定义一致，同一场戏内不得换装 | `qa_wardrobe` |
| 3 | 场景环境 | 与 `EN-###` 的布局、材质、陈列一致 | `qa_scene` |
| 4 | 光线色彩 | 光源方向、色温、对比度与 `ST-###` 一致 | `qa_light` |
| 5 | 屏幕方向 | 人物朝向、进出画方向符合轴线规则 | `qa_axis` |
| 6 | 画幅时长 | `{{画幅}}`、时长符合 `shots.csv` 规定 | `qa_spec` |
| 7 | 安全区 | 主体与字幕落在中心安全区内，横转竖不会被裁 | `qa_safe_area` |
| 8 | 跨镜连贯 | 姿态、画内位置、朝向与上一镜末帧能直接接上 | `qa_continuity` |
| 9 | 物理合理 | 无穿透 / 碰撞 / 反重力 / 软体失真，动作有收束 | `qa_physics` |
| 10 | 道具一致 | 道具数量、位置、形态与 `props_in_frame` 一致 | `qa_props` |

任一为 `fail` 则该镜头 `status=regen` 并重生成。**不允许带着 fail 进入剪辑阶段。**

这十项背后的完整排错手册（症状 → 预防 → 检查帧 → 修复决策树）见 [06-continuity-and-physics-checklist.md](06-continuity-and-physics-checklist.md)。

---

## 九、版本管理与留痕

| 资产类型 | 管理方式 |
|---|---|
| 文本资产（`schema/*.json`、`*.csv`、`docs/`、提示词） | `git` 直接管理，每次资产定稿或镜头通过都提交一次，commit message 用 `<asset_id>: <动作>` |
| 大文件（图 / 视频 / 音频） | 不入 git。用文件命名 + `assets.json.sha256` 留痕；需要版本仓库时用 `git-lfs` 或 DVC |
| 生成参数 | **永不覆盖**。每次生成在 `assets.json` 或 `shots.csv` 追加一行，保留 `job_id` 与时间戳 |

```bash
git init
printf 'project/work/\nproject/delivery/\n.env\n' >> .gitignore
git add schema docs tools .gitignore
git commit -m "S0: 项目初始化"
```

原则：任何"这个镜头之前那版更好"的诉求，都必须能靠 `_v00N` 找回。删文件等于删证据。

---

## 十、跨集复用的资产

交付时把资产分三档，写进 `project/delivery/asset_manifest.md`：

| 档位 | 含义 | 例子 |
|---|---|---|
| 项目资产 | 仅本项目可用 | 主要角色定妆图、专属场景 |
| 系列资产 | 同系列其他剧集可复用 | 通用街景、通用风格锚图、配角 |
| 通用资产 | 跨项目可复用 | 风格锚图、音色绑定、通用道具 |
