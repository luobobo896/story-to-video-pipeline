#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一次生成的作业结果回填到 schema/shots.csv 的指定镜头行。

用法：
    python3 tools/record_shot.py --shot EP01-SC01-SH001 \
        --set status=done --set clip_file=project/work/clips/xxx.mp4 \
        --set qa_identity=pass

只改指定列，其余不动；列名必须是表头里已有的，写错会直接报错而不是静默新增。
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _console import force_utf8_stdio  # noqa: E402
from _project import resolve_schema_dir  # noqa: E402


def main() -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(description="回填某个镜头的字段")
    parser.add_argument("--shot", required=True, help="shot_id，如 EP01-SC01-SH001")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="要写入的字段，可重复")
    parser.add_argument("--schema-dir",
                        default="", help="项目 schema 目录；不给则自动选中 projects/ 下唯一的项目")
    args = parser.parse_args()

    schema_dir = resolve_schema_dir(args.schema_dir)
    if schema_dir is None:
        return 1
    path = schema_dir / "shots.csv"
    if not path.exists():
        print(f"找不到 {path}", file=sys.stderr)
        return 1
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = list(csv.reader(io.StringIO("\n".join(lines))))
    header, data = rows[0], rows[1:]

    updates: dict[str, str] = {}
    for item in args.set:
        if "=" not in item:
            print(f"--set 需要 KEY=VALUE 形式：{item}", file=sys.stderr)
            return 1
        key, value = item.split("=", 1)
        if key not in header:
            print(f"不在表头里的列名：{key}（先确认 schema/shots.csv 的表头）", file=sys.stderr)
            return 1
        updates[key] = value

    hit = 0
    for row in data:
        if row and row[0] == args.shot:
            for key, value in updates.items():
                row[header.index(key)] = value
            hit += 1
    if hit != 1:
        print(f"匹配到 {hit} 行，应为 1 行：{args.shot}", file=sys.stderr)
        return 1

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(data)
    # 统一 LF：Windows 上文本模式默认写 CRLF，同一份 shots.csv 跨机器会整文件 diff
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    changed = " ".join(f"{k}={v}" for k, v in updates.items())
    print(f"已更新 {args.shot}: {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
