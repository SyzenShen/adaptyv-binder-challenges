# STATE — 项目状态

最后更新：2026-10-03 ｜ 阶段：**2 云端 smoke test — 可靠性合并 Checkpoint A/B/C 完成并 push 核实（A=`f8b9f0d`，B=`bc81198`；C 见 git log/ls-remote）；2026-10-03 按用户六条指令完成 D-019 per-model PyRosetta relaxation 容错（BUG 016，唯一授权上游窄补丁，BindCraft pin `7713aa0` 不变；补丁+应用器+pristine 夹具+JSONL 记录+manifest 必终结；124/124 双套件通过；Checkpoint D/E 提交/push/ls-remote 见本文件末尾回填）；薄 A–H notebook + 单一恢复 cell G，工件按 pin commit 获取；BUG 001-016 台账见 [stage2_reliability_consolidation.md](reports/stage2_reliability_consolidation.md)；等待用户 A7 在 Colab 跑/恢复一次真实 smoke；不启动 EGFR 生产生成**；A+ 已关闭（主选 B 经用户批准）；已有云端硬件实测：**Tesla T4 / 15360 MiB / CUDA 12.8（用户 2026-10-01 回传）**，PDL1 成功 run 已持久化到用户 Drive（`PDL1_smoke_l65_s909721.pdb`，rc 0、零最终接受），EGFR 0 轨迹，时长/吞吐/成功率仍为 null。阻塞项 A7 Colab 跑薄 notebook（reset 后从 A 跑到 G 即恢复；Cell D 补丁步骤幂等）、A6 Slack 截图、A3 资格确认

## 总体里程碑

| 阶段 | 状态 | 说明 |
|---|---|---|
| 0 规则/环境/仓库/最小项目 | ✅ 完成（push 已核实） | 远端 main @ 24d362c |
| 1 目标/映射/表位候选 | ✅ 完成（测试 22/22） | 科学确认点 A 已被 A+ 取代 |
| 1.5 目标+assay 感知表位审计 | ✅ 完成（测试 36/36） | A+ 已由用户 2026-10-01 批准（D-013） |
| 2 云端 smoke test | 🟡 可靠性合并完成（A/B/C push 核实）+ D-019 容错补丁（Checkpoint D/E），待 A7 云端复测 | 实测 T4 15GB；PDL1 成功 run 已持久化（零最终接受）；薄 A–H notebook + 检查点幂等恢复就绪；124/124 测试 |
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
- **修复 001（D-017，未打上游补丁）**：notebook 改为在 Colab 内自建隔离 Miniforge **Python 3.10** 环境（conda-forge/nvidia `jax=0.6.0 jaxlib=0.6.0=*cuda*`，`CONDA_OVERRIDE_CUDA=12.6`，`numpy<2`、`flax<0.10`，ColabDesign pin e31a56f `--no-deps`，PyRosetta cp310 wheel），BindCraft 子进程全部走 env python；新增硬门 [bindcraft_preflight.py](scripts/bindcraft_preflight.py)（权重下载前验证版本/clear_mem/xla_bridge/GPU matmul）。科学配置零改动。
- **云端尝试 002 preflight（用户 2026-10-01 实测，真实结果）**：隔离 env 本身健康（jax 0.6.0 / GPU / clear_mem 过 / xla_bridge 过），但 `trivial_gpu_matmul` 检查因 `jax.Array.devices()` 返回 `set[Device]` 被错误地用 `[0]` 索引而崩溃——**PRE-FLIGHT TEST-HARNESS BUG**（不是新的环境不兼容）。级联记录缺陷导致额外两条假失败。已修复：`devices()` 全部迭代处理、matmul 检查验证 4 项条件（gpu backend + 完成 + 数值 + GPU 驻留）、下游不可执行检查记入 `"skipped"`（SKIP 语义），环境与 notebook 不变。
- **云端尝试 003 权重下载（用户 2026-10-01 实测，真实结果）**：preflight 修复后 Cell 7 下载 AF2 权重失败——旧代码用 `subprocess.Popen("aria2c … && tar … && touch done.txt")` 发射后不管，再盲轮询 30 分钟；子进程实际**立即退出**（无 aria2c/tar 进程、params≈4 KB、done.txt=false、0 个 .npz），返回码与 stderr 被完全丢弃——**DOWNLOAD-HARNESS BUG**。已修复（attempt-004）：Cell 7 改为**内联可观测 wget harness**（不再依赖外部脚本）——已存在完整 15 文件集则跳过；否则保证 wget、用 `wget -c` 续传、观测子进程（PID/按大小进度/returncode/download.log）、非零即停并打印日志尾部、解包前 `tar -tf` 校验完整性、校验**恰好 15 个**官方 .npz（5 base + 5 pTM + 5 Multimer-v3，之前误写 14）、校验通过才写 done.txt 并删归档。Cell 5 上传文件回退为 3 个。环境与科学配置不变。
- **GPU/VRAM 已实测：T4 15360 MiB（free 值复测时由 preflight/元数据回填）；轨迹时长/峰值占用/吞吐/成功率仍 null（0 条 relaxed 轨迹，禁止推测）**。未创建 compute_escalation.md（无 OOM 证据）。
- Slack 凭据：[reports/slack_provenance/INDEX.md](reports/slack_provenance/INDEX.md)，7 条主张全部 PENDING（用户尚未提供截图）。
- 测试 69/69（[test_stage2.py](tests/test_stage2.py)，含 JAX 版本策略、preflight 设备语义、内联下载 harness 回归）。

### 可靠性合并（2026-10-02，Checkpoint A/B/C 已完成）

- 触发：用户 23 节合并指令——把 Colab smoke 流程重构为可复现、可重启安全、持久化、幂等；科学冻结，不做 EGFR 生产采样。
- **Checkpoint A（已 push + ls-remote 核实 `f8b9f0d1b75926b5e83a7c924558fab7980ace85`）**：新增 `scripts/stage2_paths.py`（唯一路径来源，`STAGE2_PERSISTENT_ROOT` 可覆盖，原子 JSON）、`stage2_preflight.py`（GPU 优先门；matmul 改为 A@A 后逐元素 ≈2048，`devices()` 只迭代；`bindcraft_preflight.py` 降为兼容垫片）、`stage2_configure.py`（确定性两份 target + max1/max3，差异断言仅 `max_trajectories`）、`stage2_checkpoint.py`（manifest 生命周期/检查点校验/LEGACY_CHECKPOINT 证据受限采纳/COMPLETED 不可静默覆盖）、`stage2_run_job.py`（先 manifest 后运行、design_path 持久断言、日志+VRAM 落 Drive、OOM 分类）、`stage2_analyze.py`（复用既有几何引擎，不复制逻辑）、`stage2_orchestrate.py`（GPU_UNAVAILABLE 受控阻断 rc=2，绝不 CPU；PDL1 门=rc0+relaxed PDB；持久 JSON+MD 报告）。
- 报告：[stage2_reliability_consolidation.md](reports/stage2_reliability_consolidation.md)（BUG 001–015 台账，FIXED/证据标注）。
- 回归测试在 A 后扩至 93/93：覆盖 Q（路径来自 config）、R（无 RUNROOT 依赖）、S（模拟 runtime reset 后检查点复用）、T（完成即跳过）、U（配置哈希不匹配强制重跑）、V（零 MPNN 接受仍过门）、W（PDL1 失败阻断 EGFR）、X（非持久 design_path 拒跑）、Y（无 GPU=GPU_UNAVAILABLE，rc 2，建环境前停）、Z（不静默覆盖 COMPLETED）及静态模式守卫。
- **Checkpoint B（已 push + ls-remote 核实 `bc8119886cc3aaf6f57d9b1f8c548cfcff8dffc9`）**：新增 `scripts/ensure_af2_weights.py`——本地精确 15 npz → Drive 解包文件缓存恢复 → Drive 归档解包 → 可观测 `wget -c` 下载（`.part` 续传、pid/rc/耗时/字节/日志/归档 SHA256 全记录，SHA256 仅作观察摘要不宣称验真）；`done.txt` 永不权威；14/16/空文件/陈旧 done 一律拒绝；wget 不可用时 apt 保证安装，绝不假设 aria2c。preflight matmul 逐元素 ≈2048。回归 **105/105**（K/L/M/N/O/P + 下载成功/失败/归档/dry-run/orchestrator 接入）。
- **Checkpoint C（2026-10-02 完成；commit/push/ls-remote 见 git log）**：[cloud/stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb) 重建为 2 markdown + 8 个薄代码 cell（A GPU 门 rc2 绝不 CPU；B Drive 挂载；C 经 Colab Secret `GITHUB_TOKEN` 按**精确 pin commit `bc81198`** clone/fetch 私有仓库并校验 SHA/SHA256，token 不打印，手工 tarball 仅 fallback；D BindCraft `7713aa0` + py3.10/jax0.6.0 隔离环境幂等构建 + crop PDB 身份校验；E preflight；F 权重精确 15 npz/缓存/续传；G 唯一昂贵 cell 运行单一 orchestrator（PDL1 完成即 skip、失败阻断 EGFR）；H 持久报告 + py3Dmol）。文档：README 当前阶段/目录、RUNBOOK §7（新 A–H 流程 + §7.3 reset 恢复 + §7.4 配额 + §7.5 自有 Linux GPU 服务器变体）、HUMAN_ACTIONS A7（先配 GITHUB_TOKEN、再从 A 跑到 G）、DECISIONS D-018。回归 **109/109**（新增 TestThinNotebook 16 个静态守卫：锚点区分 Cell C 工件名与真正调用点、禁止 devices()[/14 计数/RUNROOT/aria2c 16 线程/盲 sleep）。
- 冻结科学零改动：不做 EGFR 生产采样、不跑 broad、不加轨迹、不改表位、不付费；`experimentally_validated` 恒 false；paid_budget=0。

### D-019 per-model relaxation 容错（2026-10-03，BUG 016，Checkpoint D/E）

- 触发：用户六条明确指令——relaxation 未产出预期 per-model PDB 时：①`clean_pdb()` 前先验证产物；②记录 candidate/model 级失败；③保留 unrelaxed PDB；④继续下一个 MPNN candidate；⑤不终止整条 BindCraft run；⑥子进程失败后 manifest 仍必终结。
- 上游事实（pin `7713aa0`，2026-10-03 实拉核实）：`pr_relax`、trajectory relax（bindcraft.py L128）、per-model 打分（L~248）、finalize（L371–389）全部零异常处理；缺 relaxed PDB 即进程崩溃 + 二次 copy 崩溃。
- 交付物：
  - [patches/bindcraft-7713aa0-relax-tolerance.patch](patches/bindcraft-7713aa0-relax-tolerance.patch)：4 文件统一 diff（`generic_utils.py` 新增 `record_stage2_relax_failure` 写 JSONL；`pyrosetta_utils.py` 新增 `RelaxationFailure` + clean_pdb 前后双重校验；`colabdesign_utils.py` per-model try/except→记录/留 PDB/continue；`bindcraft.py` trajectory try/except + 打分块 relaxed 存在门 + finalize 只在现存 relaxed PDB 选优/全无则跳过 candidate）。仅控制流，无科学改动。
  - [scripts/apply_bindcraft_patch.py](scripts/apply_bindcraft_patch.py)：**唯一入口**；HEAD==pin 才允许，`git apply --check` 先行，拒绝漂移/半补丁/错 commit，pre/post SHA256 写 `persistent/metadata/bindcraft_patch.json`。
  - [scripts/stage2_relax_failures.py](scripts/stage2_relax_failures.py)：JSONL 只读解析（坏行计数），`unrelaxed_without_relaxed` 留存清单。
  - [scripts/stage2_run_job.py](scripts/stage2_run_job.py)：子进程段 try/finally，启动异常记 `launch_error`、状态 FAILED，终态 manifest 嵌入 relax 失败汇总字段。
  - [scripts/stage2_orchestrate.py](scripts/stage2_orchestrate.py)：env 后/preflight 前新增 `step_bindcraft_patch()`（dry-run=`SKIPPED_DRY_RUN`，失败=`BINDCRAFT_PATCH_FAIL`），报告 JSON/MD 带补丁状态与每 job 失败计数。
  - [cloud/stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb) Cell D：pin checkout SHA 校验后、长环境构建前调用应用器并断言 APPLIED/ALREADY_APPLIED（reset 后幂等）。
  - pristine 测试 oracle：[tests/fixtures/bindcraft_7713aa0_pristine/](tests/fixtures/bindcraft_7713aa0_pristine/)（4 上游文件 + PROVENANCE SHA256；仅测试用，不进 results/ 或 submission/）。
- 验证：临时 git 树全生命周期（NOT_PATCHED→APPLIED→ALREADY_APPLIED→VERIFIED）、漂移拒绝、半补丁歧义、commit 不匹配、CLI 元数据；坏行 JSONL 解析；启动失败仍终结 FAILED manifest。回归 **124/124**（unittest 与 .venv pytest 双跑）。
- 提交（两提交 pin 舞，push 后用 ls-remote 核实并回填）：D=____（含补丁/应用器/测试/文档，Cell C PROJECT_PIN 仍指 C `bc81198`）；E=____（仅把 PROJECT_PIN 与 `test_frozen_pins_present` 字面量 bump 到 D）。

## 当前 Blockers（真实阻挡）

1. **AWAITING_CLOUD_SMOKE_RERUN (A7)** — 可靠性合并 A/B/C + D-019 容错补丁已完成（BUG 001–016 全部 FIXED 或 EVIDENCE；124/124 测试）。等用户在 Colab：配 `GITHUB_TOKEN` secret → T4 GPU → 上传薄 notebook → 从 Cell A 顺序跑到 G（Cell D 自动幂等打补丁）；已持久化的 PDL1 run 会被采纳为 LEGACY_CHECKPOINT（或校验通过直接 SKIP），权重走 Drive 缓存。reset/配额中断后从 A 跑到 G 即可恢复。PDL1 环境门（rc0 + relaxed PDB）未重新证实前阶段 3 不得开始。
2. **MOUSE_CONSTRUCT_PROOF_PENDING** — mouse 25–647 仅 Slack 转述（A2/A6）；不阻塞 human smoke，阻塞阶段 4 mouse 验证。
3. **SLACK_PROVENANCE_PENDING (A6)** — 7 条 Slack 主张无截图（含上条）；[INDEX](reports/slack_provenance/INDEX.md) 全 PENDING。
4. **ELIGIBILITY/REGISTRATION_PENDING** — Track 3 资格/注册用户尚未确认（A3）；不阻塞技术 smoke，阻塞提交。
5. **DISK_TIGHT** — 本地空间有限；权重与产物均在云端（A4，非阻塞）。

## 依赖

- 阶段 2：A+ 已批准；需本人在 Colab 用新版薄 notebook 跑/恢复（配 GITHUB_TOKEN secret → T4 → Cell A→H）；付费必须先批准。
- 阶段 4：另依赖 A2/A6 mouse 官方构建体凭据。

## 下一动作（按优先级）

1. **A7（用户，跑/恢复 Stage 2 smoke）**：按 [HUMAN_ACTIONS.md](HUMAN_ACTIONS.md) A7 与 [RUNBOOK.md](RUNBOOK.md) §7.2——Colab Secrets 加 `GITHUB_TOKEN`（读私有仓库的 PAT；不愿配则 Cell C 手工传 tarball）；T4 GPU runtime；上传 [cloud/stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb)；从 Cell A 顺序跑到 H，数字不改。G 是唯一昂贵 cell（PDL1 合法检查点/legacy PDB 自动跳过，失败即阻断 EGFR）。中断/reset/配额被拒后重连 GPU 再从 A 跑到 G 即恢复（§7.3/§7.4）。回传 Drive `BindCraft/stage2_smoke/persistent/{reports,metadata,logs}` 与 relaxed PDB。
2. 我收到实测产物后写 Stage 2 smoke 报告：环境 vs 靶点故障判定、B 接触/迁移/边缘伪影诊断、仅按实测吞吐给批次建议；若 OOM 两次才写 compute_escalation.md。
3. A6 Slack 截图；A3 Track 3 资格确认（一次性问题，见 HUMAN_ACTIONS）。
4. smoke 报告经用户复核前不扩大生成、不跑 broad hotspot、不付费。

## 批准记录

- 无付费/公开/提交类批准。paid_budget=0。
- A+ 已批准（D-013）；阶段 2 smoke 范围已由用户 2026-10-01 指令限定（D-014），生产生成未获批准。
