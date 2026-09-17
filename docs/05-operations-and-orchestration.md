# 05 · 运行与编排

---

## 一、作业机制：为什么不会跑偏

整套方案只有一个机制，但它是地基：

```text
读 schema/ 文件 ──► 执行本阶段 ──► 结果回写 schema/ ──► 跑场记核对 ──► 进下一阶段
     ▲                                                              │
     └──────────── 只从文件读状态，不从上下文记忆读 ────────────────┘
```

每完成一步，写：**一次文件更新 + 一次校验**。

这条规则带来的直接好处：

| 场景 | 结果 |
|---|---|
| 对话被重开 / 上下文丢失 | 读 `schema/` 立刻恢复全部进度 |
| 隔几天再继续 | 不用回忆"上一集做到哪一镜了" |
| 想换机器 | 克隆仓库即可，状态全在文本里 |
| 想复盘"这镜头为什么这么生成" | `job_id` + `prompt_zh` + `version` 全在表里 |

## 二、会话纪律：看图有上限，视频阶段单独开工

上下文不是状态源，但它会被撑爆——**撑爆一次，这个会话就再也进不去**。本机实测（2026-09-16，`v-pr` 视频会话）：

| 事实 | 数据 |
|---|---|
| 一个塞满内联图的会话 | 单次请求 `input_tokens` 627,099，rollout 55.3MB / 2914 条 |
| 网关开始拒绝的请求体 | >40MB（40MB 放行，48MB 返回 `413 length limit exceeded`） |
| 罪魁祸首 | 原始定妆图/关键帧 4–9MB、QA 拼图 2MB；直接识图一张就能往上下文里注入 3MB |

两条硬纪律：

1. **看图一律走 `python3 tools/eye.py <图片或视频> [--at T] [--tiles 3x2]`。** 它把同一画面压到 300KB 以内（定妆图 64KB、9:16 拼图 156KB），判断身份、穿帮、字幕位置照样够用。禁止把 `keyframes/`、`assets/`、`clips/` 里的原始文件直接喂给识图，也禁止让 `look.py` 的全尺寸 PNG 进上下文。
2. **S4 视频生成单独开一个会话，一个会话只推一个阶段。** 出视频天然要反复看图，塞进"顺手改代码/写文档"的会话里必炸；重开会话的代价是零——状态全在 `schema/` 里，读一遍就接上（见第一节）。

   已经撑爆的会话**不要 fork**：fork 继承历史，第一条请求照样 413。直接开新会话，从 `schema/` 接手。

---

## 三、Codex 的两顶帽子

本流水线只需要一个执行者，但它需要切换两种工作模式。**关键是两种模式的产物都记入台账，不靠对话传递。**

| 模式 | 干什么 | 不该干什么 |
|---|---|---|
| **推理脑**（S1 / S3） | 读剧本，抽取实体与剧情节点，推导分集与单集时长，撰写分镜脚本与中文提示词，设计钩子 | 不碰 CLI、不判断生成结果好坏 |
| **执行手**（S0 / S2 / S4 / S5 / S6 / S7） | 读写 `schema/`、调 `higgsfield` CLI、上传与登记素材、用原生识图做视觉六项校验（素材先过 `tools/eye.py`）、跑 ffmpeg 剪辑、打包交付 | 不凭记忆断言"已经生成过了"，必须先读文件 |

切换点就是**验收关**：推理脑产出 → 场记核对通过 → 执行手开工 → 结果回写 → 推理脑读表继续。

---

## 四、单集通告单（照单执行）

（下面是 bash 写法。Windows PowerShell 里变量写成 `$P = "$PIPELINE_HOME\projects\{{项目名}}"`，
`python3` 换成 `python`，其余命令一致；装法与坑见 [11](11-windows-setup.md)。）

```bash
# 命令都在复用层根目录执行；P 指向项目实例（也可以是仓库外的路径）
PIPELINE_HOME=/Users/hanson/work/个人文档/v-pr/story-to-video-pipeline
P=$PIPELINE_HOME/projects/{{项目名}}

# ── 开工：先读状态，别靠记忆 ──────────────────────────
cd $PIPELINE_HOME
python3 tools/check_consistency.py --schema-dir $P/schema    # 必须 0 错误
jq '.meta' $P/schema/story_bible.json                        # 确认项目参数未变
higgsfield account status                                    # 确认额度

# ── S3 分镜 ─────────────────────────────────────────
# 产出 EP{{NN}} 的场次与镜头，写入 episodes.csv / shots.csv
python3 tools/check_consistency.py --schema-dir $P/schema    # 验收关 G3

# ── S4 逐镜生成 ─────────────────────────────────────
# 对 shots.csv 中 status=todo 的每一行：
#   1. 出关键帧 -> keyframes/
#   2. 挂载 CH/EN/ST + 首尾帧 -> 生成视频
#   3. job_id 回填 shots.csv
#   4. 视觉六项校验 -> 写 qa_* 字段
python3 tools/check_consistency.py --schema-dir $P/schema    # 验收关 G4

# ── S5 配音 ────────────────────────────────────────
higgsfield voices list --json
# 逐句 TTS -> audio/；回填 audio_duration_s
python3 tools/check_consistency.py --schema-dir $P/schema    # 验收关 G5

# ── S6 剪辑 ────────────────────────────────────────
# 拼接 -> 修首尾 -> 转场 -> 统一调色 -> 混音 -> 字幕
ffprobe 批量核对规格                         # 验收关 G6
higgsfield generate workflow reframe ...     # 出 9:16 抖音分发版

# ── S7 交付 ────────────────────────────────────────
# 成片 + 封面 + 资产清单 + 归档包
git add -A && git commit -m "EP{{NN}}: 通过全部验收关"
git tag ep{{NN}}-v001
```

批量生成时的并发建议：S2 出图与 S4 出视频可以并发提交，但**同一角色的镜头建议串行**（先确认第一镜没漂，再放量）。宁可慢一点，也别批量产出 20 条废片。

---

## 五、一次典型对话怎么发起

你只需要给 Codex 一个阶段指令，不需要复述上下文：

```text
【S1】读 project/raw/ 下的剧本，抽取五类实体写入 schema/story_bible.json。
      同时推导项目名、集数、单集时长，把推导依据写进 meta.derivation_notes。
      外观锚点必须可被图像检验。不确定的写进 open_questions，不要猜。

【S2】按 story_bible.json 出全部角色定妆图（三视图）与场景空镜，登记 assets.json。
      每张出完对着锚点自检，不合格重生成。

【S3】按 episode_plan 拆集，写入 episodes.csv 与 shots.csv。
      一镜只放一个主节拍，单镜 2-4s，主体放在中心安全区。跑场记核对到 G3 通过。

【S4】生成 EP{{NN}} 的全部镜头，逐镜做视觉六项校验，不合格就重生成，不要带 fail 过来。
```

---

## 六、装机与作业说明

### 环境要求

| 项 | 要求 |
|---|---|
| 操作系统 | macOS / Linux / Windows 10+（本机 macOS 已具备全部本地工具；Windows 装法见 [11](11-windows-setup.md)） |
| 必须安装 | `higgsfield` CLI（**已装 v1.1.25**）、`python3`、`ffmpeg`、`git` |
| 推荐安装 | `jq`、`ImageMagick` |
| 账号 | Higgsfield 账号（免费额度可跑生成；Soul 训练需 Basic 以上，本项目不用） |
| 密钥 | **无** |

### 首次装机

```bash
curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh
higgsfield auth login
higgsfield account status
higgsfield model list            # 核实现行模型，别照抄文档
```

Windows 换成 `npm install -g --allow-scripts=@higgsfield/cli @higgsfield/cli` + `higgsfield workspace set <id>`
（新机器第一次必须选工作区，否则 `account status` 报的是没选工作区而不是没登录）。逐条见 [11-windows-setup.md](11-windows-setup.md)。

### 目录约定

| 目录 | 写入者 | 是否入库 |
|---|---|---|
| `<项目>/schema/` | Codex | **入库**（场记台账） |
| `<项目>/docs/`（含 07 实测记录）+ `<项目>/README.md` | 人 / Codex | **入库** |
| `<项目>/project/raw/` | 人（只读） | 剧本入库 |
| `<项目>/project/work/` | Codex | 不入库 |
| `<项目>/project/delivery/` | Codex | 不入库（另走网盘 / OSS） |
| 复用层 `rules/` `tools/` `docs/01–06,08,09` `skills/` | 人 | **入库**，且**不复制进项目** |

### 留底策略

1. **`schema/` 是命根子**：每次提交推到远端仓库，它能让任何一台机器在几分钟内恢复全部状态。
2. **大文件用对象存储**：`project/work/` 与 `project/delivery/` 同步到网盘或 OSS，保持目录结构一致。
3. **归档包**：`archive_<PROJECT>_<YYYYMMDD>.tar.gz` 只含 `schema/`、`docs/`、提示词与资产索引，不含大文件，便于长期保存。

---

## 七、交付与归档规范

```
project/delivery/
├── EP01_16x9_v001.mp4        16:9 母版
├── EP01_9x16_v001.mp4        抖音分发版
├── EP01.srt                  字幕
├── cover_16x9.jpg            横版封面
├── cover_9x16.jpg            竖版封面
├── asset_manifest.md         资产清单（项目 / 系列 / 通用三档）
└── delivery_checklist.md     交付检查表
```

命名规则：`<集号>_<画幅>_v<版本>.mp4`，日期与生成来源记在 `schema/`，不塞进文件名，避免路径过长。
