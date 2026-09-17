# 11 · Windows 换机：装什么 / 命令怎么写 / 哪里和 macOS 不一样

> 回答一件事：**在 Windows 上从零到能跑，要装什么、命令怎么写、哪些 macOS 步骤在这里不成立。**
> 与 [09-toolchain-setup.md](09-toolchain-setup.md)（macOS 实测）配对看，本文只写差异和 Windows 自己的坑。
> 事实核验日期：2026-09-17，Windows 11 x64 + scoop + fnm(node 24.19) + npm 12.0.2。写了「实测」的都是在这台机器上真跑通的。

一条命令体检：

```powershell
python tools\bootstrap.py --doctor
```

---

## 一、先记住三件与 macOS 不同的事

| macOS 的做法 | Windows 上等价的做法 | 为什么 |
|---|---|---|
| `python3 xxx.py` | `python xxx.py` | Windows 的解释器名是 `python`；scoop 的 shim 也提供 `python3`，但不保证每台机器都有 |
| `brew install ffmpeg ffmpeg-full`，每次调用前 `export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"` | `scoop install ffmpeg` 或 `winget install Gyan.FFmpeg`，装完就在 PATH 上，**不用每次改 PATH** | macOS 的 Homebrew 把「普通 ffmpeg」和 keg-only 的 ffmpeg-full 分开；Windows 没有这个分裂，gyan.dev 的构建自带 libass + libfreetype（实测 `subtitles` / `drawtext` / `ass` / `vidstabdetect` 全在） |
| `ln -s <仓库> ~/.codex/skills/xxx` | `New-Item -ItemType Junction -Path ... -Target ...` | Windows 建符号链接要开发者模式或管理员权限；**目录联接（Junction）不需要**，效果一样：仓库改了 skill 立刻生效，不分叉 |

`tools/` 下的脚本已按平台区分：体检输出哪一节、给什么安装命令、打印 `python` 还是 `python3`，都由脚本自己判断，不用记。

---

## 二、系统二进制

scoop 与 winget 二选一，下面是实测过的包名与结果：

| 依赖 | 装 | 验 | 干什么 |
|---|---|---|---|
| `python` | `scoop install python` / `winget install Python.Python.3.13` | `python -V` | 全部脚本（要 3.10+；实测 3.14.7） |
| `git` | `scoop install git` / `winget install Git.Git` | `git --version` | `schema/` 与文档的版本管理 |
| `jq` | `scoop install jq` | `jq --version` | 查 `schema/*.json` |
| `ffmpeg` / `ffprobe` | `scoop install ffmpeg` / `winget install Gyan.FFmpeg` | `ffmpeg -version` | 规格核对、拼接转码、字幕烧录、`eye.py` 压图 |
| ImageMagick `magick` | `scoop install imagemagick` / `winget install ImageMagick.ImageMagick` | `magick -version` | 图片规格统一、拼版、帧差测量（`rules/ME` 的测量方法） |
| `tar` | Windows 10 1803+ 自带 | `tar --version` | 归档包 |
| `certutil` | 系统自带 | `certutil -hashfile <文件> SHA256` | 手工核对剧本指纹与资产哈希，顶替 macOS 的 `shasum`（脚本内部用 Python `hashlib`，不依赖它） |
| `node` / `npx` | `scoop install nodejs`，或本机已有的 fnm | `node -v`（≥18；实测 24.19.0） | 装第三方 skill、跑 shuohao-skills 的 `.mjs` 脚本 |

**两个实测坑**：

1. `scoop install imagemagick` 在这台机器上失败了 —— scoop 要先装解包工具 `innounp`，而它的下载地址返回 404（上游 manifest 问题）。改走 `winget install ImageMagick.ImageMagick` 一次成功（装到 `C:\Program Files\ImageMagick-7.1.2-Q16-HDRI`）。
2. winget 写的是**机器级 PATH**，当前已经打开的终端看不到 `magick`，重开一个终端（或临时 `$env:Path = "$env:Path;C:\Program Files\ImageMagick-7.1.2-Q16-HDRI"`）才认。

---

## 三、ffmpeg：Windows 上只有一个概念

macOS 要装两个是因为 Homebrew 的普通 `ffmpeg` 没带 libass / freetype；Windows 没这个问题。实测 `scoop install ffmpeg` 装的是 `ffmpeg 9.0-full_build-www.gyan.dev`，字幕与文字叠加要用的滤镜一个不缺：

```powershell
scoop install ffmpeg          # 主 bucket 的 ffmpeg：下载 gyan.dev 的 full_build
winget install Gyan.FFmpeg    # 等价替代

ffmpeg -hide_banner -filters | Select-String -Pattern "subtitles|drawtext"   # 两条都要有输出
```

实测 `subtitles` / `drawtext` / `ass` / `vidstabdetect` / `vidstabtransform` 全部可用，**不需要像 macOS 那样每次前置 PATH**（FF-001）。手工解压便携包、又不想改系统 PATH 时，只影响当前会话：

```powershell
$env:Path = "D:\tools\ffmpeg\bin;$env:Path"
```

项目脚本用 `shutil.which("ffmpeg")` 找二进制，所以只要这个目录在 PATH 最前面，字幕相关的活儿就会走它。

---

## 四、higgsfield CLI：Windows 走 npm，不走 install.sh

官方 `install.sh` 里写死了只支持 darwin / linux，Windows 上跑会直接 `Unsupported OS`。Windows 的官方路径是 npm 包：

```powershell
npm install -g --allow-scripts=@higgsfield/cli @higgsfield/cli   # 官方跨平台安装（Windows × x64 / arm64）
higgsfield --version        # 实测 1.1.25，与 macOS 那台同一版本

higgsfield auth login       # 浏览器 OAuth（自动打开授权页，终端等回调）
higgsfield workspace list   # 看工作区 id、套餐与余额
higgsfield workspace set <workspace_id>   # 换新机器必须选一次
higgsfield account status   # 实测输出形如：<账号> — basic plan, NN.N credits
higgsfield model list       # 模型 ID 的唯一口径，文档会滞后
```

**`--allow-scripts` 不能省**：npm 12 默认拦掉依赖的 postinstall 脚本，而这个包的 postinstall 才是「下载当前平台官方二进制」那一步。省掉它 npm 会报 `added 1 package` 看着成功，但 `higgsfield` 命令底下没有二进制。

失败信号（Windows 实测）：

| 现象 | 原因 | 处置 |
|---|---|---|
| `Error: Not authenticated.` + `Hint: Run: hf auth login` | 没有登录态 | `higgsfield auth login` |
| `Error: No workspace selected.` + `Hint: Run: hf workspace set <workspace_id>` | 登录态可能有、工作区一定没选（新机器第一次必碰） | 先 `higgsfield workspace list`：能列出工作区说明已登录，再 `workspace set <id>`；列不出来就先 `auth login` |
| `higgsfield` 不是内部或外部命令 | npm 全局 bin 目录不在 PATH | `npm prefix -g` 查目录，加进 PATH 后重开终端 |

第 2 条值得记一笔：没选工作区时 `account status` **返回的是「No workspace selected」而不是「未登录」**（退出码 4），所以看到这一条不能直接断定登录态坏了。`workspace list` 一次能同时看出两件事。

---

## 五、skills：挂载方式换掉，其余照旧

本仓库自带的编排 skill（目录联接，不需要管理员权限）：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.codex\skills\story-to-video" -Target "<本仓库>\skills\story-to-video"

Get-Item "$env:USERPROFILE\.codex\skills\story-to-video" | Select-Object Name,LinkType,Target
python tools\bootstrap.py --doctor      # 那一行应显示 ✅ 和解析后的真实路径
```

第三方 skill：

| skill | Windows 装法 | 实测结果 |
|---|---|---|
| `ffmpeg-skill` | `npx ffmpeg-skill --codex` → `~/.agents/skills/ffmpeg-skill` | ✅ 装上 1.17.3，45 个脚本 |
| `seedance-prompt-skill` | 源码放仓库外，`New-Item -ItemType Junction -Path "$env:USERPROFILE\.agents\skills\seedance-prompt-skill" -Target <仓库根>` | ✅ 联接可用 |
| `novel-*` 五件套 | `git clone https://github.com/eternityspring/shuohao-skills.git`，然后**手动目录联接** 5 个 skill（见下） | ✅ 五个自测合计 1170 项断言全过 |
| `higgsfield-generate` · `higgsfield-youtube-thumbnail`（官方 9 个里本项目要的两个） | `git clone https://github.com/higgsfield-ai/skills.git <仓库外目录>`，再把这两个目录联接进 `~/.codex/skills/` | ✅ 联接可用；`higgsfield generate cost` 实测返回 0.12 / 2 credits |

```powershell
foreach ($n in 'novel-outline','novel-characters','novel-art','novel-script','novel-storyboard') {
  New-Item -ItemType Junction -Path "$env:USERPROFILE\.codex\skills\$n" -Target "C:\Users\<用户名>\aiwork\shuohao-skills\skills\$n"
}
```

**`shuohao-skills/scripts/install.sh` 在 Windows 上不要直接跑**：它是 shell 脚本、用 `ln -sfn`，而 Git Bash 的 `ln -s` 实际是**复制**，脚本里的软链判断（`-L`）也不是 Windows 语义 —— 跑完会得到一份会分叉的副本，正好违反仓库「不复制」的约定。用上面的目录联接，语义与 macOS 的软链等价。

官方 skill 仓库同理：它自带的 `./setup` 也是 shell 脚本，而 `npx skills add higgsfield-ai/skills` 走的是**复制**（装完就不再跟仓库走）。想要 `git pull` 就生效，用克隆 + 目录联接：

```powershell
git clone https://github.com/higgsfield-ai/skills.git C:\Users\<用户名>\aiwork\higgsfield-skills
foreach ($n in 'higgsfield-generate','higgsfield-youtube-thumbnail') {
  New-Item -ItemType Junction -Path "$env:USERPROFILE\.codex\skills\$n" -Target "C:\Users\<用户名>\aiwork\higgsfield-skills\$n"
}
```

官方仓库里一共 9 个 skill，本项目只挂这两个：`higgsfield-generate` 是 N6 / N8 / N9 的必需项，`higgsfield-youtube-thumbnail` 给 N12 出封面；其余 7 个（soul-id / brandkit / product-photoshoot / marketplace-cards / websites / video-explainer / game-generation）README 第四节有明确不装的理由，要临时用再照上面一行加挂即可。

---

## 六、凭证

1. 实测位置：`~/.config/higgsfield/credentials.json` —— **Windows 上也是这个路径**（不是 `%APPDATA%`），即 `C:\Users\<用户名>\.config\higgsfield\credentials.json`。要换位置用 `HIGGSFIELD_CONFIG_PATH`。
2. 本项目脚本**不读**这个文件，只依赖 `higgsfield account status` 能返回账号（`--doctor` 的判定口径也是这一条）。
3. Windows 没有 `chmod 600`：要么保证它只在自己用户目录下，要么用 ACL 收紧，例如
   `icacls "<文件>" /inheritance:r /grant:r "%USERNAME%:R"`。
4. 不回显、不复制、不提交、不截图；泄漏就 `higgsfield auth logout` 再去平台侧处理。

---

## 七、中文 Windows 的编码（已在本仓库脚本里修掉）

中文 Windows 的 Python 默认编码是 cp936（GBK），实测踩到两处，都在脚本里修好了：

1. **标准流**：打印 ✅ / ❌ / ⚠️ 直接 `UnicodeEncodeError`，`--doctor` 第一条就崩；输出重定向到文件或管道时中文全是乱码。`tools/_console.py` 的 `force_utf8_stdio()` 把 stdout / stderr 固定成 UTF-8，6 个入口脚本都调了。
2. **子进程输出**：`subprocess.run(..., text=True)` 用本机 locale 解码子进程输出，而 ffmpeg / higgsfield 吐的是 UTF-8 —— 读线程抛 `UnicodeDecodeError`，**报错内容被丢掉**，等于出错时看不到原因。改用 `run_text()`（UTF-8 + `errors="replace"`）后修好；`eye.py` 自检是第一个暴露它的地方。

自查：

```powershell
python tools\bootstrap.py --doctor > doctor.txt
Get-Content doctor.txt -Encoding utf8 | Select-Object -First 3
python tools\eye.py --selftest    # 应输出两行体积对比并以「自检通过」结尾，且没有线程异常
```

自己写新脚本时，入口照抄 `from _console import force_utf8_stdio` + `force_utf8_stdio()`，跑外部命令用 `run_text()`。

---

## 八、Windows 实测的坑（这一节是换机的省钱清单）

| 坑 | 现象 | 处理 |
|---|---|---|
| npm 12 拦 postinstall | `npm install -g @higgsfield/cli` 说成功，`higgsfield` 却没有二进制 | 装的时候带 `--allow-scripts=@higgsfield/cli` |
| 登录后还要选工作区 | `account status` 报 `No workspace selected`，看着像没登录 | `workspace list` → `workspace set <id>` |
| `ffmpeg-skill` 的 doctor 报 1 项缺 | `filter:drawtext` 被判 missing：裸调 `drawtext` 没字体时 ffmpeg 直接崩（退出码 3221225477），不是干净报错 | **工具本身不受影响**：实测 `caption.py` 烧中文字幕、`graphics.py` 出标题卡都正常，它自己会解析 `C:\Windows\Fonts\msyh.ttc` 并传 `fontfile=`。只有你手写裸 ffmpeg 命令时才要自己加 `fontfile=` |
| scoop 装 ImageMagick 失败 | 卡在 `innounp` 的 404 | 改用 `winget install ImageMagick.ImageMagick` |
| winget 装的命令当前终端看不到 | `magick` 报「不是内部或外部命令」 | 重开终端（它写的是机器级 PATH） |
| Git Bash 的 `ln -s` 是复制 | shuohao-skills 的 `install.sh` 会做出一份副本 | 用 `New-Item -ItemType Junction` |
| 子进程报错读不出来 | 线程抛 `UnicodeDecodeError`，真正的 ffmpeg 报错丢了 | 用 `tools/_console.py` 的 `run_text()` |
| npm 装的 CLI 不能用裸名字调 | `subprocess.run(["higgsfield", …])` 报 `FileNotFoundError`：Windows 上装出来的是 `higgsfield.CMD`，CreateProcess 不做 PATHEXT 补全 | `shutil.which("higgsfield")` 要全路径再传（`tools/tts_batch.py` 已改成这样） |

---

## 九、换机 30 秒清单（PowerShell）

```powershell
scoop install python git jq ffmpeg nodejs
winget install ImageMagick.ImageMagick          # scoop 版卡在 innounp 的 404

npm install -g --allow-scripts=@higgsfield/cli @higgsfield/cli
higgsfield auth login
higgsfield workspace list ; higgsfield workspace set <workspace_id>
higgsfield account status

npx ffmpeg-skill --codex
git clone https://github.com/eternityspring/shuohao-skills.git C:\Users\<用户名>\aiwork\shuohao-skills
git clone https://github.com/MapleShaw/seedance2.0-prompt-skill.git C:\Users\<用户名>\aiwork\seedance-prompt-skill
git clone https://github.com/higgsfield-ai/skills.git C:\Users\<用户名>\aiwork\higgsfield-skills
# 再按第五节把这些目录联接进 ~/.codex/skills 与 ~/.agents/skills：
#   novel-* ×5、story-to-video、higgsfield-generate、higgsfield-youtube-thumbnail、seedance-prompt-skill

python "<本仓库>\tools\bootstrap.py" --doctor            # 必须全绿
python "<本仓库>\tools\check_consistency.py" --selftest  # 校验器自检
python "<本仓库>\tools\eye.py" --selftest                # 压图链路自检
```

抖音发布依然是人工步骤（没有公开上传 API），见 [09 第六节](09-toolchain-setup.md)。

---

## 十、Windows 实测结论（2026-09-17）

| 链路 | 结论 | 证据 |
|---|---|---|
| 工具链体检 `bootstrap.py --doctor` | ✅ | 二进制、ffmpeg 滤镜、6 个 skill 全绿 |
| 场记核对 `check_consistency.py` | ✅ | `--selftest` 七类注入错误全抓到；样例项目 0 错误 / 13 警告 |
| 压图限流 `eye.py` | ✅ | `--selftest`：视频 1376KB→66KB 拼图、图片 860KB→93KB，都 ≤300KB |
| 字幕生成 `make_srt.py` | ✅ | 样例项目 16 条字幕 / 28 镜 / 142.00s |
| 烧字幕（libass + 中文字体） | ✅ | 合成 3s 素材烧中文 SRT，抽帧人眼确认：微软雅黑渲染正常、自动折两行、避让抖音底部 UI |
| 文字叠加（drawtext + 中文字体） | ✅ | `graphics.py` 标题卡，抽帧确认中文正常 |
| 交付合规 `check.py --platform tiktok` | ✅ 工具可用 | 13 项检查正常输出（合成素材本身 16:9、响度不达标，属预期） |
| shuohao-skills 五件套 | ✅ | 1170 项断言全过（node 24.19） |
| higgsfield CLI | ✅ 已登录并选工作区 | 1.1.25；`account status` 返回 basic plan 与余额 |
| higgsfield 官方 skill | ✅ 已挂 `higgsfield-generate` + `higgsfield-youtube-thumbnail` | 目录联接；`model list`、`voices list`、`generate cost` 全部正常（估算 0.12 / 2 credits，不扣积分） |
| 出图调用（N6，`soul_location`） | ✅ 实测通过 | 16:9 空镜 2048×1152，24s 完成；扣 **0.12 积分**（55.2 → 55.08，与 docs/10 单价一致）；产物走 `tools/eye.py` 压到 59KB 并人眼确认 |
| 出视频调用（N8） | ✅ 实测通过（**换了模型**） | `seedance_2_0` 在 Basic 档被拦（fast/mini `Not found`、std 要 Pro，见 docs/10 复测节），改用 `seedance1_5` 4s/720p/首帧：34s 完成，**实扣 2.4 积分**，产出 1280×720 / 24fps / 4.04s |
| 配音调用（N9） | ✅ 实测通过 | `tools/tts_batch.py --shots EP01-SC04`：2 句 = 0.2 积分，实测时长 2.040s / 4.032s 并回填台账 |
| 剪辑成片（N10 / N11） | ✅ 实测通过 | SRT 烧录（微软雅黑）→ 挂配音 → 响度归一化 -14.2 LUFS / TP -1.5 → 横转竖 1080×1920；**9:16 分发版 `check.py --platform tiktok` 13 项 0 失败** |
