# 状元是买的，但才华是真的

> 项目实例（EP01）｜剧本：`project/raw/状元是买的，但才华是真的.txt`｜复用层：`../../`

> 样张（角色定妆图三视图 / 场景空镜 / 风格锚 / G2 评审拼图 / 成片截帧）见 [`docs/images/`](docs/images/)，根 README 也展示了这几张；`project/work/` 下的原件 4–9MB，不入库。

## 当前状态

| 项 | 值 |
|---|---|
| 阶段 | `S2 资产已补齐`（等 G2 作者过目）· `S3 分镜完成` · `S4 EP01 进行中`（4 镜出片后判定重做） |
| 校验 | **`通过（0 错误 / 4 警告）`** —— 2 条 ME-006（面部不可读，设计如此）+ Q-008、Q-009（待你拍板） |
| 账号档位 | **basic**（$9/月，120 积分/月）：视频只能用 `seedance_2_0 --mode fast`（≤720p）或 `seedance_2_0_mini`；完整 2.0 与 2.5 需 Pro。已写进 `meta.account`，场记核对 **R21** 会拦住越档模型 |
| 积分 | 本轮补齐资产花 **12 积分**（6 张 × 2 积分），余额 67.2 → **55.2**；整集成本 ≈ 431（mini）/ 573（fast）积分 |
| 剧本指纹 | `79039b147c9b50ead3817a5eb2dfd0d93349d11a147a423aeafd01a22c7ea5e6` |

### 本轮补的 4 张资产（已自检，等 G2 定稿）

| 资产 | 文件 | 验收结论 |
|---|---|---|
| `CH-003` 沈芸 | `project/work/assets/CH-003_v001.png` | ✅ 三视图；挽髻素银簪、藕荷襦裙 + 月白褙子、通身无绣纹、面容温和，符合锚点 |
| `CH-004` 礼部侍郎 | `project/work/assets/CH-004_v002.png` | ✅ **v001 不合格已弃用**（面部仍可辨、背景是城墙非厅堂）；v002 纯背光剪影、面部完全不可辨、高冠双垂翅、厅堂门洞 |
| `CH-005` 当今圣上 | `project/work/assets/CH-005_v001.png` | ✅ 垂帘后高背龙椅端坐剪影、暗金边缘微光、面部不可辨 |
| `PR-004` 灵位牌 | `project/work/assets/PR-004_v001.png` | ✅ 两块木牌并排、竖排金漆字迹、供桌 + 香炉 + 残烛，无人无手 |

## 还需要作者拍板的两件事

1. **G2 定稿**：把上面 4 张图对照外观锚点过一眼。哪张哪条不符就说，重生成 2 积分/张；确认后把 `assets.json` 对应行的 `status` 改成 `locked`。
2. **Q-008 单集时长**：台词实测 81.1s + 12 个无台词镜头 48s = 下限 129.1s，原 120s 目标没给台词留时间。本次已按 VD-002 延长镜头到 142s；要守 120s 就得拆镜或精简台词。
3. **Q-009 视频档位**：Basic 的 120 积分/月只够约 1/4 集（整集 431–573 积分），且没有完整的 Seedance 2.0（只有 Fast / Mini）与 2.5。要么就用 Fast/Mini 跑通，要么升 Pro（$23/月、600 积分）后改 `meta.account` 解锁 1080p 与 2.5。

## 目录

```
状元是买的，但才华是真的/
├── README.md          本文件（项目状态写在这里，不写进复用层）
├── schema/            场记台账：story_bible / assets / episodes / shots
├── docs/07-project-calibration-notes.md   本项目的实测数据与阈值校准
└── project/
    ├── raw/           剧本（只读）
    ├── work/          定妆图、关键帧、片段、音频（不入库）
    └── delivery/      成片与交付物（不入库）
```

## 常用命令

```bash
cd ../..                                    # 回到复用层
python3 tools/check_consistency.py --schema-dir projects/zhuangyuan-ep01/schema
python3 tools/check_consistency.py --selftest
python3 tools/make_srt.py                   # 只有这一个项目时可省略 --schema-dir
```
