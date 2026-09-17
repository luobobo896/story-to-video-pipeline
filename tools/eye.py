#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看图限流器：只把 ≤300KB 的 JPEG 交给模型的眼睛（零依赖，标准库 + ffmpeg）。

    python3 tools/eye.py project/work/keyframes/EP01-SC01-SH001_v001.png
    python3 tools/eye.py project/work/clips/EP01-SC01-SH001_v001.mp4        # 3x2 拼图
    python3 tools/eye.py project/work/edit/DEMO_9x16_v004.mp4 --tiles 4x3
    python3 tools/eye.py project/work/edit/DEMO_9x16_v004.mp4 --at 12.5    # 单帧
    python3 tools/eye.py --selftest

为什么必须走这里：定妆图/关键帧是 4–9MB 的 PNG，QA 拼图约 2MB。把它们内联给模型，
单次请求体很快超过 40MB，被 DeepSeek 前面的 CDN 网关 413 掉（实测边界：body 40MB 放行、
48MB 拒）。同一画面压成 30–250KB 后，判断构图/穿帮/字幕位置照样够用。

输出永远是 JPEG（默认 `<源同目录>/<源名>.eye.jpg`，视频拼图是 `.eye_sheet.jpg`），
按阶梯降尺寸与质量直到 ≤ --max-kb，压不到就直接报错而不是悄悄塞一张大图。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from _console import force_utf8_stdio, run_text

MAX_KB = 300
# 实测：定妆图 1280px/q5 = 65KB，9:16 的 3x2 拼图 1280px/q5 = 158KB，
# 都远在 300KB 以内，脸和字幕还看得清。超限才降级到下一档。
LADDER = [(1280, 5), (1024, 7), (768, 9)]


def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return run_text(cmd)


def probe(path: str) -> dict:
    out = run(["ffprobe", "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", path])
    if out.returncode != 0:
        die(f"ffprobe 读不了 {path}：{out.stderr.strip()}")
    return json.loads(out.stdout)


def fps_of(stream: dict) -> float:
    num, _, den = (stream.get("r_frame_rate") or "0/1").partition("/")
    try:
        return float(num) / float(den or 1)
    except ValueError:
        return 0.0


def has_motion(meta: dict) -> bool:
    """是不是"能放"的视频。单帧图片（png_pipe/jpeg_pipe）在 ffprobe 里也算 video 流，
    但它们没有时长，只能当静态图压一张。"""
    fmt = meta.get("format", {}).get("format_name", "")
    if "pipe" in fmt:
        return False
    return any(s.get("codec_type") == "video" for s in meta["streams"])


def encode(args: list[str], out: Path) -> bool:
    res = run(["ffmpeg", "-v", "error", "-y", *args, "-frames:v", "1", str(out)])
    if res.returncode != 0:
        die(f"ffmpeg 失败：{res.stderr.strip()}")
    return out.exists() and out.stat().st_size > 0


def shrink(src: str, width: int, quality: int, out: Path, seek: str | None = None) -> bool:
    vf = f"scale='min({width},iw)':-2:flags=lanczos"
    args = (["-ss", seek] if seek else []) + ["-i", src, "-vf", vf, "-q:v", str(quality)]
    return encode(args, out)


def sheet(src: str, cols: int, rows: int, width: int, quality: int, out: Path, meta: dict) -> bool:
    video = next(s for s in meta["streams"] if s.get("codec_type") == "video")
    dur = float(meta.get("format", {}).get("duration") or video.get("duration") or 0)
    if dur <= 0:
        die("视频没有可用时长，出不了拼图；用 --at T 取单帧")
    n = cols * rows
    frames_avail = int(fps_of(video) * dur)
    if frames_avail and n > frames_avail:  # tile 等不到不存在的帧，输出会是空文件
        cols, rows = max(1, min(cols, frames_avail)), 1
        n = cols * rows
    tile_w = max(2, (width // cols) // 2 * 2)
    vf = (f"fps={n / dur:.6f},scale={tile_w}:-2:flags=fast_bilinear,"
          f"tile={cols}x{rows}:padding=2:margin=2:color=0x202020")
    return encode(["-i", src, "-vf", vf, "-q:v", str(quality)], out)


def main() -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(description="把图片/视频压成 ≤300KB 的 JPEG 再看")
    parser.add_argument("input", nargs="?", help="图片或视频")
    parser.add_argument("--at", help="取单帧的时间点，如 12.5")
    parser.add_argument("--tiles", default="3x2", help="视频拼图网格 COLSxROWS（默认 3x2）")
    parser.add_argument("-o", "--out", help="输出路径，只出 JPEG")
    parser.add_argument("--max-kb", type=int, default=MAX_KB, help=f"体积上限 KB（默认 {MAX_KB}）")
    parser.add_argument("--selftest", action="store_true", help="自检：合成素材验证压缩与上限")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.input:
        parser.error("要给出图片或视频路径（或 --selftest）")

    src = Path(args.input)
    if not src.exists():
        die(f"文件不存在：{src}")
    meta = probe(str(src))
    moving = has_motion(meta)
    src_kb = src.stat().st_size // 1024

    if args.out:
        out = Path(args.out)
        if out.suffix.lower() not in (".jpg", ".jpeg"):
            print(f"只出 JPEG：{out} -> {out.with_suffix('.jpg')}")
            out = out.with_suffix(".jpg")
    elif moving and not args.at:
        out = src.with_name(f"{src.stem}.eye_sheet.jpg")
    elif args.at:
        out = src.with_name(f"{src.stem}.eye_{args.at.replace('.', '_')}s.jpg")
    else:
        out = src.with_name(f"{src.stem}.eye.jpg")
    out.parent.mkdir(parents=True, exist_ok=True)

    if moving and not args.at:
        try:
            cols, rows = (int(x) for x in args.tiles.lower().split("x"))
        except ValueError:
            die("--tiles 要形如 3x2")
        ladder, build = LADDER, lambda w, q: sheet(str(src), cols, rows, w, q, out, meta)
        kind = f"{cols}x{rows} 拼图"
    else:
        seek = args.at if moving else None
        ladder, build = LADDER, lambda w, q: shrink(str(src), w, q, out, seek)
        kind = "单帧" if moving else "图片"

    kb = 0
    for width, quality in ladder:
        if not build(width, quality):
            die("ffmpeg 没写出文件")
        kb = out.stat().st_size // 1024
        if kb <= args.max_kb:
            break
    else:
        die(f"{kind}压不到 {args.max_kb}KB（最小仍 {kb}KB）：{out}")

    print(f"{kind}：{src_kb}KB -> {kb}KB（{width}px/q{quality}）")
    print(out.resolve())
    return 0


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        clip, still = Path(tmp) / "t.mp4", Path(tmp) / "t.png"
        # 合成素材：2s 1080p 视频 + 1080p 单帧。用带细节的源（testsrc2 / mandelbrot），
        # 纯色块压得太狠，测不出"确实变小了"
        for cmd in (["-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=25:duration=2",
                     "-pix_fmt", "yuv420p", str(clip)],
                    ["-f", "lavfi", "-i", "mandelbrot=size=1920x1080",
                     "-frames:v", "1", "-update", "1", str(still)]):
            if subprocess.run(["ffmpeg", "-v", "error", "-y", *cmd]).returncode != 0:
                print("自检失败：合成素材没造出来（ffmpeg 不可用？）")
                return 1
        for src, expect in ((clip, ".eye_sheet.jpg"), (still, ".eye.jpg")):
            res = run([sys.executable, __file__, str(src)])
            if res.returncode != 0:
                print(f"自检失败：{src.name}\n{res.stderr}")
                return 1
            out = src.with_name(src.stem + expect)
            kb = out.stat().st_size // 1024 if out.exists() else 0
            if not 0 < kb <= MAX_KB:
                print(f"自检失败：{out.name} 体积 {kb}KB，应 ≤{MAX_KB}KB")
                return 1
            if kb >= src.stat().st_size // 1024:
                print(f"自检失败：{out.name} 没比源文件小")
                return 1
            print(f"  {src.name} {src.stat().st_size // 1024}KB -> {out.name} {kb}KB")
        over = run([sys.executable, __file__, str(still), "--max-kb", "1"])
        if over.returncode == 0:
            print("自检失败：压不到上限时应当报错")
            return 1
    print("自检通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
