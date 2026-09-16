#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5 配音执行器：按 shots.csv 的台词与 assets.json 的音色绑定，批量生成台词音频。

做的事：
  1. 从 assets.json 读 voices[]，建立 角色 -> 音色 的绑定（VC-###）
  2. 逐条读 shots.csv 里 dialogue 非空的镜头
  3. 调 higgsfield text2speech_v2 生成，下载到 project/work/audio/
  4. 用 ffprobe 量出真实时长，回填 audio_file 与 audio_duration_s
  5. 台词长于镜头时**直接报出来**（rules 里 R8 的判定）

用法：
    python3 tools/tts_batch.py --dry-run          # 只列计划，不花钱
    python3 tools/tts_batch.py                    # 只跑缺音频的
    python3 tools/tts_batch.py --shots EP01-SC03  # 限定场次
    python3 tools/tts_batch.py --force            # 重生成已有音频
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _project import resolve_project_root  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema"
SHOTS = SCHEMA / "shots.csv"
AUDIO = ROOT / "project/work/audio"


def read_shots(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    import csv, io
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = list(csv.reader(io.StringIO("\n".join(lines))))
    header, data = rows[0], rows[1:]
    return header, [dict(zip(header, r)) for r in data]


def write_shots(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow([r.get(c, "") for c in header])
    path.write_text(buf.getvalue(), encoding="utf-8")


def voice_map() -> dict[str, dict[str, str]]:
    """VC-### -> {character_id, voice_id, voice_type, engine_variant}"""
    doc = json.loads((SCHEMA / "assets.json").read_text(encoding="utf-8"))
    return {v["asset_id"]: v for v in doc.get("voices", []) if v.get("asset_id")}


def probe_duration(path: Path) -> float | None:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def tts(text: str, voice: dict[str, str]) -> str | None:
    cmd = ["higgsfield", "generate", "create", "text2speech_v2",
           "--prompt", text,
           "--variant", voice.get("engine_variant") or "seed_speech",
           "--voice_type", voice.get("voice_type") or "preset",
           "--voice_id", voice["voice_id"],
           "--wait", "--json"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r'"result_url":\s*"([^"]+)"', out.stdout)
    if not m:
        print(f"    TTS 失败：{(out.stdout or out.stderr)[-200:]}", file=sys.stderr)
        return None
    return m.group(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="S5 批量配音")
    ap.add_argument("--shots", default="", help="按 shot_id 前缀过滤")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="重生成已有音频")
    ap.add_argument("--report", action="store_true", help="输出配音对照表 markdown")
    ap.add_argument("--project", default="",
                    help="项目根目录；不给则自动选中 projects/ 下唯一的项目")
    args = ap.parse_args()

    global ROOT, SCHEMA, SHOTS, AUDIO
    proj = resolve_project_root(args.project)
    if proj is None:
        return 1
    ROOT = proj
    SCHEMA, SHOTS = ROOT / "schema", ROOT / "schema/shots.csv"
    AUDIO = ROOT / "project/work/audio"

    vmap = voice_map()
    if not vmap:
        print("assets.json 的 voices[] 是空的 —— 先注册音色绑定（VC-###）", file=sys.stderr)
        return 1

    header, rows = read_shots(SHOTS)
    AUDIO.mkdir(parents=True, exist_ok=True)

    todo = [r for r in rows
            if (r.get("dialogue") or "").strip()
            and (not args.shots or (r.get("shot_id") or "").startswith(args.shots))]

    print(f"待配音 {len(todo)} 条")
    done = 0
    over = []
    for r in todo:
        sid = r["shot_id"]
        text = r["dialogue"].replace("【内心OS】", "").strip()
        vc = vmap.get(r.get("voice_id", ""))
        out_path = AUDIO / f"{sid}_v001.mp3"

        if not vc:
            print(f"  {sid} 跳过：voice_id={r.get('voice_id') or '(空)'} 未在 assets.json.voices 注册")
            continue
        if out_path.exists() and not args.force:
            dur = probe_duration(out_path)
            r["audio_file"], r["audio_duration_s"] = str(out_path.relative_to(ROOT)), f"{dur:.3f}" if dur else ""
            print(f"  {sid} 已有 {dur:.3f}s，跳过")
            continue
        if args.dry_run:
            print(f"  {sid} 计划：{vc['character_id']} <- {vc.get('voice_id')[:8]}… 「{text[:18]}…」")
            continue

        url = tts(text, vc)
        if not url:
            continue
        subprocess.run(["curl", "-fsSL", url, "-o", str(out_path)], check=False)
        dur = probe_duration(out_path)
        shot_dur = float(r.get("duration_s") or 0)
        r["audio_file"] = str(out_path.relative_to(ROOT))
        r["audio_duration_s"] = f"{dur:.3f}" if dur else ""
        flag = "放得下" if dur and dur <= shot_dur else "超长"
        if dur and dur > shot_dur:
            over.append((sid, dur, shot_dur, len(text)))
        print(f"  {sid} {vc['character_id']} 音频 {dur:.3f}s / 镜头 {shot_dur:g}s → {flag}")
        done += 1

    if not args.dry_run:
        write_shots(SHOTS, header, rows)
        print(f"\n生成 {done} 条，shots.csv 已回填")

    if over:
        print(f"\n台词超出镜头时长 {len(over)} 条（R8）：")
        for sid, d, sd, n in over:
            print(f"  {sid}: 音频 {d:.2f}s > 镜头 {sd:g}s，超出 {d - sd:.2f}s（{n} 字）")

    if args.report and not args.dry_run:
        rep = ROOT / "project/work/edit/EP01_配音对照表.md"
        rep.parent.mkdir(parents=True, exist_ok=True)
        names = {v["asset_id"]: (v.get("name", ""), v.get("preset_name", ""), v.get("engine_variant", ""))
                 for v in vmap.values()}
        lines = ["# EP01 配音 · 音色 · 字幕 对照表", "",
                 "> 由 `tools/tts_batch.py --report` 生成。字幕时间轴由 `tools/make_srt.py` 按**真实音频时长**生成。", "",
                 "| 镜头 | 角色 | 音色 | 引擎 | 台词 | 音频 | 镜头 | 余量 | 字幕 | 判定 |",
                 "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            if not (r.get("dialogue") or "").strip():
                continue
            sid = r["shot_id"]
            nm, preset, eng = names.get(r.get("voice_id", ""), ("", "", ""))
            a = r.get("audio_duration_s", "")
            d = float(r.get("duration_s") or 0)
            af = float(a) if a else 0.0
            slack = d - af
            verdict = "OK" if af and slack >= 0 else ("超长" if af else "未生成")
            txt = r["dialogue"].replace("【内心OS】", "OS：")[:26]
            lines.append(f"| {sid[-5:]} | {nm} | {preset} | {eng} | {txt} | {a or '-'}s | {d:g}s | "
                         f"{slack:+.2f}s | {sid[-5:]} | {verdict} |")
        rep.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n对照表：{rep.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
