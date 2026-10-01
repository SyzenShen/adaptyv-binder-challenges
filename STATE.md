# STATE — 项目状态

最后更新：2026-10-01 ｜ 阶段：**2 云端 smoke test — 尝试 001 在环境层失败（Colab Py3.13/JAX 0.11.1，已定位并修复 notebook，等待用户 factory reset 后复测 A7）**；A+ 已关闭（主选 B 经用户批准）；已有云端硬件实测：**Tesla T4 / 15360 MiB / CUDA 12.8（用户 2026-10-01 回传）**，但 PDL1 未产出 relaxed 轨迹、EGFR 0 轨迹，时长/吞吐/成功率仍为 null；不启动 EGFR 生产生成。阻塞项 A7 Colab 复测、A6 Slack 截图、A3 资格确认

## 总体里程碑

| 阶段 | 状态 | 说明 |
|---|---|---|
| 0 规则/环境/仓库/最小项目 | ✅ 完成（push 已核实） | 远端 main @ 24d362c |
| 1 目标/映射/表位候选 | ✅ 完成（测试 22/22） | 科学确认点 A 已被 A+ 取代 |
| 1.5 目标+assay 感知表位审计 | ✅ 完成（测试 36/36） | A+ 已由用户 2026-10-01 批准（D-013） |
| 2 云端 smoke test | 🟡 尝试 001 环境失败、已修复待复测 | 实测 T4 15GB；PDL1 因 JAX 0.11.1 崩溃；新隔离 py3.10/jax0.6.0 环境 + preflight 门就绪 |
| 3 小批次生成与筛选 | ⏳ 未开始 | 依赖 smoke 报告经用户复核 |
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

## 阶段 2 进展（真实执行，2026-10-01）

- A+ 关闭：用户书面批准主选 B（UniProt 390–403 + 421–431）、备选 C、H433 推迟阶段 5（D-013）。
- 官方文档实拉：BindCraft main **7713aa0**（2026-09-21）、ColabDesign main **e31a56f**（2025-10-23，云端解析版本实测后回填）；AF2 权重 alphafold_params_2022-12-06（5.3 GB）；PyRosetta 学术非商业许可。
- Hotspot 翻译（[bindcraft_hotspot_translation.md](reports/bindcraft_hotspot_translation.md)）：裁剪 PDB [6ARU_chainA_domain3_310-481.pdb](data/processed/6ARU_chainA_domain3_310-481.pdb)（172 残基，resseq=UniProt，坐标未改）；保守集 **390,393,399,421,424,431**（6 个），对照集 12 个全暴露残基（初始不运行）；binder 80 aa。**包络内确认无 F/W/Y/M、无 relSASA≥0.20 的疏水锚（最高 I394=0.145），如实记录为待检验假设**。
- advanced smoke 文件逐字节复制官方 `default_4stage_multimer.json`，仅 `max_trajectories` false→1/3；非 hardtarget、无目标突变、官方 default_filters 原样。
- 云端 [stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb)：环境元数据采集 → PDL1 官方最小示例（65 aa，hotspot 56，cap 1）→ EGFR micro（cap 3）→ [analyze_bindcraft_run.py](scripts/analyze_bindcraft_run.py) 几何判读（B 接触/迁移/clash/裁剪边缘）→ py3Dmol 目检 → `stage2_smoke_report.json`。
- **云端尝试 001（用户 2026-10-01 实测，真实结果）**：Tesla T4 / 15360 MiB；Colab 镜像 Python 3.13.15 + CUDA 12.8 + 预装 JAX/jaxlib 0.11.1 + ColabDesign 1.1.3；PyRosetta、AF2 权重安装成功。PDL1 在 relaxed 轨迹前崩于 `jax.lib.xla_bridge.get_backend()`（ColabDesign clear_mem）——**ENVIRONMENT_FAILURE**。根因与证据：[stage2_environment_failure_001.md](reports/stage2_environment_failure_001.md)（xla_bridge 在 JAX 0.8.0 移除；官方脚本约束 jax ≤0.6.0、py3.10、numpy<2；numpy 1.26.4 无 cp313 wheel）。
- **修复（D-017，未打上游补丁）**：notebook 改为在 Colab 内自建隔离 Miniforge **Python 3.10** 环境（conda-forge/nvidia `jax=0.6.0 jaxlib=0.6.0=*cuda*`，`CONDA_OVERRIDE_CUDA=12.6`，`numpy<2`、`flax<0.10`，ColabDesign pin e31a56f `--no-deps`，PyRosetta cp310 wheel），BindCraft 子进程全部走 env python；新增硬门 [bindcraft_preflight.py](scripts/bindcraft_preflight.py)（权重下载前验证版本/clear_mem/xla_bridge/GPU matmul）。科学配置零改动。
- **GPU/VRAM 已实测：T4 15360 MiB（free 值复测时由 preflight/元数据回填）；轨迹时长/峰值占用/吞吐/成功率仍 null（0 条 relaxed 轨迹，禁止推测）**。未创建 compute_escalation.md（无 OOM 证据）。
- Slack 凭据：[reports/slack_provenance/INDEX.md](reports/slack_provenance/INDEX.md)，7 条主张全部 PENDING（用户尚未提供截图）。
- 测试 62/62（[test_stage2.py](tests/test_stage2.py) 新增至 26 个，含 JAX 版本策略与 notebook 隔离环境回归）。

## 当前 Blockers（真实阻挡）

1. **CLOUD_SMOKE_ATTEMPT_001_FAILED_ENV / AWAITING_RETEST** — 首次云端执行在环境层失败（JAX 0.11.1），修复已入库（隔离 py3.10/jax 0.6.0 + preflight 门），需用户 factory reset 后复测（A7）；PDL1 relaxed 轨迹未取得前阶段 3 不得开始。
2. **MOUSE_CONSTRUCT_PROOF_PENDING** — mouse 25–647 仅 Slack 转述（A2/A6）；不阻塞 human smoke，阻塞阶段 4 mouse 验证。
3. **SLACK_PROVENANCE_PENDING (A6)** — 7 条 Slack 主张无截图（含上条）；[INDEX](reports/slack_provenance/INDEX.md) 全 PENDING。
4. **ELIGIBILITY/REGISTRATION_PENDING** — Track 3 资格/注册用户尚未确认（A3）；不阻塞技术 smoke，阻塞提交。
5. **DISK_TIGHT** — 本地空间有限；权重与产物均在云端（A4，非阻塞）。

## 依赖

- 阶段 2：A+ 已批准；需本人在 Colab 用更新后 notebook 复测（factory reset → T4 → 三文件上传 → preflight 通过）；付费必须先批准。
- 阶段 4：另依赖 A2/A6 mouse 官方构建体凭据。

## 下一动作（按优先级）

1. **A7（用户，复测）**：Colab 先 Disconnect and delete runtime，重新选 T4 GPU，打开更新后的 [stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb) 逐格执行；Cell 5 上传**三个**文件（裁剪 PDB、`analyze_bindcraft_run.py`、`bindcraft_preflight.py`）；确认 Cell 6 打印 `PRE-FLIGHT PASSED ... jax 0.6.0`；回传 `BindCraft/stage2_smoke/`（preflight.json、env_metadata.json、stage2_smoke_report.json、两个 log、relaxed PDB）。
2. 我收到实测产物后写 Stage 2 smoke 报告：环境 vs 靶点故障判定、B 接触/迁移/边缘伪影诊断、仅按实测吞吐给批次建议；若 OOM 两次才写 compute_escalation.md。
3. A6 Slack 截图；A3 Track 3 资格确认（一次性问题，见 HUMAN_ACTIONS）。
4. smoke 报告经用户复核前不扩大生成、不跑 broad hotspot、不付费。

## 批准记录

- 无付费/公开/提交类批准。paid_budget=0。
- A+ 已批准（D-013）；阶段 2 smoke 范围已由用户 2026-10-01 指令限定（D-014），生产生成未获批准。
