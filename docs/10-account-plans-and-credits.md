# 10 · 账号、权限与积分门槛

> 一页回答三件事：**要什么账号**、**哪些能力需要什么档位（权限门槛）**、**每个动作最少多少积分**。
> 积分单价一律以 `higgsfield generate cost` 为准（**它不花钱**，提交前自己复算，见第六节）；
> 档位与月费来自作者 2026-09-16 从官网定价页（登录态）复制的原文，见第二节。

---

## 一、账号与登录

| 项 | 做法 |
|---|---|
| 注册 | 浏览器打开 https://higgsfield.ai ，邮箱注册，无需邀请码 |
| 登录 | `higgsfield auth login`（终端出设备码 → 浏览器授权） |
| 凭证 | `~/.config/higgsfield/credentials.json`（CLI 自动 `chmod 600`） |
| 查状态 | `higgsfield account status`（账号 / 档位 / 余额）、`higgsfield account transactions`（积分流水） |
| 本机实测 | 已登录；档位 **basic**（对应下表 $9/月档） |

**没有 apikey。** 唯一凭证就是这台机器上的登录态；泄漏处置是 `higgsfield auth logout` + 平台侧处理。

---

## 二、套餐档位与权限矩阵（官网原文，2026-09-16）

| | **Basic** | **Pro** | **Max** | **Team** |
|---|---|---|---|---|
| 定位 | 第一次做 AI 创作 | 日常创作 | 大项目 | 团队 / 企业 |
| 月费（年付） | **$9/月** | **$23/月**（月付 $29，年付省 $72） | **$165/月**（月付 $237，年付省 $864） | **从 $65/座/月**，2 座起 |
| 每月积分 | **120**（固定） | 600（月付档 900） | 5,400（档位 1,800 / 3,600 / 5,400） | 池化：从 1,000/座/月 |
| 等价出图 | ≈ 60 张 Nano Banana Pro | ≈ 300 张 NBP | ≈ 2,700 张 NBP | 自定义额度 |
| 「无限免费生成」模型 | Nano Banana Pro / Nano Banana 2 / Kling 3.0（**没有其他**） | Nano Banana 2（2K，7 天无限）、Kling 3.0（7 天无限）等 **7 个** | NBP 2K（7 天无限）等 **7 个** | 同全量 |
| **Seedance 2.0 完整版** | **❌ 没有**（只有 **2.0 Fast** 与 **2.0 Mini**） | ✅ 完整行，含 **1080p / 4K** | ✅ 同 Pro | ✅ |
| **Seedance 2.5** | **❌ 没有**（Pro 起才有） | ✅ 1080p 全量 | ✅ | ✅ |
| 并行生成 | 2 视频 + 2 图 | 无限（付费并行） | 无限 | 更高并发 + 优先队列 |
| 其他 | Supercomputer、精选模型与功能、新功能早鸟、无限 marketplace | 全模型全功能、每积分成本更低 | 每积分成本再低 60% | SOC 2 / SSO / 无训练条款 / 专属产能 SLA / Slack 支持 |

### 由这张表推出的两条硬事实

1. **Basic 档跑不了完整 Seedance 2.0，也跑不了 2.5。** 只能在 `seedance_2_0` 的 **fast 模式**与 `seedance_2_0_mini` 之间选，且 fast 只支持 480p/720p。
2. **月费档决定的不只是钱，是产能上限**：Basic 120 积分/月，一集要用 400+ 积分（见第四节）——**Basic 只够跑通流程与试片，不够出片**。

### 实测澄清（本机 CLI 一手，和官网口径对不齐的地方）

| 官网说法 | 本机实测 | 结论 |
|---|---|---|
| Nano Banana Pro 属于「UNLIMITED & FREE GENS」 | **每张扣 2 积分**：本轮生成 6 张，余额 67.2 → 55.2 | 规划预算**按扣费口径**，别按"无限"算 |
| 「Seedance 2.0 Fast」 | CLI 里**不是独立模型**，是 `seedance_2_0 --mode fast`（`mode: std\|fast`，默认 std） | 分镜表写 `seedance_2_0` 就够，执行时用 `--mode fast` |
| —（官网未写） | `--mode fast` **只支持 480p / 720p**；1080p / 4K 必须 std，而 std 属 Pro 档 | Basic 上最高 720p |

---

## 三、单价表（本机 `generate cost` 实测）

### 出图

| 用途（官方 `model-catalog.md` 的推荐口径） | 模型 | 规格 | 积分 | 档位 |
|---|---|---|---|---|
| **场景 / 环境 / 无人空景**（官方：*Best-in-class*） | `soul_location` | 16:9 | **0.12** | Basic+ |
| 角色（UGC / 时尚编辑感） | `text2image_soul_v2` | 2k | **0.12** | Basic+ |
| 角色（创意人设，**纯文本不吃参考图**） | `soul_cast` | 16:9 | **0.12** | Basic+ |
| 电影感静帧 | `soul_cinematic` | 2k | **0.12** | Basic+ |
| **通用 / 需挂参考图编辑**（最多 14 张参考图） | `nano_banana_pro` | 1k / 2k / 4k | 2 / 2 / **4** | Basic+ |

### 视频（按秒计费，最短 4s）

| 模型 / 模式 | 规格 | 积分/秒 | 实例 | 档位 |
|---|---|---|---|---|
| `seedance_2_0 --mode fast` | 720p | **3.5** | 5s = 17.5 | **Basic+** |
| `seedance_2_0_mini` | 720p | **2.5** | 5s = 12.5 | **Basic+** |
| `seedance_2_0`（std） | 720p | **4.5** | 5s = 22.5 · 6s = 27 · 11s = 49.5 | **Pro+** |
| `seedance_2_0`（std） | 1080p | **9** | 6s = 54 | **Pro+** |
| `seedance_2_5` | 1080p | **9** | 6s = 54 | **Pro+** |

### 音频与后处理

| 动作 | 命令 | 积分 | 档位 |
|---|---|---|---|
| 单句台词配音 | `text2speech_v2`（`seed_speech` 预设） | **0.1 / 句** | Basic+ |
| 音效 / 环境音 | `seed_audio` | **0.1 / 条** | Basic+ |
| 横转竖 | `generate workflow reframe` 1080p | **≈9.3 / 秒**（7.1s = 66） | Basic+ |
| Soul ID 训练 | `soul-id create` | 未实测 | **Basic+**（免费档不行，见下） |

---

## 四、一集要多少积分（EP01 实测体量：28 镜 / 142 秒）

| 环节 | 算法 | Mini 跑法（Basic） | Fast 跑法（Basic） | std 跑法（Pro） |
|---|---|---|---|---|
| 场景资产 | 1 景 × 1 张 soul_location | 0.12 | 0.12 | 0.12 |
| 角色定妆图 | 3 角色（本项目实测 4 张资产共 12 积分） | 12 | 12 | 12 |
| 道具 + 风格锚 | 3 张 | 6 | 6 | 6 |
| 关键帧 | 28 镜 × 1 张 nano_banana_pro 2k | 56 | 56 | 56 |
| **视频** | 142 秒 × 每秒价 | 2.5×142 = **355** | 3.5×142 = **497** | 4.5×142 = **639** |
| 配音 | 16 句 × 0.1 | 1.6 | 1.6 | 1.6 |
| 音效 / BGM | 2 条 | 0.2 | 0.2 | 0.2 |
| 横转竖 | 用 ffmpeg 裁切（**别用 reframe**） | 0 | 0 | 0 |
| **合计** | | **≈ 431 积分/集** | **≈ 573 积分/集** | **≈ 715 积分/集** |

### 档位产能对照

| 档位 | 每月积分 | 每月能出几集（Mini / Fast / std） | 跑完 120 集要多久（Mini） |
|---|---|---|---|
| **Basic（当前）** | 120 | **0.28 / 0.21 / —（std 不可用）** | 不现实（需 431×120 = 5.2 万积分 ≈ 51 个月） |
| **Pro** | 600 | 1.4 / 1.05 / 0.84 | 约 8.6 年 |
| **Max** | 5,400 | 12.5 / 9.4 / 7.6 | **约 9.6 个月** |
| Team | 1,000+/座/月（池化） | 按座数与额度线性放大 | 用池化额度 + 并发 |

**结论**：这是**120 集**的量级——单集 431–715 积分、全剧 5.2–8.6 万积分。Basic 只能跑通流程，Pro 够做样片与月更一集，**要真正量产得上 Max 或 Team**。

---

## 五、由价格与档位推出的硬决策

1. **横转竖默认用 ffmpeg 裁切**，不用 `workflow reframe`：reframe ≈9.3 积分/秒，一集 142 秒要 **1320 积分**，比整集视频还贵一倍。只有构图必须重排时才用（rules/FF-009）。
2. **场景图优先 `soul_location`（0.12 积分/张）**，官方口径是无人空景最佳；注意它是 **prompt-only**（不吃参考图）。
3. **关键帧与带参考图的编辑必须用 `nano_banana_pro`**（最多 14 张参考图）——这是一致性挂载的物理前提，不能为省钱换 prompt-only 模型。
4. **Basic 档的视频只能跑 `--mode fast`（≤720p）或 mini**；要 1080p/4K、要 Seedance 2.5，**必须升 Pro**。分镜表里写 `seedance_2_0` 是对的，执行参数按档位给（`model_mode` 由用户文档记录，见 docs/01 S4）。
5. **4K 只给交付封面**（4 积分/张，2K 的两倍）；分镜关键帧 2K 足够。
6. **免费档唯一被卡住的是 Soul ID 训练**（官方 skills 仓库原文：`Minimum Basic plan required` / `Soul training needs a paid plan`）；本项目走「定妆图三视图 + 多角度」，不受影响。

---

## 六、怎么自己复算（不改钱）

```bash
# 出图：场景 / 角色 / 通用
higgsfield generate cost soul_location      --prompt t --aspect_ratio 16:9
higgsfield generate cost text2image_soul_v2 --prompt t --quality 2k
higgsfield generate cost nano_banana_pro    --prompt t --resolution 2k

# 视频：改时长看单价，改 mode 看档位差
higgsfield generate cost seedance_2_0      --mode fast --prompt t --duration 5 --resolution 720p
higgsfield generate cost seedance_2_0_mini  --prompt t --duration 5 --resolution 720p
higgsfield generate cost seedance_2_0      --prompt t --duration 5 --resolution 1080p

# 配音 / 音效 / 横转竖
higgsfield generate cost text2speech_v2 --prompt "测试" --variant seed_speech \
  --voice_type preset --voice_id <voice_id>
higgsfield generate cost seed_audio --prompt t
higgsfield generate cost workflow reframe --duration 7.1 --resolution 1080p
```

**模型与参数永远以 `higgsfield model list` / `model get <id>` 为准**：官方文档与 skills 仓库都有滞后（实测出图模型真名是 `nano_banana_pro`；「Seedance 2.0 Fast」在 CLI 里是 `--mode fast`，不是独立模型）。

---

## 七、本项目实际花掉的积分

| 动作 | 数量 | 积分 |
|---|---|---|
| 补齐 EP01 的 4 张资产（CH-003 / CH-004 / CH-005 / PR-004） | 5 张（含 CH-003 重复一次） | 10 |
| CH-004 v002 重做（v001 看图不合格） | 1 张 | 2 |
| **合计** | 6 张 | **12**（余额 67.2 → 55.2） |

教训：生成成功就要**立刻下载记入台账**——第一次生成 CH-003 时只看了 JSON、没存文件，脚本判定"文件不存在"又生成了一遍，白花 2 积分。
