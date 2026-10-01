# STATE — 项目状态

最后更新：2026-10-01 ｜ 阶段：**1.5 目标+assay 感知表位审计完成（本地测试 36/36 通过）**，停在**科学确认点 A+**（[SCIENTIFIC_CHECKPOINT_A_PLUS.md](SCIENTIFIC_CHECKPOINT_A_PLUS.md)，等待用户批准主选 B / 备选 C）；不启动 EGFR 生产生成。剩余阻塞项 A2 mouse 构建体官方凭据、A3 注册资格、A6 Slack 截图

## 总体里程碑

| 阶段 | 状态 | 说明 |
|---|---|---|
| 0 规则/环境/仓库/最小项目 | ✅ 完成（push 已核实） | 远端 main @ 24d362c |
| 1 目标/映射/表位候选 | ✅ 完成（测试 22/22） | 科学确认点 A 已被 A+ 取代 |
| 1.5 目标+assay 感知表位审计 | ✅ 计算完成（测试 36/36） | **科学确认点 A+ 待用户批准**；报告见下 |
| 2 云端 smoke test | ⏳ 未开始 | 依赖确认点 A+ |
| 3 小批次生成与筛选 | ⏳ 未开始 | |
| 4 双物种复核 / 完整 ECD | ⏳ 未开始 | 另依赖 A2 |
| 5 pH 假设与有限重设计 | ⏳ 未开始 | |
| 6 新颖性/组合/人工终审 | ⏳ 未开始 | |
| 7 冻结与提交包 | ⏳ 未开始 | |

截止（已核实，2026-09-30 页面）：**2026-10-04 23:59 AoE = 2026-10-05 11:59 UTC**；内部目标 10-04 18:00 Europe/Berlin。

## 阶段 0 已完成（真实执行）

- 本机环境实测：macOS 15.6 / Intel x86_64 / i7-9750H 6C12T / 32GB RAM / 磁盘可用仅 27.5GB / 无 CUDA（AMD 5300M 4GB 不可用于模型）/ Python 3.10.11(python.org) / git 2.50.1 / gh 2.87.3 / Homebrew 7.0.6 / 无 conda。详见 [environment_audit.md](reports/environment_audit.md)。
- 官方来源核实（S1/S2 比赛与 EGFR 页、Terms、S10 新颖性博客、S11 Colab FAQ、S13/S14 TRAE 文档，及 S6/S7/S9/S12 仓库 HEAD 与 S3/S4/S5 端点连通性）：见 [sources_register.md](reports/sources_register.md)、[competition_rules.md](reports/competition_rules.md)。
- 目录骨架、7 个状态文件、`configs/competition.json`、`.gitignore`、TRAE always-apply 项目规则（`.trae/rules/egfr-project.md`）。
- 最小流水线代码 `scripts/seqvalidate.py` + `tests/test_smoke.py`（系统 Python 12/12 通过；`.venv` 下 pytest 12/12 通过）。
- 本地 git 仓库初始化，首个 commit **be3359b35a78032a861ee05525948ae214339d58**（分支 main，26 个文件，已做暂存体积/密钥检查）。
- 隔离分析环境 `.venv`（156MB，不入库），精确版本锁定于 configs/requirements-lock.txt：biopython 1.88 / pandas 2.3.3 / numpy 2.2.6 / PyYAML 6.0.3 / requests 2.34.2 / pytest 8.4.2。

## 阶段 1 已完成（真实执行）

- 下载并校验（URL/UTC 时间/SHA256 见 [targets.manifest.json](data/raw/targets.manifest.json)）：P00533.fasta、Q01279.fasta、6ARU.cif（1.5MB）。
- 6ARU 实测内容：Cetuximab Fab 突变体 + EGFR ECD，X 射线 3.2 Å；chain A = P00533 25–640 + His6 标签；与 UniProt 两处 conflict（N540K、E634R）；编号恒等偏移 +24（由 struct_ref_seq 推导，非硬编码）。
- **比赛构建体验证**：重抓比赛页提取的 621 aa 序列与本地 UniProt 25–645 切片逐字符一致（[competition_construct_check.json](data/processed/competition_construct_check.json)）。641–645（GPKIPS）不在 6ARU 构建体内。
- [residue_map.csv](data/processed/residue_map.csv)：621 行逐残基映射；609 残基有坐标；缺失密度 25–27/637–640；观察到糖基化 N352/N361/N413/N444（共 11 个 sequon）。
- 人鼠比对（PROVISIONAL，Q01279 全长，官方构建体未知）：无 gap，identity 88.7%（551/621 identical + 35 conservative）。
- Domain III（310–481）表面分析：4 个候选表位 patch（EPI_H_1..4，全部人鼠保守、距 Cetuximab Fab ≥ 8.6 Å）；详见 [target_preparation.md](reports/target_preparation.md) 与 [target_view.html](reports/target_view.html)。
- 测试 22/22 通过（系统 unittest 与 .venv pytest 双跑）。

## 阶段 1.5 已完成（真实执行，2026-10-01）

- 新增数据：P00533.txt、Q01279.txt（manifest 含 URL/UTC/SHA256）。
- **A 人鼠 ECD 比对**（mouse 25–647 = 623 aa，Slack 用户转达、官方凭据待 A6）：623 列，551 identical（0.8873）/35 conservative/2 mouse-only（639 W、640 P），0 内部 gap；H370/H418/H433 与 N352/N413/N444 同位同一；**鼠 361=Y，无 sequon**。[human_mouse_ecd_alignment.csv](data/processed/human_mouse_ecd_alignment.csv)
- **B/D/E/C 几何**（mmCIF 直读，全 ECD 四上下文 SASA+最小重原子距离）：EPI_H_1 糖风险最高（K335→N361 糖 4.27 Å、遮挡 11.3 Å²；N361 人特有）；EPI_H_2/H_3 连续为一面（2.71 Å）；糖伸入缺口 404–415 排除。**H418 埋藏（relSASA 0.022），阶段 1"表面 H418"正式撤回**；H370 部分暴露（0.155）；**H433 高暴露（0.676）、距 Fab 3.47 Å（Cetux 功能表位上）、距 K431 3.35 Å、8 Å 内无 Asp/Glu**。精修 hotspot：**390–403 + 421–431**（糖 ≥7.1/12.6 Å，Fab ≥9.11 Å）。
- 报告：[glycan_epitope_audit.md](reports/glycan_epitope_audit.md)、[ph_target_hotspot_audit.md](reports/ph_target_hotspot_audit.md)、[cetuximab_distance_audit.md](reports/cetuximab_distance_audit.md)、[epitope_3d_continuity.md](reports/epitope_3d_continuity.md)、[assay_metadata.md](reports/assay_metadata.md)、[germinal_assessment.md](reports/germinal_assessment.md)；终决 [SCIENTIFIC_CHECKPOINT_A_PLUS.md](SCIENTIFIC_CHECKPOINT_A_PLUS.md)（主选 B、备选 C）。
- viewer：[target_view.html](reports/target_view.html)（5 预设视角，脚本 [make_target_view.py](scripts/make_target_view.py) 已重写并运行）。
- 候选指标配置 [candidate_metrics.json](configs/candidate_metrics.json)（排名用；linker 字段保持 null 及原因）。
- 测试新增 [test_stage15.py](tests/test_stage15.py)（14 个）；系统 unittest 与 .venv pytest 双跑 36/36。

## 当前 Blockers（真实阻挡）

1. **CONFIRMATION_A_PLUS_PENDING** — 主选 B（390–403 + 421–431，H433 留门）/备选 C 已交付，等待用户批准。未经确认不启动生产计算。
2. **MOUSE_CONSTRUCT_PROOF_PENDING** — mouse 25–647 边界目前仅有用户转达的 Slack 信息，官方页 2026-10-01 仍空；需 A2/A6 截图或官方文本。
3. **ELIGIBILITY/REGISTRATION_PENDING** — Terms §3.1 排除中国等地区法定居民；Track 3 需 Proteinbase 注册（A3），阻塞最终提交。
4. **DISK_TIGHT** — 本地容器空间有限。模型权重/数据集走云端（A4，非阻塞）。

## 依赖

- 阶段 2：需确认点 A+ 批准 + 本人登录 Colab、授权 Drive 结果目录；付费必须先批准。
- 阶段 4：另依赖 A2/A6 mouse 官方构建体凭据。

## 下一动作（按优先级）

1. 用户批准 SCIENTIFIC_CHECKPOINT_A_PLUS.md（主选 B / 备选 C / 维持 A / 再分析 D）；含 H433 推迟到阶段 5 的处理是否同意。
2. A6：用户提供 Slack 原文截图（mouse 25–647 等 6 条 assay 信息）→ reports/slack_provenance/；A3 资格注册。
3. A+ 批准后进入阶段 2：Colab 环境准备 + BindCraft 官方示例 smoke test（先非 EGFR），记录真实 GPU/时长/断点续跑。

## 批准记录

- 无付费/公开/提交类批准。paid_budget=0。
- A+ 终决仅为分析推荐，生产生成未获批准。
