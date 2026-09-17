#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""影视制作流水线：工具链体检 + 新项目脚手架。

顶层（本仓库的 rules/ tools/ docs/）是**复用层**：装一次，所有短剧项目共用。
每个短剧项目是**独立层**：只有 schema/（场记台账）+ project/（素材）+ README。

用法：
    python3 tools/bootstrap.py --doctor                    # 体检：工具装齐没有、登录没有
    python3 tools/bootstrap.py 剧本.txt                     # 丢进剧本，默认落在 projects/<项目名>/
    python3 tools/bootstrap.py 剧本.txt -o ../我的新剧      # 也可以放仓库外

铺完之后，按 docs/08 的工序表走 N1 → N12；每道工序都跑场记核对。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from _console import IS_WINDOWS, PY, force_utf8_stdio, run_text

PIPELINE_HOME = Path(__file__).resolve().parent.parent      # 复用层根目录（本仓库）
MEANINGLESS_NAMES = ("新建文本文档", "未命名", "untitled", "新建")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# 缺失时给出的安装命令（只列需要主动安装的）；按平台分两套，不要互相照抄
INSTALL_HINTS = {
    "python3": "brew install python@3",
    "git": "xcode-select --install",
    "jq": "brew install jq",
    "magick": "brew install imagemagick",
    "ffmpeg": "brew install ffmpeg-full（keg-only，见下条）",
    "ffprobe": "随 ffmpeg-full 一起装",
    "ffmpeg-full": "brew install ffmpeg-full",
    "tar": "系统自带，不该缺",
    "shasum": "系统自带，不该缺",
    "higgsfield": "curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh",
}
WINDOWS_HINTS = {
    "python": "scoop install python（或 winget install Python.Python.3.13）",
    "git": "scoop install git（或 winget install Git.Git）",
    "jq": "scoop install jq",
    "magick": "scoop install imagemagick（或 winget install ImageMagick.ImageMagick）",
    "ffmpeg": "scoop install ffmpeg（gyan.dev full_build，装完就在 PATH 上）",
    "ffprobe": "随 ffmpeg 一起装（scoop install ffmpeg）",
    "tar": r"Win10 1803+ 自带 C:\Windows\System32\tar.exe；否则 scoop install tar",
    "certutil": r"系统自带，不该缺（Windows 上没有 shasum，用它算哈希）",
    "higgsfield": "npm install -g --allow-scripts=@higgsfield/cli @higgsfield/cli"
                  "（官方 Windows 路径；install.sh 只支持 macOS / Linux；"
                  "npm 12 默认拦 postinstall，不加 --allow-scripts 会装出没有二进制的空壳）",
}


def binary_list() -> list[str]:
    """本机要核验的命令行工具。Windows 用 python + certutil 顶替 python3 + shasum。"""
    if IS_WINDOWS:
        return ["python", "node", "git", "tar", "certutil", "jq", "magick", "ffmpeg", "ffprobe"]
    return ["python3", "node", "git", "tar", "shasum", "jq", "magick", "ffmpeg", "ffprobe"]


def credential_candidates() -> list[Path]:
    """Higgsfield 登录态的可能位置。登录态由 CLI 自己写，这里只用来提示，不做校验。"""
    found: list[Path] = []
    env_path = os.environ.get("HIGGSFIELD_CONFIG_PATH", "").strip()
    if env_path:
        found.append(Path(env_path).expanduser())
    # 实测：Windows 上也是 ~/.config/higgsfield/credentials.json，不是 %APPDATA%
    found.append(Path.home() / ".config/higgsfield/credentials.json")
    return found


def skill_link_hint(skill: str) -> str:
    """第三方 skill 怎么挂进来：macOS 用软链，Windows 用目录联接（不需要管理员权限）。"""
    if IS_WINDOWS:
        return (f'New-Item -ItemType Junction -Path "$env:USERPROFILE\\.agents\\skills\\{skill}" '
                f'-Target <{skill} 仓库根>')
    return f"仓库在 {PIPELINE_HOME.parent}/{skill} → 软链或复制到 ~/.agents/skills/"


def which_all(names: list[str]) -> list[tuple[str, str]]:
    """返回 (名称, 路径或空串)。"""
    return [(n, shutil.which(n) or "") for n in names]


def run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = run_text(cmd, timeout=timeout)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)


def audio_filters(ffmpeg: Path) -> set[str]:
    """ffmpeg 支持的滤镜名集合；字幕与文字叠加依赖 libass / freetype。"""
    if not ffmpeg.exists():
        return set()
    code, out = run([str(ffmpeg), "-hide_banner", "-filters"], timeout=30)
    return set(re.findall(r"^\s*\S+\s+(\w+)", out, re.M)) if code == 0 else set()


def doctor() -> int:
    hints = WINDOWS_HINTS if IS_WINDOWS else INSTALL_HINTS
    missing: list[str] = []
    print(f"一、本机二进制（{'Windows' if IS_WINDOWS else 'macOS / Linux'}）")
    for name, path in which_all(binary_list()):
        if path:
            print(f"  ✅ {name:<10} {path}")
        else:
            missing.append(name)
            print(f"  ❌ {name:<10} 缺失 → {hints.get(name, f'装一个 {name} 并放进 PATH')}")
    if shutil.which("node"):
        code, ver = run(["node", "-v"])
        m = re.match(r"v(\d+)", ver)
        if not m or int(m.group(1)) < 18:
            missing.append("node>=18")
            print(f"  ❌ node 版本 {ver} 低于 18：shuohao-skills 的脚本要求 ≥18")
        else:
            print(f"  ✅ node {ver}（shuohao-skills 要求 ≥18）")

    print("\n二、ffmpeg 的字幕 / 文字叠加能力（带 libass + freetype 的构建才有）")
    if IS_WINDOWS:
        # Windows 没有 keg-only 那套：装的是一个完整构建，只要它在 PATH 最前面
        found = shutil.which("ffmpeg")
        filters = audio_filters(Path(found)) if found else set()
        if {"subtitles", "drawtext"} <= filters:
            print(f"  ✅ {found}（subtitles / drawtext 可用）")
        elif found:
            missing.append("ffmpeg(缺 subtitles/drawtext)")
            print(f"  ❌ {found} 缺 subtitles / drawtext → 换完整构建："
                  "scoop install ffmpeg 或 winget install Gyan.FFmpeg")
        else:
            print("  ❌ 找不到 ffmpeg（已计入第一节）→ "
                  "scoop install ffmpeg 或 winget install Gyan.FFmpeg")
        print("  ℹ️  Windows 上这个 ffmpeg 在 PATH 上就行，不需要像 macOS 那样每次改 PATH（FF-001）")
    else:
        full = Path("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg")
        filters = audio_filters(full)
        if {"subtitles", "drawtext"} <= filters:
            print(f"  ✅ {full}（subtitles / drawtext 可用）")
        else:
            missing.append("ffmpeg-full")
            print(f"  ❌ {full} 缺失或缺滤镜 → brew install ffmpeg-full")
        print("  ⚠️  调用前必须 export PATH=\"/opt/homebrew/opt/ffmpeg-full/bin:$PATH\"，"
              "否则字幕与文字叠加全废（FF-001）")

    print("\n三、higgsfield CLI 与登录态")
    higgs = shutil.which("higgsfield")
    if not higgs:
        missing.append("higgsfield")
        print(f"  ❌ 未安装 → {hints['higgsfield']}")
    else:
        code, ver = run([higgs, "--version"])
        print(f"  ✅ {ver or '已安装'}")
        code, status = run([higgs, "account", "status"], timeout=30)
        if code == 0:
            # 不回显账号邮箱：终端输出会进日志与上下文
            print(f"  ✅ 登录态正常：{EMAIL_RE.sub('***@***', status)}")
            print("  ℹ️  S4/S5 开跑前再确认一次余额")
        elif "workspace" in status.lower():
            # 换新机器第一次就是这条：登录态已写，但还没选计费工作区
            missing.append("higgsfield 工作区")
            print("  ⚠️  没选工作区（新机器第一次必碰）→ "
                  "higgsfield workspace list 看 id，再 higgsfield workspace set <workspace_id>")
            print("     它同时能验登录：list 报未登录，就先 higgsfield auth login")
        else:
            missing.append("higgsfield 登录")
            print(f"  ❌ 未登录 → higgsfield auth login（设备码流程，浏览器授权）\n     {status[:120]}")
        cred = next((c for c in credential_candidates() if c.exists()), None)
        guard = "不入库、不回显、不截图" if IS_WINDOWS else "chmod 600、不入库、不回显"
        if cred:
            print(f"  ✅ 凭证文件 {cred}（按密钥对待：{guard}）")
        else:
            print(f"  ⚠️  没找到凭证文件（未登录时本来就没有；位置由 CLI 自己管，"
                  f"可用 HIGGSFIELD_CONFIG_PATH 指定）。按密钥对待：{guard}")

    print("\n四、第三方 skills")
    homes = [Path.home() / ".codex/skills", Path.home() / ".agents/skills"]
    if IS_WINDOWS:
        shuohao_hint = (f"git clone https://github.com/eternityspring/shuohao-skills.git "
                        f"{PIPELINE_HOME.parent}\\shuohao-skills，再在 Git Bash 里跑 "
                        f"./scripts/install.sh --codex（跑不通就把 skills/novel-* 目录联接进 ~/.codex/skills/）")
    else:
        shuohao_hint = (f"git clone https://github.com/eternityspring/shuohao-skills.git "
                        f"{PIPELINE_HOME.parent}/shuohao-skills && cd $_ && ./scripts/install.sh --codex")
    for skill, hint in (
        ("ffmpeg-skill", "npx ffmpeg-skill --codex"),
        ("seedance-prompt-skill", skill_link_hint("seedance-prompt-skill")),
    ):
        hit = next((h / skill for h in homes if (h / skill).exists()), None)
        if hit:
            print(f"  ✅ {skill:<22} {hit}")
        else:
            missing.append(skill)
            print(f"  ❌ {skill:<22} 未安装 → {hint}")
    print("  ―― 短剧前段（shuohao-skills：大纲 → 角色 → 美术 → 剧本 → 分镜）")
    for skill in ("novel-outline", "novel-characters", "novel-art", "novel-script",
                  "novel-storyboard"):
        hit = next((h / skill for h in homes if (h / skill).exists()), None)
        if hit:
            print(f"  ✅ {skill:<22} {hit}")
        else:
            missing.append(skill)
            print(f"  ❌ {skill:<22} 未安装 → {shuohao_hint}")
    print("  ―― 本仓库自建的编排 skill（软链必须指向本仓库，指向别处就是死链）")
    own = next((h / "story-to-video" for h in homes if (h / "story-to-video").exists()), None)
    if own:
        print(f"  ✅ {'story-to-video':<22} {own} → {own.resolve()}")
        if own.resolve() != (PIPELINE_HOME / "skills/story-to-video").resolve():
            print(f"  ⚠️  它指向 {own.resolve()}，不是本仓库的 skills/story-to-video —— 换过目录名就要重建软链")
    else:
        missing.append("story-to-video")
        if IS_WINDOWS:
            link = (f'New-Item -ItemType Junction -Path "$env:USERPROFILE\\.codex\\skills\\story-to-video" '
                    f'-Target "{PIPELINE_HOME}\\skills\\story-to-video"')
        else:
            link = f"ln -sfn {PIPELINE_HOME}/skills/story-to-video ~/.codex/skills/story-to-video"
        print(f"  ❌ {'story-to-video':<22} 未安装 → {link}")
    plugin = Path.home() / ".codex/plugins/cache/personal"
    repo = PIPELINE_HOME.parent / "higgsfield-skills"
    # 官方 9 个 skill：装法有两种（插件市场 / 直接把仓库里的 skill 目录挂进 skills/），两种都认
    hf_skills = sorted({p.name for h in homes for p in h.glob("higgsfield-*") if (p / "SKILL.md").exists()})
    if hf_skills:
        print(f"  ✅ higgsfield 官方 skill：{', '.join(hf_skills)}")
    elif plugin.exists() and any(plugin.glob("*higgsfield*")):
        print("  ✅ higgsfield 官方插件已安装")
    else:
        print(f"  ⚠️  higgsfield 官方 skill 未装（仓库在 {repo}）→ git clone "
              f"https://github.com/higgsfield-ai/skills.git {repo}，再把这次要用的 "
              f"higgsfield-generate 目录联接进 ~/.codex/skills/；只出图出视频的话，直接用 CLI 也能跑")

    print("\n五、发布环节")
    print("  ℹ️  抖音发布没有 API，人工上传：账号注册 + 实名认证 + 创作者中心上传（不进自动化）")

    if missing:
        print(f"\n体检结果：{len(missing)} 项待处理 —— {'、'.join(missing)}")
        return 1
    print("\n体检结果：全部就绪")
    return 0


def derive_project_name(script: Path) -> str:
    stem = script.stem.strip()
    if len(stem) >= 3 and not any(k in stem for k in MEANINGLESS_NAMES):
        return stem.rstrip("！!？?。 ")
    first = next((ln.strip() for ln in script.read_text(encoding="utf-8").splitlines() if ln.strip()), "")
    first = re.sub(r"^(剧名|title)[:：]\s*", "", first)
    return (first or stem).rstrip("！!？?。 ") or "未命名项目"


def bootstrap(script: Path, out_dir: Path) -> int:
    if not script.is_file():
        print(f"找不到剧本：{script}", file=sys.stderr)
        return 1
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"目标目录已存在且非空：{out_dir}", file=sys.stderr)
        return 1

    name = derive_project_name(script)
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    schema = out_dir / "schema"
    for d in (schema, out_dir / "project/raw", out_dir / "project/delivery",
              *(out_dir / f"project/work/{w}" for w in ("assets", "keyframes", "clips", "audio", "edit"))):
        d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(script, out_dir / "project/raw" / script.name)

    # 骨架来自复用层的 templates/schema/（列定义与字段字典的唯一出处）
    template = PIPELINE_HOME / "templates/schema"
    for src in sorted(template.iterdir()):
        shutil.copy2(src, schema / src.name)

    bible_path = schema / "story_bible.json"
    bible = json.loads(bible_path.read_text(encoding="utf-8"))
    bible["meta"].update({
        "project_name": name,
        "script_file": f"project/raw/{script.name}",
        "script_sha256": digest,
        "updated_at": date.today().isoformat(),
    })
    # 台账统一 LF：Windows 上文本模式默认写 CRLF，同一份 schema 在 Mac / Windows 之间会整文件 diff
    bible_path.write_text(json.dumps(bible, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")

    assets_path = schema / "assets.json"
    assets = json.loads(assets_path.read_text(encoding="utf-8"))
    assets["project_name"] = name
    assets_path.write_text(json.dumps(assets, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8", newline="\n")

    (out_dir / "README.md").write_text(f"""# {name}

> 由影视制作流水线脚手架生成　｜　剧本：`project/raw/{script.name}`　｜　sha256：`{digest[:12]}…`

**当前阶段**：`S0 已初始化`，下一步走 N1（题材与时代识别）。

复用层（规则、脚本、通用文档）不复制进本项目，统一在：
`{PIPELINE_HOME}`

## 下一步

```bash
cd {PIPELINE_HOME}
{PY} tools/check_consistency.py --schema-dir {schema} --draft   # 骨架自检，应 0 错误
```

然后让 Codex 按 skill `story-to-video` 跑 N1 → N12：
读剧本产出 `schema/story_bible.json`（题材 / 人物 / 场景 / 道具 / 音色 / 分集），
每一步改完文件就回跑校验器；定妆图定稿（G2）、视觉十项（G4）、成片通看（G6）三处必须停下来等作者。
""", encoding="utf-8", newline="\n")

    print(f"项目已铺好：{out_dir}")
    print(f"  项目名      {name}")
    print(f"  剧本指纹    {digest[:12]}…")
    print(f"  schema      {schema}")
    print(f"  复用层      {PIPELINE_HOME}（rules / tools / docs，未复制）")
    print("\n下一步：")
    print(f"  {PY} {PIPELINE_HOME / 'tools/check_consistency.py'} --schema-dir {schema} --draft")
    return 0


def main() -> int:
    force_utf8_stdio()
    ap = argparse.ArgumentParser(description="影视制作流水线：工具链体检 + 新项目脚手架")
    ap.add_argument("script", nargs="?", help="剧本 txt")
    ap.add_argument("-o", "--out", default="", help="新项目目录")
    ap.add_argument("--doctor", action="store_true", help="只体检工具链")
    args = ap.parse_args()

    if args.doctor or not args.script:
        return doctor()
    script = Path(args.script).expanduser()
    if not script.is_file():
        print(f"找不到剧本：{script}", file=sys.stderr)
        return 1
    # 默认落在复用层的 projects/ 下；要放仓库外就显式 -o
    out = Path(args.out).expanduser() if args.out \
        else PIPELINE_HOME / "projects" / derive_project_name(script)
    return bootstrap(script, out)


if __name__ == "__main__":
    sys.exit(main())
