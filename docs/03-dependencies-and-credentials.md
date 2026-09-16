# 03 · 依赖与凭证

回答三个问题：**每个环节用什么 skill、调什么 API、要哪些凭证。**

---

## 一、凭证清单（结论先行）

> **本项目不需要任何 apikey。** 唯一凭证是 Higgsfield 的登录态。

| 名称 | 必需性 | 用途 | 配置位置 | 获取方式 |
|---|---|---|---|---|
| Higgsfield 登录态 | **必需** | 全部生成类调用（出图 / 出视频 / 配音 / 转竖屏） | `~/.config/higgsfield/credentials.json` | `higgsfield auth login`（设备码流程） |
| 视觉校验用 key | **不需要** | 镜头一致性核对 | — | 直接复用 Codex 原生识图 |
| 第三方平台 key | **不需要** | 仅在改用外部替代方案时才涉及 | 对应平台 | 见第四节替代方案 |

### 安全管理建议

1. **`credentials.json` 按密钥对待**：`chmod 600`，不复制、不提交、不截图分享。
2. **不回显**：任何脚本、日志、对话里都不要打印 token；跑脚本前不要开 `set -x`。
3. **不进版本库**：`.gitignore` 已忽略 `.env`、`project/work/`、`project/delivery/`。文本资产（`schema/`、`docs/`）正常入库。
4. **泄漏即撤销**：怀疑泄漏立刻 `higgsfield auth logout` 并在平台侧处理，而不是"先删 commit"。
5. **额度与套餐**：`higgsfield account status` 查余额。本账号实测为 **basic 套餐**，Soul 训练可用；当前仍走定妆图路线，留作一致性升级手段。

### 成本与档位门槛

**价格、档位门槛、单集最少积分，全部集中在 [10-account-plans-and-credits.md](10-account-plans-and-credits.md)**（用 `higgsfield generate cost` 实测，不花钱）。这里只留一条结论：能同时满足"多图参考 + 自带音频"的视频模型只有 `seedance_2_0` 与 `seedance_2_5`，其余便宜的模型要么不吃参考图数组、要么不出音。

**注意**：`kling3_0` / `wan2_7` 虽然便宜，但**不接受多图参考数组**，会直接废掉一致性挂载策略，本片不使用。能同时满足"多图参考 + 自带音频"的只有 `seedance_2_0` 与 `seedance_2_5`。

---

## 二、Skills 清单

Codex 的 skill 装在 `~/.codex/skills/<name>/`，插件形式的随插件市场更新。

| Skill | 来源 | 负责阶段 | 用途 | 必需性 |
|---|---|---|---|---|
| `novel-outline` | 社区 `eternityspring/shuohao-skills`（Apache-2.0） | S1（N1 / N4） | 小说 → 短剧大纲五件套：改编说明、人物表、爽点表、分集梗概、资产清单；14 道质量门由脚本硬查（角色分档上限、主场景上限随集数、爽点间隔 ≤3 集、每集钩子必填） | **强烈推荐** |
| `novel-characters` | 同上 | S1 后半 + S2（N2 / N5 / N6） | 角色设定集：人物画像、形象提示词、**音色提示词**、角色设定图（吃 `outline.json` 的角色表） | **强烈推荐** |
| `novel-art` | 同上 | S1 后半 + S2（N3 / N6） | 美术设定集：场景 + 叙事道具，含一致性锚点、光照与状态变体、尺度参照、无人无手白底提示词；11 道质量门 | **强烈推荐** |
| `novel-script` | 同上 | S3（N7 的台词与节拍） | 剧本：场次 + 节拍流，**逐集时长按语速确定性折算**、钩子前 3 拍冷开场、台词本按角色聚合带音色提示词；10 道质量门 | **强烈推荐** |
| `novel-storyboard` | 同上 | S3 / S4（N7 分镜 + N8 关键帧） | 分镜：段（一次生成 ≤15s）→ 分镜（2–5s 硬门）→ 分镜图；MiniMax H3 提示词逐字对账；17 道质量门 | **强烈推荐** |
| `higgsfield-generate` | 官方插件 `higgsfield-ai/skills` | S2 / S4 / S5 / S6 | 出图、出视频、出音频、爆款评分，30+ 模型统一入口 | **必需** |
| `ffmpeg-skill` | 社区 `kajisho5/ffmpeg-skill`（MIT，42 个工具） | S6 / S7 | **所有剪辑与交付**：裁剪、拼接、横转竖、字幕、响度、合规检查、QA 看图。装法 `npx ffmpeg-skill --codex` | **必需** |
| `seedance-prompt-skill` | 社区 `MapleShaw/seedance2.0-prompt-skill`（MIT） | S3 | **运镜四维编码 Z/Y/X/F、25 格流水线、六套剪辑公式、短剧全案范例** | **强烈推荐** |
| ~~`create-storyboard-skill`~~ / ~~`cinematic-storyboard-skill`~~ / ~~`h3-storyboard-skill`~~ | 社区 | — | 分镜类 skill 统一走 `novel-storyboard` 后**不再需要**（拆镜定律那篇仍值得读） | 不装 |
| `higgsfield-youtube-thumbnail` | 官方插件 | S7 | 封面 / 首图 | 可选 |
| `imagegen` | Codex 内置 | S2 | 位图生成与编辑 | 可选 |
| `spreadsheets` / `excel-xlsx` | Codex 内置 | S3 / S7 | 分镜表、资产索引导出为 XLSX | 可选 |
| `visualize` | Codex 内置 | S3 / S6 | 节奏曲线、时间线可视化 | 可选 |

### shuohao-skills 与本地 schema 怎么对接（重要）

它们的产物是独立的 `outline.json` / `cast.json` / `art.json` / `script.json` / `storyboard.json`，**不是本项目的 `schema/` 格式**。分工是：

| 谁管什么 | 说明 |
|---|---|
| **shuohao-skills** | 前段**素材生产**：大纲、角色设定、美术设定、剧本、分镜——把"该有什么"想清楚，并自带脚本质量门 |
| **本流水线** | **状态与验收**：场记台账 `schema/`、ID 与锚点锁定、引用完整性、QA 十项、验收关、剪辑与交付 |

接法是**转录**：把它们的 json 落进 `schema/story_bible.json`、`episodes.csv`、`shots.csv`、`assets.json`，然后照常跑 `check_consistency.py`。转录时保留 `script_ref` 与 `refs` 的来源标记，别让两套编号各说各话（写一个一次性转录脚本，不要手抄）。

本项目**不使用**的官方 skill 及其原因：

| Skill | 为什么不用 |
|---|---|
| `higgsfield-soul-id` | 需 Basic 以上套餐，当前未购买 |
| `higgsfield-video-explainer` | 面向非写实解说片，与写实短剧不匹配 |
| `higgsfield-brandkit` / `higgsfield-product-photoshoot` / `higgsfield-marketplace-cards` | 品牌与电商向，短剧不需要 |

**本项目自建一个编排 skill**（其余全是现成的，不重复造）：

| Skill | 位置 | 干什么 |
|---|---|---|
| `story-to-video` | `skills/story-to-video/`（软链到 `~/.codex/skills/`） | 编排层：丢进剧本后按 N0–N12 推进，管验收关与停机待审；规则仍以 `docs/` 与 `rules/` 为准，不复制 |

安装与实测状态（一条命令体检：`python3 tools/bootstrap.py --doctor`）：

```bash
npx ffmpeg-skill --codex                                              # ✅ 已装
ln -s ../seedance-prompt-skill ~/.agents/skills/seedance-prompt-skill # ✅ 已装（软链，避免分叉副本）
ln -s <本仓库>/skills/story-to-video ~/.codex/skills/            # ✅ 已装
```

完整清单（安装 / 注册 / 登录 / 验证 / 失败信号）见 [09-toolchain-setup.md](09-toolchain-setup.md)。

---

## 三、API / 命令清单

所有 Higgsfield 调用**必须走 CLI**，不要直接 curl `api.higgsfield.ai`。CLI 负责认证、重试、轮询、参数校验与文件自动上传。

| 命令 / 接口 | 阶段 | 用途 | 凭证 |
|---|---|---|---|
| `higgsfield auth login` | S0 | 设备码登录（交互式） | 浏览器授权 |
| `higgsfield account status` | S0 / 全程 | 余额与套餐级别 | 登录态 |
| `higgsfield model list` / `model get <id>` | 全程 | **模型与参数的唯一口径（以 CLI 为准）**，文档与 CLI 版本有滞后时以此为准 | 登录态 |
| `higgsfield upload create <file>` | S2 / S5 | 上传本地素材，拿到 upload id | 登录态 |
| `higgsfield generate create <model> ... --wait --json` | S2 / S4 / S5 | 图 / 视频 / 音频生成（一次调用创建并阻塞到结束） | 登录态 |
| `higgsfield generate workflow reframe` | S6 | 横转竖，产出抖音 9:16 分发版 | 登录态 |
| `higgsfield generate workflow draw_to_video` | S4 | 用改过的单帧重渲染该片段，修穿帮 | 登录态 |
| `higgsfield generate workflow voice-change` | S5 | 成片换音色 | 登录态 |
| `higgsfield voices list` / `voices get` | S5 | 列音色，取 `voice_id` 与 `voice_type` | 登录态 |
| `higgsfield generate cost ...` | 全程 | 提交前估算成本 | 登录态 |
| `higgsfield generate list` / `get` / `wait` | 全程 | 作业查询与重连 | 登录态 |

本项目**不用**的命令：`soul-id *`（需付费套餐）、`generate workflow dubbing`（纯中文，不出海）。

> **版本滞后（实测）**：官方 skills 仓库把 `seedance_2_5` 列为默认视频模型，但 CLI 的 `MODELS.md` 里查不到它；仓库 README 宣传 9 个 skill，实际只有 8 个（`higgsfield-game-generation` 缺失，`./setup` 脚本会因此报错退出）。**选型一律先跑 `higgsfield model list`。**

---

## 四、本地工具清单（本机已实测）

| 工具 | 版本 | 用途 |
|---|---|---|
| `ffmpeg` / `ffprobe` | 8.1.2 | 拼接、裁剪、转码、混音、规格核对 |
| `ffmpeg-full` | **9.0.1（必须另装）** | 字幕烧录、文字叠加、防抖。普通 `ffmpeg` formula **不含** libass/freetype/libvidstab，`brew install ffmpeg-full`，是 keg-only，调用前 `export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"` |
| `python3` | 3.14.6 | 场记核对、批处理脚本 |
| `jq` | 1.8.2 | JSON / CSV 查询与转换 |
| `ImageMagick (magick)` | 7.1.2 | 图片规格统一、加水印、拼版 |
| `git` | 2.39.5 | 文本资产版本管理 |
| `higgsfield` CLI | 1.1.25（**已安装**） | 全部生成类调用；`higgsfield model list` 是模型与参数的唯一口径（以 CLI 为准） |

---

## 五、环节级替代方案对比

| 环节 | 主路线（本项目默认） | 本地 / 开源路线 | 第三方平台路线 |
|---|---|---|---|
| S1 剧本结构化 | Codex 直接读剧本抽取 —— 免 key、长上下文、中文强 | 本地中文大模型 —— 数据不出机；缺点是要显卡与运维 | 云端 LLM API —— 上下文更长；缺点是额外 key 与费用 |
| S2 设定出图 | Higgsfield `nano_banana_pro`（实测 2 积分/张）/ `gpt_image_2_5` —— 与后续视频同平台，参考图可直接复用 | ComfyUI + 开源文生图 —— 免费、可训 LoRA；缺点是要自建环境、质量波动大 | 即梦 / Midjourney —— 质量高；缺点是资产跨平台搬运会断一致性链 |
| S4 视频生成 | Higgsfield `seedance_2_5`（多镜、4–30s）；对白戏用 `kling3_0 --sound on` / `wan2_7` | 本地开源视频模型 —— 免费可离线；缺点是显存要求高、连贯性弱 | 即梦 `dreamina` 等 —— 各有强项；缺点是多平台导致风格不统一 |
| S5 配音 | Higgsfield `text2speech_v2`（5 个引擎可选）—— 与画面同平台、一个账号搞定 | GPT-SoVITS / ChatTTS 等开源 TTS —— 可克隆音色；缺点是要训练、要显卡 | ElevenLabs 直连 —— 音质顶级；缺点是贵、要单独 key |
| S5 口型 | 生成时带音频（`kling3_0 --sound on` / `wan2_7`）—— 最省事；缺点是台词要写进提示词 | Wav2Lip / LatentSync 等 —— 可事后修；缺点是画质有损、需 GPU | 第三方对口型服务 —— 效果稳定；缺点是额外成本与数据外发 |
| S6 剪辑 | `ffmpeg` 脚本化 —— 可复现、可版本化、批量快；缺点是转场与调色不如 GUI 直观 | 剪映 —— 直观、模板多；缺点是手工步骤不可复现 | 云端剪辑 API —— 可自动化；缺点是成本与锁定 |
| S6 横转竖 | `higgsfield generate workflow reframe` —— 一条命令、与母版同源 | ffmpeg 裁切 + 构图重排 —— 零成本、完全可控 | 剪辑软件手动适配 —— 精细；缺点是不可批量 |
| S7 封面 | `higgsfield-youtube-thumbnail` —— 与全片风格同源 | ImageMagick 模板批量生成 —— 完全可控、零成本 | 设计工具手工做 —— 质量高；缺点是不可批量 |

**选型建议**：除非有合规或成本硬约束，**S2–S5 尽量留在 Higgsfield 一家**。跨平台意味着参考图与风格锚无法传递，是短剧一致性最大的隐形杀手。
