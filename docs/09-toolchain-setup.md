# 09 · 工具链：安装 / 注册 / 登录 / 验证

> 回答一个问题：**换台机器，从零到能跑，要装什么、要注册什么、怎么确认装对了。**
> 每条都是「安装 → 注册或授权 → 验证 → 失败信号」。实测环境：macOS Apple Silicon，2026-09-16。

一条命令体检：

```bash
python3 tools/bootstrap.py --doctor     # 全绿 = 可以开工；有 ❌ 就照它给的命令补
```

---

## 一、五类东西，别混着数

| 类别 | 装在哪 | 频次 | 谁提供 |
|---|---|---|---|
| 系统二进制 | Homebrew / 系统自带 | 一次 | 本机 |
| `ffmpeg-full` | Homebrew（keg-only） | 一次安装 + **每次调用前改 PATH** | 本机 |
| `higgsfield` CLI | 官方安装脚本 → `/usr/local/bin` | 一次 | Higgsfield |
| Higgsfield 账号 + 登录态 | 浏览器注册 → `~/.config/higgsfield/credentials.json` | 一次（登录态会过期） | 你 |
| 第三方 skills | `~/.agents/skills/`、`~/.codex/skills/` | 一次 | 社区 / 本项目 |

**没有任何 apikey。** 唯一凭证是 Higgsfield 登录态，见第七节。

---

## 二、系统二进制

| 依赖 | 用途 | 安装 | 验证 | 本机实测 |
|---|---|---|---|---|
| `python3` | 场记核对、批处理脚本 | `brew install python@3` | `python3 -V` | 3.14.6 |
| `jq` | JSON / CSV 查询 | `brew install jq` | `jq --version` | 1.8.2 |
| `git` | 文本资产版本管理 | `xcode-select --install` | `git --version` | 2.39.5 |
| `magick`（ImageMagick） | 图片规格统一、拼版 | `brew install imagemagick` | `magick -version` | 7.x |
| `node` / `npx` | 安装 `ffmpeg-skill` 用 | `fnm install --lts` 或 `brew install node` | `node -v` | v25.9.0 |
| `tar` / `shasum` | 归档、剧本指纹 | 系统自带 | `shasum -a 256 <文件>` | ✓ |

---

## 三、ffmpeg：唯一「必须另装」的系统依赖

```bash
brew install ffmpeg            # 装了也行，但字幕相关的活儿干不了
brew install ffmpeg-full       # keg-only，不会覆盖上面那个
```

**为什么是两个**：Homebrew 的普通 `ffmpeg` formula 编译时**没带** libass / libfreetype / libvidstab，字幕烧录、文字叠加、防抖一律报 `No such filter: 'subtitles'`。本机实测 `/opt/homebrew/bin/ffmpeg` = 9.0.1，`ffmpeg -filters` 里**没有** `subtitles` / `drawtext`；`ffmpeg-full` 有。

```bash
# 验证：必须两条都有输出
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"
ffmpeg -hide_banner -filters | grep -E "subtitles|drawtext"
```

**失败信号**：`No such filter: 'drawtext'` / `'subtitles'` / `'vidstabdetect'` → PATH 没生效（FF-001）。这一行 PATH 必须写在每次调用之前，因为 `ffmpeg-skill` 是用 `shutil.which("ffmpeg")` 找二进制的。

---

## 四、Higgsfield：注册 → 安装 → 登录 → 验证

### 1) 注册账号

浏览器打开 https://higgsfield.ai 用邮箱注册（无需邀请码），登录后在账号页确认**套餐与积分**。

| 套餐事实 | 对本项目的影响 |
|---|---|
| 免费额度可跑生成 | 够跑通 EP01 的前几个镜头 |
| Soul 真人脸训练需 **Basic（付费档）以上** | **本项目不需要**：走「定妆图三视图 + 多角度」路线，一致性靠反复挂同一张参考图（docs/02 第二/七节）。档位门槛与积分见 [docs/10](10-account-plans-and-credits.md) |
| 积分按模型计费 | 出图 `nano_banana_pro` 2 积分/张；视频 `seedance_2_0` 22.5 积分/5s 720p。单集 28 镜粗算 600+ 积分 |

### 2) 装 CLI

```bash
curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh
```

### 3) 登录（设备码流程）

```bash
higgsfield auth login        # 终端给一个设备码，浏览器里确认授权
```

凭证落在 `~/.config/higgsfield/credentials.json`，CLI 会自动 `chmod 600`。

### 4) 验证三连

```bash
higgsfield --version         # 实测：1.1.25
higgsfield account status    # 实测输出形如：<账号> — basic plan, NN.N credits（余额随时变，不写死）
higgsfield model list        # 模型 ID 的唯一口径，不要照抄文档
```

### 5) 失败信号与处置

| 现象 | 原因 | 处置 |
|---|---|---|
| `unauthenticated` / 401 | 登录态过期 | `higgsfield auth login` 重登 |
| `unknown model: nano_banana_2` | 抄了旧文档的模型 ID | 以 `higgsfield model list` 为准（实测真名是 `nano_banana_pro`） |
| `Minimum Basic plan required` | 用了 Soul 训练 | 本项目不走 Soul；或升级套餐 |
| 余额不足 / 中途失败 | 积分耗尽 | `higgsfield account status` 查余额，长项目分段充值 |
| 作业被 `nsfw` / `ip_detected` 拦 | 内容安全 | 避免真实公众人物与商标，提示词用正面表述（风险 R-08） |

---

## 五、第三方 skills（装一次，跨项目复用）

| skill | 装法 | 验证 | 本机状态 |
|---|---|---|---|
| `ffmpeg-skill` | `npx ffmpeg-skill --codex` | `ls ~/.agents/skills/ffmpeg-skill` | ✅ 已装 |
| `seedance-prompt-skill` | 仓库在 `../seedance-prompt-skill`，软链即可 | 同上 | ✅ 已装（软链，避免分叉） |
| **`shuohao-skills` 五件套** | 见下一节：`git clone` + 仓库自带的 `./scripts/install.sh --codex` | `ls ~/.codex/skills/novel-*` | ✅ 已装（软链） |
| higgsfield 官方插件 | 仓库在 `../higgsfield-skills`，按插件安装 | `ls ~/.codex/plugins/cache/personal/` | ⚠️ 未装（CLI 已够用） |
| **本项目自建编排 skill** | `ln -s <本仓库>/skills/story-to-video ~/.codex/skills/` | `ls -l ~/.codex/skills/` | ✅ 见 `skills/story-to-video/SKILL.md` |

### shuohao-skills（短剧前段五件套）

`novel-outline` / `novel-characters` / `novel-art` / `novel-script` / `novel-storyboard`，来源
[`eternityspring/shuohao-skills`](https://github.com/eternityspring/shuohao-skills)（Apache-2.0）。
**零 npm 依赖、零 API key**，脚本只用 Node 标准库。

```bash
# 前置：Node ≥ 18（实测 v25.9.0）
node -v

# 安装：克隆到复用层旁边，再让仓库自带的脚本做软链（它只覆盖软链，不动真实目录）
git clone --depth 1 https://github.com/eternityspring/shuohao-skills.git ../shuohao-skills
cd ../shuohao-skills
./scripts/install.sh --codex            # 装到 ~/.codex/skills/
./scripts/install.sh --codex novel-characters   # 只装一个
./scripts/install.sh --uninstall                # 取消软链

# 验证：5 个 skill 各自的自测（实测 1170 项断言全过，约 1 秒）
for f in skills/*/scripts/selftest.mjs; do node "$f"; done
```

软链安装意味着 `git pull` 之后立刻生效，不用重装。体检一并覆盖：

```bash
python3 tools/bootstrap.py --doctor     # 检查 node 版本 + 5 个 novel-* skill 是否在
```

---

## 六、发布环节：不自动化

抖音没有对外开放的上传 API（且要求实名认证），**发布是人工步骤**，不进流水线：

1. 注册抖音账号并完成实名认证；
2. 创作者中心上传 9:16 分发版 + 封面 + 简介；
3. 上传前对着 `project/delivery/delivery_checklist.md` 过一遍。

---

## 七、凭证纪律

1. `credentials.json` **按密钥对待**：`chmod 600`、不复制、不提交、不截图。
2. **不回显**：脚本与日志里不打印 token。`tools/bootstrap.py --doctor` 已把账号邮箱打码成 `***@***`。
3. **不进版本库**：`.gitignore` 已忽略 `.env`、`project/work/`、`project/delivery/`、`__pycache__/`。
4. **泄漏即撤销**：`higgsfield auth logout`，再去平台侧处理，而不是「先删 commit」。

---

## 八、换机 30 秒清单

```bash
brew install python@3 jq imagemagick ffmpeg ffmpeg-full
npx ffmpeg-skill --codex                                       # 剪辑 skill
curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh
higgsfield auth login && higgsfield account status && higgsfield model list
ln -s <仓库根>/seedance-prompt-skill ~/.agents/skills/seedance-prompt-skill
ln -s <本仓库>/skills/story-to-video ~/.codex/skills/story-to-video
python3 <本仓库>/tools/bootstrap.py --doctor                   # 必须全绿
```
