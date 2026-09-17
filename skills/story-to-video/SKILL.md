---
name: story-to-video
version: 1.0.0
description: 剧本 / 小说到成片的影视制作流水线编排，短剧、网剧、影视、动画、动漫、漫剧一视同仁。当用户丢进一份剧本或小说 txt、或说「跑流水线」「继续做下一集」「从剧本出成片」「这部做到哪了」时使用。按 N0–N12 推进：题材与时代识别 → 人物与服装 → 场景与物件 → 音色 → 资产定稿 → 分集分镜 → 视频生成 → 配音 → 字幕 → 剪辑交付；每步记入台账 schema/ 并跑场记核对，在人工验收关停下等作者。
---

# 影视制作流水线（编排层 · 短剧 / 影视 / 动漫通用）

## 分层：先认清东西在哪

| 层 | 位置 | 内容 | 可变性 |
|---|---|---|---|
| **复用层** | `$PIPELINE_HOME`（macOS 上默认 `/Users/hanson/work/个人文档/v-pr/story-to-video-pipeline`；Windows 上就是本仓库路径，例：`C:\Users\<用户名>\aiwork\story-to-video-pipeline`） | `rules/`、`tools/`、`docs/01–06,08–11`、本 skill | 装一次，**所有内容形态共用**（短剧 / 网剧 / 影视 / 动画 / 动漫 / 漫剧）；改这里等于改流程；**不放任何具体剧本的数据** |
| **项目层** | `$PIPELINE_HOME/projects/<项目名>/`（`-o` 也可放仓库外） | `schema/`（场记台账）、`project/`（素材）、`README.md`（**项目状态写这里**）、`docs/07`（项目实测） | 每个剧本一套，互不影响 |

**不把 rules / tools / docs 复制进项目**——复制就是分叉，两处必然对不上。命令用 `--schema-dir <项目>/schema` 指到项目（只有一个项目时可省略，工具会自动选中）。

**项目状态严禁写进复用层**：进度、缺口、待拍板项一律写进该项目的 `README.md`。

## 开工：三种入口

```bash
PIPELINE_HOME=/Users/hanson/work/个人文档/v-pr/story-to-video-pipeline        # 复用层（用户自定义时用 $PIPELINE_HOME）

# ① 新剧本：铺项目骨架（剧本入库 + 指纹 + 空 schema），然后走 N1
python3 $PIPELINE_HOME/tools/bootstrap.py <剧本.txt>              # 默认落在 $PIPELINE_HOME/projects/<项目名>/
python3 $PIPELINE_HOME/tools/bootstrap.py <剧本.txt> -o <目录>     # 也可放仓库外

# ② 已有项目接着做：先读红灯，不要凭记忆猜进度
python3 $PIPELINE_HOME/tools/check_consistency.py --schema-dir <项目>/schema

# ③ 只体检环境（工具没装齐、没登录，先跑这个）
python3 $PIPELINE_HOME/tools/bootstrap.py --doctor
```

Windows（PowerShell）：`python3` 换成 `python`，`$PIPELINE_HOME` 换成仓库绝对路径（如 `C:\Users\<用户名>\aiwork\story-to-video-pipeline`），路径分隔符用 `\`；其余步骤一致。换机装什么见 [docs/11](../../docs/11-windows-setup.md)。

接手任何项目的第一件事都是 ②：**状态只在 `schema/` 里**，对话里的记忆不算数。

## 工序：读什么 → 写什么 → 跑什么

| 工序 | 产出（记入台账） | 必读 | 跑什么 |
|---|---|---|---|
| N0 初始化 | 目录骨架、`meta.script_sha256` | docs/01 S0 | `bootstrap.py <剧本>` |
| N1 题材与时代 ★ | `meta.theme`（题材 / 时代 / 跨时代 / 服装方向 / `evidence` 原文出处） | docs/01 S1、**skill `novel-outline`** | 场记核对 R13 |
| N2 人物与服装 | `characters[]`（`appearance_anchors` 3–6 条可检验 + `asset_level` + `voice_need`）、`wardrobe[]` | docs/01 S1、schema/README、**skill `novel-characters`** | G1 |
| N3 场景与物件 | `environments[]`（含 `time_of_day` 与光照方向）、`props[]` | 同上 + **skill `novel-art`** | G1 |
| N4 剧情节点与分集 | `plot_beats[]`、`timeline[]`、`episode_plan` | 同上 + **skill `novel-outline`** | G1 |
| N5 音色选型绑定 | `assets.json.voices[]`，回填 `characters[].voice_id` | rules/VD-005、docs/01 S5、**skill `novel-characters` 的音色提示词** | VD-001 一角色一音色 |
| N6 资产定稿出图 | `assets.json.assets[]`（`anchor_file` + `sha256` + `job_id`） | docs/01 S2、docs/02 第二/七节、docs/10（积分与档位）、`novel-characters` / `novel-art` 的设定图 | **G2 人工验收关** |
| N7 分集与分镜 | `episodes.csv`、`shots.csv` | docs/01 S3、docs/02 第五/六节、**`novel-script`（台词与语速折算）+ `novel-storyboard`（段/分镜/分镜图）**、seedance-prompt-skill | G3（含台词预算 R14） |
| N8 视频生成 | `keyframes/`、`clips/`、`job_id`、`qa_*` 十项 | docs/01 S4、docs/06、rules/ME、rules/PH | **G4 抽查** |
| N9 配音执行 | `audio/*.mp3`、回填 `audio_duration_s` | docs/01 S5、rules/VD | G5 |
| N10 字幕 | `project/work/edit/EP**.srt` | rules/VD-003/004 | 场记核对 R16 |
| N11 剪辑与成片 | 16:9 母版 + 9:16 分发版 | docs/01 S6、rules/FF | **G6 通看** |
| N12 交付归档 | `project/delivery/`、资产清单、归档包 | docs/01 S7、rules/COMP | `--delivery` 审计 |

工序依赖总图与并行关系见 `docs/08`；验收关定义见 `docs/04`。**N1–N4 可并行，N5 与 N6 可并行，N9 不等 N8。**

### 用 `novel-*` 五件套（shuohao-skills）跑前段

装好的话，N1–N7 的"想素材"这一步直接交给它们，它们自带几十道脚本质量门（比人肉检查硬）：

```text
小说/剧本 → novel-outline（大纲五件套）→ novel-characters（角色+音色）∥ novel-art（场景+道具）
          → novel-script（剧本/台词/语速折算）→ novel-storyboard（分镜 + 分镜图）
```

产物是 `outline.json` / `cast.json` / `art.json` / `script.json` / `storyboard.json`，**不是本项目的 `schema/`**。所以中间必须有一步**转录**（写一次性脚本，别手抄）：json → `story_bible.json` / `episodes.csv` / `shots.csv` / `assets.json`，转完立刻跑 `check_consistency.py`；两套编号只保留 schema 一套。它们管"该有什么"，本流水线管"状态与验收"。

## 三条硬规则

1. **以场记台账为准**：状态只从 `schema/` 读。禁止凭上下文断言「这镜已经生成过了」。
2. **改完就跑场记核对**，修到 0 错误再进下一步；有 `open_questions` 未决时先问作者，不要猜。
3. **看图一律走 `python3 tools/eye.py <素材> [--at T] [--tiles 3x2]`**（压到 ≤300KB）。把 `assets/`、`keyframes/`、`clips/` 的原图直接喂进上下文会撑爆会话（实测 413，见 docs/05 第二节）。

## 必须停下来问人

| 停机待审 | 为什么 |
|---|---|
| **G2 定妆图 / 剪影图定稿** | 视觉一致性的地基，Agent 自检不能替代人眼；`asset_level=full` 逐条对锚点打勾 |
| **G4 关键镜抽查** | 每集抽 3–5 个镜头给作者看 |
| **G6 成片通看** | 节奏问题数据看不出来 |
| **批量生成前** | 先 `higgsfield generate cost` 报预估积分与镜数，别默默烧钱 |
| **任何 `open_questions`** | 不拍板就往下走 = 猜，猜错要重跑整段 |

## 常见坑（都踩过）

- 模型 ID 以 `higgsfield model list` 为准，文档里的 ID 会滞后。
- 字幕 / 文字叠加前 `export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"`（FF-001，macOS：系统 `ffmpeg` 不带 libass）；Windows 上用 `scoop install ffmpeg` / `winget install Gyan.FFmpeg`，装完即在 PATH 上，不需要这一行。
- **剪辑不得改变 `duration_s`**（FF-011）：它是字幕与配音的共同时间基准，改了必须重跑 `tools/make_srt.py`。
- **台词预算在分镜阶段算**：`duration_s ≥ 台词字数 ÷ 4.4 + 0.5s`，超了就拆镜 / 精简台词 / 延长镜头，不要靠提速硬塞（VD-002）。
- 音色必须海选试听后再定稿（VD-005）；预设音色没有语言与性别元数据，名字说明不了什么。
- 生成参数**只追加不覆盖**，文件名带 `_v00N`，`assets.json` 留 `sha256`（R-10）。
- **场景出图首选 `soul_location`**（官方口径无人空景最强，0.12 积分/张）；**角色与带参考图的编辑必须用 `nano_banana_pro`**（最多 14 张参考图）——一致性靠挂图，不能换成 prompt-only 模型。
- **横转竖默认用 ffmpeg 裁切**，不要顺手调 `generate workflow reframe`（≈9.3 积分/秒，一集 142 秒要 1320 积分，比整集视频还贵）。积分与档位门槛见 `docs/10`。
