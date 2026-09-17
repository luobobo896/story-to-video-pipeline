#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定位项目：复用层的脚本要同时服务 projects/ 下的项目，以及仓库外的项目。

规则（按优先级）：
  1. 显式给了路径就用它；
  2. 否则看仓库根下的 schema/（兼容老布局）；
  3. 否则看 projects/*/schema —— 只有一个项目时自动选中；
  4. 有多个项目时必须显式指定：--schema-dir <项目>/schema 或 --project <项目>。
"""

from __future__ import annotations

import sys
from pathlib import Path

from _console import PY

PIPELINE_HOME = Path(__file__).resolve().parent.parent


def _candidates() -> list[Path]:
    found: list[Path] = []
    if (PIPELINE_HOME / "schema").is_dir():
        found.append(PIPELINE_HOME / "schema")
    projects = PIPELINE_HOME / "projects"
    if projects.is_dir():
        found.extend(sorted(p / "schema" for p in projects.iterdir()
                            if (p / "schema").is_dir()))
    return found


def resolve_schema_dir(explicit: str = "") -> Path | None:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_dir():
            print(f"找不到 schema 目录：{path}", file=sys.stderr)
            return None
        return path
    found = _candidates()
    if len(found) == 1:
        return found[0]
    if not found:
        print(f"找不到任何项目：先跑 {PY} tools/bootstrap.py <剧本.txt> -o <项目目录>",
              file=sys.stderr)
        return None
    print("有多个项目，必须显式指定：", file=sys.stderr)
    for path in found:
        print(f"  --schema-dir {path}", file=sys.stderr)
    return None


def resolve_project_root(explicit: str = "") -> Path | None:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not (path / "schema").is_dir():
            print(f"不是项目目录（缺 schema/）：{path}", file=sys.stderr)
            return None
        return path
    schema = resolve_schema_dir()
    return schema.parent if schema else None
