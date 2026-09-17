# FF · 剪辑与交付规则

管一件事：**剪辑产物必须经得起平台检验，而不是"我看着还行"。**

## 工具来源

本项目不自造 ffmpeg 命令，统一用 [`kajisho5/ffmpeg-skill`](https://github.com/kajisho5/ffmpeg-skill)（MIT，1070★，42 个工具，纯 Python 标准库）。

```bash
npx ffmpeg-skill --codex        # 装到 ~/.agents/skills/ffmpeg-skill
S=~/.agents/skills/ffmpeg-skill
python3 $S/scripts/<tool>.py --help
```

---

## FF-001 · 前置：PATH 必须指向 ffmpeg-full `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 字幕烧录、文字叠加、防抖、带时间码的 QA 拼图全部报 `No such filter: 'drawtext'` / `'subtitles'` |
| **判定标准** | `python3 $S/scripts/_contract.py doctor` 输出不是 `0 required missing` |
| **修正要求** | ① 装一个**带 libass / freetype 的完整构建**：macOS `brew install ffmpeg-full`（keg-only，不覆盖系统 ffmpeg），Windows `scoop install ffmpeg` 或 `winget install Gyan.FFmpeg`（无 keg-only 分裂，装完即在 PATH 上）；② macOS **每次调用前** `export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"`，Windows 上这条不需要（手工便携包才用 `$env:Path = "D:\tools\ffmpeg\bin;$env:Path"`），因为工具用 `shutil.which("ffmpeg")` 找二进制 |
| **适用范围** | 所有用 ffmpeg-skill 的场合 |
| **依据** | 实测：homebrew 的普通 `ffmpeg` formula **不包含** libass / freetype / libvidstab，doctor 会报 `4 required missing`；换 ffmpeg-full 后变成 `65 capabilities, 0 missing`。skill 自身的 doctor 给出的修复建议就是这一条 |

## FF-002 · 先 probe，再规划 `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 凭文件大小或印象规划转码参数，结果分辨率、帧率、时长都对不上 |
| **判定标准** | 任何剪辑任务开始前没有 `probe.py` 的输出 |
| **修正要求** | `python3 $S/scripts/probe.py <input>`，读 duration / fps / width×height / codecs / `variable_frame_rate_suspected`。**从真实数字规划，不从假设规划** |
| **适用范围** | 每次剪辑任务的第一步 |
| **依据** | 本项目实测：demo 母版 probe 出 `variable_frame_rate_suspected: true`（`r_frame_rate 24/1` 但 `avg_frame_rate 23.785`）——拼接产物天然是 VFR，不 probe 就发现不了 |

## FF-003 · 能无损就别重编码 `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 一个简单裁剪被重编码三次，画质掉档、文件膨胀 |
| **判定标准** | 请求可以用流拷贝（关键帧上的裁剪、remux、仅改音频）完成却做了重编码 |
| **修正要求** | 优先 `cut.py`（默认流拷贝）、`loudness.py`（默认流拷贝视频）。只有需要帧精确时才用 `cut.py --accurate`。**中间产物统一 CRF 18，只在最后一步 `export.py` 出成品** |
| **适用范围** | 所有剪辑步骤 |
| **依据** | 每一步重编码都会累积压缩损伤；多次编码是画质下降最常见的自伤 |

## FF-004 · 长任务先 dry-run `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 跑了几分钟才发现参数错了、目标文件被覆盖 |
| **判定标准** | 预计超过 1 分钟的编码任务没有先跑 `--dry-run --json` |
| **修正要求** | `--dry-run --json` 先在纸上确认；要复现就用 `--plan FILE` 记入台账，再用 `render.py FILE` 执行（输入变了会拒绝）。**`--json` 里的数字才算数——dry-run 的摘要行里尺寸可能是占位值** |
| **适用范围** | 所有编码任务 |
| **依据** | 工具契约明确说明 dry-run 摘要中的尺寸可能是占位值 |

## FF-005 · 修改顺序固定 `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 先烧字幕再改画幅，字幕被裁掉或字号失配 |
| **判定标准** | 步骤顺序不是：**色彩（HDR→SDR / LUT）→ 裁剪 → 拼接 → 静音切除 → 画幅/时长 fit → 字幕/叠加 → 同步 → 音频 → 响度 → 导出** |
| **修正要求** | 严格按上述顺序。**画面变更必须早于字幕与叠加**，这样文字才是按最终画幅排版的。三步以上不要手搓命令链，用 `render.py` + `project.json` 一把跑完 |
| **适用范围** | 所有多步剪辑 |
| **依据** | 字幕的字号与安全区依赖最终画面尺寸 |

## FF-006 · 交付前必须过 check `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 成片交给平台，被二次压缩或直接判不合格 |
| **判定标准** | 交付前没有跑 `check.py OUTPUT --platform <平台>` |
| **修正要求** | `python3 $S/scripts/check.py <output> --platform tiktok`（本项目用 tiktok）。**格式类**（编码、像素格式、尺寸、真峰值、色彩标签、VFR）直接修；**判断类**（时长、画幅、帧率、响度）会改变内容，只有在需求已隐含答案时才改，否则用一句话说明取舍 |
| **适用范围** | 每次交付 |
| **依据** | 本机实测：我们的 demo 第一版 `check.py` 报 **loudness -21.7 LUFS 不合格**（抖音要求 -14 ± 2）、VFR、采样率 32k、无字幕轨——**这四条我们自建的检查流程一条都没查过** |

## FF-007 · 响度目标要留余量 `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 响度归一化后复测，真峰值反而超标 |
| **判定标准** | 设了 `--tp -1` 却复测出 `-0.9 dBTP`（要求 ≤ -1） |
| **修正要求** | 限幅器会有过冲，**真峰值目标比标准再低 0.5 dB**：`loudness.py <in> -I -14 --tp -1.5 --sample-rate 48000 -o <out>`。**归一化之后必须再跑一次 `check.py` 复测**，不能只看工具说成功 |
| **适用范围** | 所有需要响度归一化的交付 |
| **依据** | 本机实测：`--tp -1` → 复测 -0.9 dBTP FAIL；改 `--tp -1.5` → 复测 -1.5 dBTP PASS |

## FF-008 · 必须看图，不能只看 probe `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 数字全对，成片却把主体裁掉了、字幕压在脸上 |
| **判定标准** | 画面发生变化的步骤（字幕、叠加、裁切、缩放、调色、拼接）之后没有产出并查看 QA 图 |
| **修正要求** | `python3 tools/eye.py <图或视频> --tiles 3x2` 出 ≤300KB 的 JPEG 拼图并**真的看**；单帧用 `--at T`。要看带时间码的全尺寸拼图、两版对比（`--compare`）或平台 UI 遮挡（`--safe tiktok`）时仍用 `$S/scripts/look.py`，但出图后必须过一遍 `eye.py` 再看。**任务在报告里写出 QA 图路径之前不算完成** |
| **适用范围** | 所有画面变更 |
| **依据** | probe 看不出"字幕盖在脸上"；本机实测：原图 4–9MB、`look.py` 全尺寸拼图 2MB，内联进上下文会让请求体冲到 40MB 以上，被网关 413（见 `docs/05` 第二节） |

## FF-009 · 裁切位置不许默认居中 `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 16:9 转 9:16 后主体被裁掉一半 |
| **判定标准** | 使用 `--fit crop` 时没有确认主体是否在画面中段 |
| **修正要求** | 居中裁剪是**猜测**：横转竖会丢掉大部分宽度，"不在中间三分之一的东西"（画面边缘的人、举到一侧的道具）会被切掉。主体偏心时用 `--crop-x` / `--crop-y`（0=左/上，1=右/下）指定，或改用 `--fit pad`（不丢内容）。**不确定时不要静默接受默认** |
| **适用范围** | 所有改画幅的步骤 |
| **依据** | 本机实测：demo 的 SH001 主体在画面左侧，居中裁到 9:16 后人物被左边缘切掉（`qa_safe_area=fail`），这条正是成因 |

## FF-010 · 保留原件，不覆盖源 `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 一版调参把上一版覆盖了，回不去 |
| **判定标准** | 输出路径指向了本任务没有创建过的文件 |
| **修正要求** | 输出永远写新文件名（`_v002`）。跑脚本的环境里设 `FFMPEG_SKILL_NO_OVERWRITE=1`，这样已存在的目标会被**拒绝**而不是警告；确要替换时才加 `--overwrite` |
| **适用范围** | 所有写操作 |
| **依据** | 源素材一旦被覆盖，重跑与对比都失去基准 |

## FF-011 · 剪辑不得改变单镜时长 `[硬]`

| 项 | 内容 |
|---|---|
| **问题现象** | 字幕与画面对不上、"这段怎么突然短了一截"，而且越到片尾偏得越多 |
| **判定标准** | 成片的单镜时长与 `shots.csv.duration_s` 不一致，且没有回写 |
| **修正要求** | `duration_s` 是**字幕、台词、成片的共同时间基准**：字幕时间轴由它累加（`tools/make_srt.py`），配音按它裁剪。所以**不要对每条素材顺手"首尾各剪 0.5–1s"**——剪掉的不只是运镜抖动，还有台词的头尾。要裁就裁**首尾各 0–0.2s**（只去生成噪声），确需大裁时：① 回写 `duration_s`，② 重跑 `make_srt.py`，③ 跑场记核对 R16 确认字幕逐条对齐 |
| **适用范围** | 所有改变镜头时长的剪辑操作 |
| **依据** | 本机实测：一次分镜时长调整（9 个镜头按台词延长，合计 +22s）之后，`EP01.srt` 里有 12 条字幕的起始时间与分镜差了 4–20s。字幕不会自己失效，只会静默错位；场记核对 R16 把这类偏差标为错误 |

---

## 附 A · 本项目的高频路由表

| 要做的事 | 工具 |
|---|---|
| 看素材规格 | `probe.py` |
| 裁片段（无损） | `cut.py` |
| 拼接多段 | `join.py` |
| 横转竖 / 改时长 | `fit.py --aspect 9:16 --fit crop --width 1080 [--crop-x]` |
| 烧字幕 / 软字幕 | `caption.py --mode burn\|mux --srt X.srt --platform tiktok` |
| 加标题、LOGO | `graphics.py`（**需 ffmpeg-full**） |
| 响度归一化 | `loudness.py -I -14 --tp -1.5 --sample-rate 48000` |
| 音画同步（外接麦） | `sync.py` |
| 交付合规检查 | `check.py --platform tiktok` |
| 出 QA 拼图看图 | `tools/eye.py --tiles 3x2`（≤300KB）/ `--at T`；`look.py` 的 `--compare` / `--safe tiktok` 出图后也要过 `eye.py` |
| 多步渲染一把跑 | `render.py project.json` |
| 环境体检 | `_contract.py doctor`（**只在失败时跑**，不要拿来开工） |

## 附 B · 已实测的坑

| 坑 | 现象 | 处理 |
|---|---|---|
| `--json-brief` 的输出前面有命令行与状态行 | `json.load(stdin)` 直接抛 `Expecting value: line 1 column 1` | 从第一个 `{` 开始截取再解析 |
| doctor 的能力契约不全 | `look.py` 被标为可用，实际因 `drawtext` 缺失而失败 | 装了 ffmpeg-full 后消失；**以后遇到"doctor 说行但实际报错"，先怀疑契约漏标** |
| 并发工具调用挤在一条命令里 | 输出交错，难以定位是哪一步失败 | 每个工具单独跑，或用 `render.py` 的 project.json 串起来 |
| 转竖后分辨率缩水 | `--fit crop` 只裁不放大，输出 406×720 | 显式给 `--width 1080`（高度按画幅自动跟随） |

## 附 C · 与流水线验收关的对应

| 验收关 | 本规则对应 |
|---|---|
| G6（S6 → S7） | FF-006 `check.py` 必须 0 failed；FF-008 `tools/eye.py` 的 QA 图路径必须写进报告 |
| 人工不可省的三件事之一"成片通看" | FF-008 提供看图的物料，人仍然要通看一遍 |
