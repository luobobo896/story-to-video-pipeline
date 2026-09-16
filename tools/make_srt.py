#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 schema/shots.csv 生成 SRT 字幕。

时间轴按 shots.csv 的 duration_s 顺序累加；只输出 dialogue 非空的镜头。
【内心OS】前缀会被保留为普通台词文本（去掉标记），因为旁白与台词都要字幕。

用法：
    python3 tools/make_srt.py                          # 全部镜头 -> EP01.srt
    python3 tools/make_srt.py --shots EP01-SC01        # 只取某场
    python3 tools/make_srt.py -o <路径>
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(text: str, max_chars: int) -> str:
    """超过 max_chars 就在标点处折成两行（SRT 用 \\N 换行）。

    单条字幕过长在移动端会挤成一坨或超出安全区，所以宁可折行也不缩字号。
    """
    if len(text) <= max_chars:
        return text
    half = len(text) / 2
    best = None
    for i, ch in enumerate(text):
        if ch in "，。！？；：、":
            d = abs(i + 1 - half)
            if best is None or d < best[0]:
                best = (d, i + 1)
    cut = best[1] if best else int(half)
    return text[:cut] + "\\N" + text[cut:]


def main() -> int:
    parser = argparse.ArgumentParser(description="shots.csv -> SRT")
    parser.add_argument("--schema-dir",
                        default=str(Path(__file__).resolve().parent.parent / "schema"))
    parser.add_argument("--shots", default="", help="按 shot_id 前缀过滤，如 EP01-SC01")
    parser.add_argument("-o", "--output", default="")
    parser.add_argument("--max-chars", type=int, default=20,
                        help="单行字幕字数上限，超出折行（默认 20）")
    args = parser.parse_args()

    shots_path = Path(args.schema_dir) / "shots.csv"
    if not shots_path.exists():
        print(f"找不到 {shots_path}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(shots_path.open(encoding="utf-8")))
    if args.shots:
        rows = [r for r in rows if (r.get("shot_id") or "").startswith(args.shots)]

    out_path = Path(args.output) if args.output else \
        Path(args.schema_dir).parent / "project/work/edit/EP01.srt"

    cursor = 0.0
    cues = []
    overflow = []
    for r in rows:
        try:
            dur = float(r.get("duration_s") or 0)
        except ValueError:
            dur = 0.0
        start, end = cursor, cursor + dur
        cursor = end
        text = (r.get("dialogue") or "").strip()
        if not text:
            continue
        text = text.replace("【内心OS】", "").strip()

        # 字幕跟**真实语音时长**走，不跟分镜表的理论时长走。
        # 没有音频时退回镜头时长（草稿阶段）。
        raw_audio = (r.get("audio_duration_s") or "").strip()
        try:
            audio = float(raw_audio) if raw_audio else 0.0
        except ValueError:
            audio = 0.0
        cue_end = start + audio if audio else end
        if cue_end > end:
            # 语音比镜头长：字幕不能越到下一镜，截到本镜末并记录溢出
            overflow.append((r.get("shot_id", ""), audio, dur))
            cue_end = end
        cues.append((start, cue_end, wrap(text, args.max_chars), r.get("shot_id", "")))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for i, (start, end, text, sid) in enumerate(cues, start=1):
            f.write(f"{i}\n{ts(start)} --> {ts(end)}\n{text}\n\n")

    print(f"写入 {out_path}：{len(cues)} 条字幕，覆盖 {len(rows)} 个镜头，总时长 {cursor:.2f}s")
    if overflow:
        print(f"注意：{len(overflow)} 条语音长于镜头，字幕已截到镜头末（需改分镜或改台词）：")
        for sid, a, d in overflow:
            print(f"  {sid}: 语音 {a:.2f}s > 镜头 {d:g}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
