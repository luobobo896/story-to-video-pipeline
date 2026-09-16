# schema/ 字段字典

这四个文件是**唯一真相源**。任何 Agent、任何一次重开对话，都先读这里，不靠上下文记忆。

除 `story_bible.json` 与 `assets.json` 是 JSON，其余两张表是 CSV（带表头，空行与 `#` 开头行会被校验器忽略）。多值字段（`refs`、`characters`）用分号 `;` 分隔。

---

## 1. story_bible.json

| 路径 | 含义 |
|---|---|
| `meta.project_name` | 项目名，由 S1 从剧本文件名推导 |
| `meta.script_sha256` | 剧本文件指纹，防止剧本被悄悄改动后资产失配 |
| `meta.episodes_planned` / `meta.episode_duration_target_s` | 集数与单集目标时长，由 S1 推导 |
| `meta.aspect_ratio` | 制作母版画幅，本项目固定 `16:9` |
| `meta.delivery_aspect_ratio` | 分发画幅，抖音用 `9:16` |
| `meta.derivation_notes` | 项目名 / 集数 / 单集时长的**推导依据**，用于复核与推翻 |
| `characters[].id` | `CH-###` |
| `characters[].appearance_anchors` | **3–6 条可被图像检验的外观特征**，是定妆图的验收标准 |
| `characters[].identity_mode` | `fictional`（定妆图三视图锁定，本项目全部角色）/ `soul`（真人脸训练，需 Basic 以上套餐） |
| `characters[].voice_id` | 指向 `assets.json.voices[].asset_id` |
| `props[].id` | `PR-###` |
| `environments[].id` | `EN-###`；`time_of_day` 与光照方向必须写清 |
| `styles[].id` | `ST-###`，全片风格锚 |
| `wardrobe[].id` | `WD-###`，同一角色不同造型分不同 ID |
| `timeline[]` | 时间线：时间点、所属集、剧本出处、是否闪回 |
| `plot_beats[].beat_type` | `hook` / `conflict` / `turn` / `climax` / `ending` |
| `open_questions[]` | 待作者确认项。`blocking_stage` 标出它卡住哪个阶段 |
| `episode_plan[]` | S1 推导出的分集方案：每集的标题、剧本出处、剧情节点、进入钩子与结尾钩子、预估镜头数与时长 |
| `characters[].status` | `draft` = 需要建资产的角色；`mentioned` = 仅台词提及、本章不出场，不参与外观锚点检查 |

## 2. assets.json

| 字段 | 含义 |
|---|---|
| `assets[].asset_id` | 资产编号，与 `story_bible.json` 一致 |
| `assets[].type` | `character` / `prop` / `environment` / `wardrobe` / `style` |
| `assets[].source` | `generated` / `trained` / `imported` |
| `assets[].anchor_file` | **定稿参考图路径**。后续所有镜头都复用这一张 |
| `assets[].sha256` | 定稿文件哈希，用于确认"还是那张图" |
| `assets[].job_id` | 生成它的 Higgsfield 作业 ID，便于回溯与重跑 |
| `assets[].soul_reference_id` | 真人脸训练返回的 `reference_id` |
| `assets[].version` | `v001` 起递增。**只追加，不覆盖** |
| `voices[].asset_id` | `VC-###` |
| `voices[].character_id` | 绑定到哪个角色；一个角色只能绑一个音色（校验器会查） |
| `voices[].voice_id` / `voice_type` / `engine_variant` | 来自 `higgsfield voices list` |

## 3. episodes.csv

| 列 | 含义 |
|---|---|
| `episode_id` | `EP01` 起 |
| `episode_title` | 集名 |
| `scene_id` | `SC01` 起，**集内唯一** |
| `scene_title` | 场次标题 |
| `script_ref` | 本场对应剧本的行号或段落 ID，如 `120-165` |
| `location_env_id` | 指向 `EN-###` |
| `characters` | 本场出场角色，`CH-001;CH-002` |
| `est_duration_s` | 本场预估时长 |
| `shot_count` | 本场镜头数 |
| `status` | `todo` / `wip` / `done` |

## 4. shots.csv

一行 = 一个镜头卡。字段多是有意的：**每一条都对应一次失败过的事故。**

| 列 | 含义 |
|---|---|
| `shot_id` | `EP01-SC02-SH003`，**分配后永不变更，删除留空号不重排** |
| `episode_id` / `scene_id` | 所属集与场次 |
| `shot_no` | 本场内序号 |
| `duration_s` | 时长。2–4s 插入 / 反应，4–7s 明确动作，8–12s 持续表演 |
| `aspect_ratio` | 画幅 |
| `script_ref` | **必填**，指回剧本；校验器强制 100% 覆盖 |
| `description` | 画面内容一句话 |
| `pose_start` / `pose_end` | 人物姿态起止（坐 / 站 / 跪 / 躺 / 蹲 / 趴）。**一镜只允许一次姿态转换** |
| `position_start` / `position_end` | 画内位置起止，用绝对描述（"画面左侧 1/3"），禁止"旁边""对面" |
| `facing` | 朝向（正 / 侧 / 背 + 朝向角） |
| `eyeline` | 视线落点（在看谁、在看什么） |
| `action_start` / `action_end` | 动作起点与终点，用于首尾帧夹逼 |
| `emotion_start` / `emotion_end` | 情绪起点与终点。**一镜只放一个主节拍** |
| `shot_size_z` | 景别 Z 编码（Z1 大特写 → Z9 大远景） |
| `camera_move` | 运镜。**每镜最多双轴运动** |
| `axis_note` | 轴线与屏幕方向备注 |
| `props_in_frame` | 本镜应出现的道具及数量与位置（如"杯子×2，桌面左上角"），用于切镜后比对 |
| `physics_note` | 物理约束与收束状态（如"杯子放下后静止在桌面，不弹跳"） |
| `style_id` | 指向 `ST-###` |
| `refs` | 本镜挂载的资产，`CH-001;EN-003;ST-001`，**顺序即挂载顺序** |
| `voice_id` | 指向 `VC-###` |
| `dialogue` | 台词原文（无台词留空） |
| `prompt_zh` | 中文提示词。本项目纯中文路线，不设英文列；若后续切换到英文提示词模型，自行加一列 `prompt_en` |
| `model` | 使用的模型 ID |
| `job_id` | Higgsfield 作业 ID |
| `audio_duration_s` | 实测音频时长，不得超过 `duration_s` |
| `audio_file` / `clip_file` | 产物路径 |
| `status` | `todo` / `wip` / `done` / `regen` |
| `qa_identity` … `qa_props` | 视觉十项，取值 `pass` / `fail` / 空。`status=done` 时十项必须全 `pass`。判据见 [../docs/06-连贯性与物理合理性检查清单.md](../docs/06-连贯性与物理合理性检查清单.md) |
| `refs` 中的主体 | 必须落在**中心安全区**内，保证 16:9 横转 9:16 时不被裁掉 |
| `version` | 通过的版本号，如 `v002` |
| `updated_at` | 最后更新时间 |

---

## 新增一个镜头的最小流程

1. 在 `episodes.csv` 确认它所属的 `episode_id` / `scene_id` 已存在。
2. 在 `shots.csv` 追加一行：`shot_id` 按规则编号，`script_ref` 填剧本出处，`refs` 填已定稿资产，并填齐 `pose_*` / `position_*` / `facing` / `props_in_frame` / `physics_note`。含角色的镜头缺少连续性字段时校验器会告警。
3. 跑 `python3 tools/check_consistency.py`，直到 0 错误再开始生成。
