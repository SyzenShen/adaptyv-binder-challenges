# STATE — 项目状态

最后更新：2026-09-30 20:55 CEST (UTC+2) ｜ 阶段：**1 已交付（本地测试 22/22 通过）**，停在**科学确认点 A**（等待用户选表位方案）；剩余阻塞项 A2 mouse 构建体、A3 注册资格

## 总体里程碑

| 阶段 | 状态 | 说明 |
|---|---|---|
| 0 规则/环境/仓库/最小项目 | ✅ 完成（push 已核实） | 远端 main @ 24d362c |
| 1 目标/映射/表位候选 | ✅ 完成（测试 22/22） | **科学确认点 A 待用户批准** |
| 2 云端 smoke test | ⏳ 未开始 | 依赖确认点 A |
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

## 当前 Blockers（真实阻挡）

1. **CONFIRMATION_A_PENDING** — 两套表位+裁剪方案已交付（target_preparation.md §9），等待用户选择。未经确认不启动生产计算。
2. **MOUSE_CONSTRUCT_UNKNOWN** — 官方 EGFR 页 Mouse EGFR 标签为空面板；需登录查看或 Slack 询问（A2）。阻塞双物种复核设计。
3. **ELIGIBILITY/REGISTRATION_PENDING** — Terms §3.1 排除中国等地区法定居民；Track 3 需 Proteinbase 注册（A3），阻塞最终提交。
4. **DISK_TIGHT** — 本地容器仅 25GB 可用。模型权重/数据集走云端（A4，非阻塞）。

## 依赖

- 阶段 2：需确认点 A 批准 + 本人登录 Colab、授权 Drive 结果目录；付费必须先批准。
- 阶段 4：另依赖 A2 mouse 官方构建体。

## 下一动作（按优先级）

1. 用户确认科学确认点 A（表位方案 1 或 2）。
2. A2/A3 用户侧异步动作。
3. 确认 A 后进入阶段 2：Colab smoke test（BindCraft 最小轨迹、成本测量、断点续跑验证）。

## 批准记录

- 无付费/公开/提交类批准。paid_budget=0。
