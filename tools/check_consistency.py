#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短剧流水线一致性校验器（零依赖，仅标准库）。

它把 docs/04-风险与校验点.md 里的阶段闸门变成可执行检查：

    python3 tools/check_consistency.py              # 校验默认的 ./schema
    python3 tools/check_consistency.py --json       # 机器可读
    python3 tools/check_consistency.py --selftest   # 自检：确认它真的能抓到错误

退出码：0 = 全部通过；1 = 存在错误（警告不影响退出码）。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SHOT_ID_RE = re.compile(r"^EP\d{2}-SC\d{2}-SH\d{3}$")
ASSET_ID_RE = re.compile(r"^(CH|PR|EN|WD|ST|VC)-\d{3}$")
QA_FIELDS = [
    "qa_identity", "qa_wardrobe", "qa_scene", "qa_light", "qa_axis",
    "qa_spec", "qa_safe_area", "qa_continuity", "qa_physics", "qa_props",
]
CONTINUITY_FIELDS = ["pose_start", "pose_end", "position_start", "position_end", "facing"]
# rules/ME-009：时长 ≥4s 的镜头必须有足够节拍，否则必然匀速漂移（ME-001）
MIN_BEATS_FOR_LONG_SHOT = 2
LONG_SHOT_SECONDS = 4
MIN_READABLE_FACE_SCALE = 10

EPISODE_REQUIRED = ["episode_id", "scene_id", "location_env_id", "characters"]
SHOT_REQUIRED = ["shot_id", "episode_id", "scene_id", "duration_s", "script_ref", "refs", "status"]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """读 CSV，忽略空行与以 # 开头的注释行，字段两端去空格。"""
    if not path.exists():
        return []
    lines = [
        ln for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return [{ (k or "").strip(): (v or "").strip() for k, v in row.items() } for row in reader]


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def probe_streams(path: Path) -> list[str]:
    """返回容器里的流类型列表，如 ['video', 'audio']。失败返回 []。"""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def probe_dims(path: Path) -> tuple[int, int]:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60)
        w, h = out.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0, 0


def check_delivery(project_root: Path, shots: list[dict[str, str]], draft: bool) -> tuple[list[str], list[str]]:
    """按 rules/COMP-成片核心要素.md 审计交付完整性。"""
    errors: list[str] = []
    warnings: list[str] = []
    delivery = project_root / "project/delivery"
    edit = project_root / "project/work/edit"
    audio = project_root / "project/work/audio"

    def report(rule: str, msg: str, hard: bool = True) -> None:
        (warnings if draft or not hard else errors).append(f"[{rule}] {msg}")

    # A1 视频轨：优先认 delivery/，没归档则退回 work/edit/
    clips = sorted(delivery.glob("*.mp4"))
    if clips:
        pass
    else:
        clips = sorted(p for p in edit.glob("*.mp4") if not p.name.startswith("caption_tooltest"))
        if clips:
            report("COMP-A1", f"成片还在 work/edit/，尚未归档到 delivery/（{len(clips)} 个）", hard=False)
        else:
            report("COMP-A1", "找不到任何成片（delivery/ 与 work/edit/ 下都没有 .mp4）")
            return errors, warnings

    # A2 声音轨
    has_audio = [c for c in clips if "audio" in probe_streams(c)]
    if not has_audio:
        report("COMP-A2", "成片里没有音频流（静音的不是短剧）")

    # A3 台词
    voiced = [r for r in shots if (r.get("dialogue") or "").strip()]
    missing = [r["shot_id"] for r in voiced if not (r.get("audio_file") or "").strip()]
    if missing:
        report("COMP-A3", f"{len(missing)} 个有台词的镜头没有配音音频：{', '.join(missing[:4])}…")

    # 台词是否真的混进了成片：音频文件存在但成片时长明显短于台词总长时提示
    total_voice = 0.0
    for r in voiced:
        try:
            total_voice += float(r.get("audio_duration_s") or 0)
        except ValueError:
            pass

    # B1 字幕
    srts = list(delivery.glob("*.srt")) + list(edit.glob("EP*.srt"))
    subs_in_clip = any("subtitle" in probe_streams(c) for c in clips)
    if not srts and not subs_in_clip:
        report("COMP-B1", "既没有 .srt 文件，成片里也没有字幕轨")

    # B2 分发画幅
    vertical = [c for c in clips if (lambda d: d[1] > d[0] and min(d) >= 1080)(probe_dims(c))]
    if not vertical:
        report("COMP-B2", "没有 9:16 且短边 ≥1080 的分发版")

    # B4 封面
    covers = [p for p in delivery.glob("cover_*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    if len(covers) < 2:
        report("COMP-B4", f"封面不足 2 张（横竖各一），当前 {len(covers)} 张", hard=False)

    # C1 环境音
    sfx = [p for p in (audio / "sfx").glob("*") if p.is_file()] if (audio / "sfx").is_dir() else []
    if not sfx:
        report("COMP-C1", "没有环境音 / 音效（work/audio/sfx/ 为空或不存在）", hard=False)

    # C2 BGM
    bgm = [p for p in audio.glob("*") if p.is_file() and "bgm" in p.name.lower()]
    if not bgm:
        report("COMP-C2", "没有 BGM 轨", hard=False)

    # C5 台账
    for name in ("asset_manifest.md", "delivery_checklist.md"):
        if not (delivery / name).exists():
            report("COMP-C5", f"缺少 {name}", hard=False)

    # 台词塞不塞得下：所有台词音频的总长不能超过成片时长
    if total_voice:
        try:
            dur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(clips[-1])],
                capture_output=True, text=True, timeout=60).stdout.strip())
        except (OSError, subprocess.SubprocessError, ValueError):
            dur = 0.0
        if dur and total_voice > dur:
            report("COMP-A3", f"台词音频总长 {total_voice:.1f}s 超过成片时长 {dur:.1f}s，必然塞不下")

    return errors, warnings


def check_csv_shape(path: Path, name: str) -> list[str]:
    """CSV 每行的字段数必须与表头一致，否则 DictReader 会静默错位。"""
    if not path.exists():
        return []
    lines = [
        ln for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if not lines:
        return []
    rows = list(csv.reader(io.StringIO("\n".join(lines))))
    width = len(rows[0])
    errors = []
    for idx, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            errors.append(
                f"[R0] {name} 第 {idx} 行有 {len(row)} 个字段，表头是 {width} 个，列会错位"
            )
    return errors


def split_ids(value: str) -> list[str]:
    """多值字段分隔：; , 、 以及空白分隔。"""
    if not value:
        return []
    return [t for t in re.split(r"[;,、\s]+", value) if t]


def as_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def run_checks(schema_dir: Path, draft: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(check_csv_shape(schema_dir / "episodes.csv", "episodes.csv"))
    errors.extend(check_csv_shape(schema_dir / "shots.csv", "shots.csv"))

    bible = read_json(schema_dir / "story_bible.json")
    assets_doc = read_json(schema_dir / "assets.json")
    episodes = read_csv_rows(schema_dir / "episodes.csv")
    shots = read_csv_rows(schema_dir / "shots.csv")

    for name, doc in (("story_bible.json", bible), ("assets.json", assets_doc)):
        if not doc:
            errors.append(f"[R0] 缺少或无法解析 {name}")

    # ── R0 必需列 ─────────────────────────────────────────────
    if episodes:
        missing = [c for c in EPISODE_REQUIRED if c not in episodes[0]]
        if missing:
            errors.append(f"[R0] episodes.csv 缺少必需列：{', '.join(missing)}")
    if shots:
        missing = [c for c in SHOT_REQUIRED if c not in shots[0]]
        if missing:
            errors.append(f"[R0] shots.csv 缺少必需列：{', '.join(missing)}")

    # ── 建索引 ────────────────────────────────────────────────
    asset_ids: set[str] = set()
    character_assets: dict[str, dict] = {}
    for a in assets_doc.get("assets", []):
        aid = a.get("asset_id", "")
        if not aid:
            errors.append("[R0] assets.json 中存在没有 asset_id 的资产")
            continue
        if not ASSET_ID_RE.match(aid):
            errors.append(f"[R4] 资产编号不合规范：{aid}（应为 CH/PR/EN/WD/ST/VC-###）")
        if aid in asset_ids:
            errors.append(f"[R4] 资产编号重复：{aid}")
        asset_ids.add(aid)
        if a.get("type") == "character":
            character_assets[aid] = a
    voice_assets: dict[str, dict] = {}
    for v in assets_doc.get("voices", []):
        vid = v.get("asset_id", "")
        if not vid:
            errors.append("[R0] assets.json.voices 中存在没有 asset_id 的条目")
            continue
        if vid in asset_ids:
            errors.append(f"[R4] 资产编号重复：{vid}")
        asset_ids.add(vid)
        voice_assets[vid] = v

    # 引用完整性只认 assets.json 里已登记的资产：story_bible 里定义了角色不等于资产已就绪。
    # 否则分镜可以引用一个永远没有定妆图的角色，G2 闸门就被绕过了。
    known_ids = set(asset_ids)

    scene_index: set[tuple[str, str]] = set()
    episode_ids: set[str] = set()
    for e in episodes:
        ep, sc = e.get("episode_id", ""), e.get("scene_id", "")
        if ep:
            episode_ids.add(ep)
        if ep and sc:
            if (ep, sc) in scene_index:
                errors.append(f"[R4] 场次重复：{ep}/{sc}")
            scene_index.add((ep, sc))

        # R3 场次引用完整性
        if not draft:
            for cid in split_ids(e.get("characters", "")):
                if cid not in known_ids:
                    errors.append(f"[R2] {ep}/{sc} 的 characters 引用了不存在的资产：{cid}")
            env = e.get("location_env_id", "")
            if env and env not in known_ids:
                errors.append(f"[R2] {ep}/{sc} 的 location_env_id 不存在：{env}")

    # ── R5 角色必须有锚定物 ───────────────────────────────────
    if not draft:
        for aid, a in character_assets.items():
            if not a.get("anchor_file") and not a.get("soul_reference_id"):
                errors.append(f"[R5] 角色 {aid} 既无 anchor_file 也无 soul_reference_id，无法锁定一致性")

    # ── R12 定稿资产哈希核对 ─────────────────────────────────
    project_root = schema_dir.parent
    for a in assets_doc.get("assets", []):
        aid = a.get("asset_id", "?")
        anchor = a.get("anchor_file", "")
        want = a.get("sha256", "")
        if not anchor or not want:
            continue
        path = Path(anchor) if Path(anchor).is_absolute() else project_root / anchor
        if not path.exists():
            warnings.append(f"[R12] {aid} 的定稿图本地不存在：{anchor}（可能尚未下载或在另一台机器）")
            continue
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != want:
            errors.append(f"[R12] {aid} 的定稿图已变更：{anchor} 实际哈希 {got[:12]}… 与登记值 {want[:12]}… 不符")

    # ── 逐个镜头检查 ─────────────────────────────────────────
    seen_shot_ids: set[str] = set()
    for s in shots:
        sid = s.get("shot_id", "")
        tag = sid or "(未命名镜头)"

        if not SHOT_ID_RE.match(sid):
            errors.append(f"[R4] 镜头编号不合规范：{tag}（应形如 EP01-SC02-SH003）")
        if sid in seen_shot_ids:
            errors.append(f"[R4] 镜头编号重复：{sid}")
        seen_shot_ids.add(sid)

        pair = (s.get("episode_id", ""), s.get("scene_id", ""))
        if pair not in scene_index:
            errors.append(f"[R1] {tag} 指向的场次不存在：{pair[0]}/{pair[1]}")

        if not draft:
            for rid in split_ids(s.get("refs", "")):
                if rid not in known_ids:
                    errors.append(f"[R2] {tag} 的 refs 引用了不存在的资产：{rid}")

            vid = s.get("voice_id", "")
            if vid and vid not in known_ids:
                errors.append(f"[R2] {tag} 的 voice_id 不存在：{vid}")

        if not s.get("script_ref", ""):
            errors.append(f"[R6] {tag} 缺少 script_ref，无法回溯到剧本")

        if any(r.startswith("CH-") for r in split_ids(s.get("refs", ""))) and s.get("status") in ("wip", "done"):
            blank = [f for f in CONTINUITY_FIELDS if not s.get(f, "")]
            if blank:
                warnings.append(f"[G3] {tag} 未标注 {'/'.join(blank)}，跨镜姿态与站位连续性没有依据")

        # ── rules/ME-006 & ME-009 微表情可执行约束 ─────────────
        beats_raw, scale_raw = s.get("micro_beats", ""), s.get("face_scale", "")
        beats, scale = as_float(beats_raw), as_float(scale_raw)
        dur_s = as_float(s.get("duration_s", ""))
        if beats is None and s.get("status") not in ("", "todo"):
            warnings.append(f"[ME-009] {tag} 已开工但未标注 micro_beats / face_scale")
        elif beats is not None and scale is not None and dur_s is not None:
            if scale < MIN_READABLE_FACE_SCALE and beats > 0:
                (warnings if draft else errors).append(
                    f"[ME-006] {tag} face_scale={scale:g}% 低于 {MIN_READABLE_FACE_SCALE}%，"
                    f"微表情不可读，却标了 {beats:g} 个节拍")
            elif scale >= MIN_READABLE_FACE_SCALE and dur_s >= LONG_SHOT_SECONDS and beats < MIN_BEATS_FOR_LONG_SHOT:
                (warnings if draft else errors).append(
                    f"[ME-009] {tag} 时长 {dur_s:g}s、face_scale={scale:g}% 但只有 {beats:g} 个节拍，"
                    f"必然匀速漂移（ME-001），需拆到 ≥{MIN_BEATS_FOR_LONG_SHOT} 个")
            elif scale < MIN_READABLE_FACE_SCALE and dur_s >= LONG_SHOT_SECONDS:
                warnings.append(
                    f"[ME-006] {tag} face_scale={scale:g}% 面部不可读，确认该镜确实不需要微表情")
            if scale >= MIN_READABLE_FACE_SCALE and dur_s >= LONG_SHOT_SECONDS and beats > 3:
                (warnings if draft else errors).append(
                    f"[ME-008] {tag} 情绪节拍 {beats:g} 个超过硬上限 3 个，会被抹平")

        if s.get("status") == "done":
            bad = [f for f in QA_FIELDS if s.get(f, "") != "pass"]
            if bad:
                msg = f"{tag} 已标 done，但 QA 未全通过：{', '.join(bad)}"
                (warnings if draft else errors).append(f"[R7] {msg}")

        dur = as_float(s.get("duration_s", ""))
        adur = as_float(s.get("audio_duration_s", ""))
        if dur is not None and adur is not None and adur > dur:
            errors.append(f"[R8] {tag} 音频 {adur}s 超过镜头时长 {dur}s")

    # ── 同角色音色唯一（R11）─────────────────────────────────
    char_to_voice: dict[str, str] = {}
    for vid, v in voice_assets.items():
        cid = v.get("character_id", "")
        if not cid:
            warnings.append(f"[R11] 音色 {vid} 未绑定 character_id")
            continue
        if cid in char_to_voice and char_to_voice[cid] != vid:
            errors.append(f"[R11] 角色 {cid} 绑定了多个音色：{char_to_voice[cid]} / {vid}")
        char_to_voice[cid] = vid

    # ── 软性问题只警告 ───────────────────────────────────────
    for c in bible.get("characters", []):
        if c.get("status") == "mentioned":
            continue  # 未出场角色（仅台词提及）不需要外观锚点
        anchors = c.get("appearance_anchors") or []
        if len(anchors) < 3:
            warnings.append(f"[G1] 角色 {c.get('id', '?')} 的外观锚点少于 3 条，容易被模型漂")
    for q in bible.get("open_questions", []):
        if not q.get("resolved"):
            warnings.append(f"[G1] 待确认问题未解决：{q.get('id', '?')} {q.get('question', '')}")

    return errors, warnings


def _write_fixture(d: Path, broken: bool) -> None:
    bible = {
        "meta": {"project_name": "selftest"},
        "characters": [{"id": "CH-001", "name": "甲",
                        "appearance_anchors": ["a", "b", "c"]}],
        "open_questions": [],
    }
    assets = {
        "assets": [
            {"asset_id": "CH-001", "type": "character", "anchor_file": "x.png",
             "soul_reference_id": ""},
            {"asset_id": "EN-001", "type": "environment", "anchor_file": "y.png"},
        ],
        "voices": [{"asset_id": "VC-001", "character_id": "CH-001"}],
    }
    episodes = (
        "episode_id,episode_title,scene_id,scene_title,script_ref,location_env_id,"
        "characters,est_duration_s,shot_count,status,notes\n"
        "EP01,试播,SC01,开场,1-10,EN-001,CH-001,10,2,todo,\n"
    )
    bad_ref = "PR-099" if broken else "CH-001"
    all_pass = ",".join("pass" for _ in QA_FIELDS)
    blank_qa = ",".join("" for _ in QA_FIELDS)
    shots = (
        "shot_id,episode_id,scene_id,shot_no,duration_s,script_ref,refs,status,"
        + ",".join(CONTINUITY_FIELDS) + ","
        + ",".join(QA_FIELDS) + "\n"
        f"EP01-SC01-SH001,EP01,SC01,1,5,1-5,{bad_ref},todo,坐,坐,画面左,画面左,正面,{blank_qa}\n"
        f"EP01-SC01-SH002,EP01,SC01,2,5,6-10,CH-001,done,站,站,画面中,画面中,四分之三侧,{all_pass}\n"
    )
    (d / "story_bible.json").write_text(json.dumps(bible, ensure_ascii=False), encoding="utf-8")
    (d / "assets.json").write_text(json.dumps(assets, ensure_ascii=False), encoding="utf-8")
    (d / "episodes.csv").write_text(episodes, encoding="utf-8")
    (d / "shots.csv").write_text(shots, encoding="utf-8")


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_fixture(d, broken=False)
        ok_errors, _ = run_checks(d)
        if ok_errors:
            print("自检失败：干净数据被误报：")
            for e in ok_errors:
                print("  -", e)
            return 1
        _write_fixture(d, broken=True)
        bad_errors, _ = run_checks(d)
        if not any("PR-099" in e for e in bad_errors):
            print("自检失败：坏引用没有被抓到。")
            return 1
        draft_errors, _ = run_checks(d, draft=True)
        if any("PR-099" in e for e in draft_errors):
            print("自检失败：草稿模式不应检查资产引用。")
            return 1
        with (d / "shots.csv").open("a", encoding="utf-8") as f:
            f.write("EP01-SC01-SH003,EP01,SC01,3\n")
        shape_errors, _ = run_checks(d)
        if not any("列会错位" in e for e in shape_errors):
            print("自检失败：列数错位没有被抓到。")
            return 1
    print("自检通过：干净数据 0 错误；坏引用、草稿模式、列错位三项行为正确。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="短剧流水线一致性校验器")
    parser.add_argument("--schema-dir", default=str(Path(__file__).resolve().parent.parent / "schema"),
                        help="schema 目录，默认 <项目根>/schema")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--selftest", action="store_true", help="自检校验器本身")
    parser.add_argument("--draft", action="store_true",
                        help="草稿模式：跳过资产存在性检查，允许先出分镜稿再补资产")
    parser.add_argument("--delivery", action="store_true",
                        help="额外按 rules/COMP-成片核心要素.md 审计交付完整性")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    schema_dir = Path(args.schema_dir)
    if not schema_dir.is_dir():
        print(f"找不到 schema 目录：{schema_dir}", file=sys.stderr)
        return 1

    errors, warnings = run_checks(schema_dir, draft=args.draft)

    if args.delivery:
        shot_rows = read_csv_rows(schema_dir / "shots.csv")
        d_err, d_warn = check_delivery(schema_dir.parent, shot_rows, draft=args.draft)
        errors.extend(d_err)
        warnings.extend(d_warn)

    if args.json:
        print(json.dumps({"errors": errors, "warnings": warnings,
                          "passed": not errors}, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    print(f"一致性校验：{schema_dir}")
    for label, items in (("错误", errors), ("警告", warnings)):
        for item in items:
            print(f"  [{label}] {item}")
    if not errors and not warnings:
        print("  全部通过。")
    else:
        print(f"结果：{'不通过' if errors else '通过'}（{len(errors)} 错误 / {len(warnings)} 警告）")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
