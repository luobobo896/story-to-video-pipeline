#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨平台控制台小工具（Windows 适配，被本目录其它脚本 import）。

中文 Windows 的标准流默认编码是 cp936（GBK），两个后果：
  1. 打印 ✅ / ❌ / ⚠️ 这类字符直接 UnicodeEncodeError，脚本当场崩；
  2. 输出重定向到文件或管道时（CI、日志、别的程序读走），中文编码与 UTF-8 读取方对不上，全是乱码。

所以每个脚本入口先调一次 force_utf8_stdio()。macOS / Linux 本来就是 UTF-8，调它只是把
输出固定下来，不改行为。

PY 是"给别人照着敲的"解释器名：Windows 上是 python，其余平台是 python3。

另外补一个 subprocess 包装：text=True 时 Python 用**本机 locale 编码**（中文 Windows 是
cp936）解码子进程输出，而 ffmpeg / higgsfield 之类吐出的是 UTF-8 —— 读线程会抛
UnicodeDecodeError，报错内容直接丢掉，出问题时看不到原因。
"""

from __future__ import annotations

import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"
PY = "python" if IS_WINDOWS else "python3"


def force_utf8_stdio() -> None:
    """把 stdout / stderr 切到 UTF-8；脏字符降级替换而不是抛异常。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)   # 非文本流时可能没有
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass   # 流已关闭或被重定向成不支持重配置的对象：保持原样，不要因适配崩掉


def run_text(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    """跑子进程并以 UTF-8 读回输出；脏字节替换掉，绝不因为解码失败丢报错。"""
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
