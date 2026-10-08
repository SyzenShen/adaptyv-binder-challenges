# Stage 2 可靠性合并报告（BindCraft Colab smoke workflow）

日期：2025 起（随 Checkpoint A/B/C 持续更新）
范围：将 attempt-004 的 Colab 冒烟流程重构为**可复现、可重启安全、持久化、幂等**的工作流。
冻结科学结论（未经批准不得更改）：
Epitope envelope B = human EGFR UniProt 390–403 + 421–431；hotspots
`390,393,399,421,424,431`；crop Domain III 310–481；binder 80 aa；EGFR 上限 3 条轨迹；
PDL1 对照 hotspot 56 / 65 aa / 上限 1 条；BindCraft pin
`7713aa0d0d351e4117a8befeb8541f3a8ebd3368`；默认过滤器 + 官方
`default_4stage_multimer.json`（仅改 `max_trajectories`）；无 hardtarget / mutation / CPU 回退。

证据来源：`reports/stage2_environment_failure_001.md`（attempt-002/003/004 记录）、
Colab 运行日志、用户 Drive 中实际持久化的 PDL1 relaxed PDB。
所有结果区分 `software_test_passed` / `model_run_completed` /
`computational_filter_passed` / `experimentally_validated`；本项目无湿实验，最后一项恒为 false。

## 一、缺陷台账 BUG 001–016

| ID | 现象 | 根因 | 状态 | 修复位置 |
|----|------|------|------|----------|
| 001 | Colab Python 3.13 + JAX 0.11.1 下 `jax.lib.xla_bridge` 被移除，BindCraft/colabdesign 链式崩溃 | JAX 0.8.0 起删除 xla_bridge；Colab 默认版本不受我们控制 | FIXED | 隔离 py3.10 / jax 0.6.0 conda env；`stage2_preflight.py` 版本上限策略 |
| 002 | `y.devices()[0]` 抛 `TypeError: 'set' object is not subscriptable` | `jax.Array.devices()` 返回 `set[Device]`，不是 list | FIXED | `stage2_preflight.gpu_devices()` 一律迭代，静态检查禁止 `devices()[` |
| 003 | 上游检查失败后连锁报假错，掩盖根因 | 下游探测在依赖不可用时仍当 FAIL | FIXED | 失败根因记 FAIL；不可执行的探测记 `status=SKIP` 并指向根因 |
| 004 | 权重下载 `Popen` 后 fire-and-forget，盲目 30 分钟轮询，进程死了也不知道 | 下载不可观测 | FIXED | `ensure_af2_weights.py`：阻塞观察下载，记录 pid/rc/耗时/字节/日志 |
| 005 | `aria2c` 在运行时不一定存在 | 假设预装 | FIXED | 预检下载器；无则用可保证的 `wget -c`（PATH 注入可测试） |
| 006 | 旧逻辑只数权重文件数（`==14`），官方 tar 实际**恰好 15 个 npz** | 计数过弱，缺/多/改名都会漏判 | FIXED | `ensure_af2_weights.py`：校验精确 15 个文件名集合（5 base + 5 `_ptm` + 5 `_multimer_v3`），回归 K/L/M |
| 007 | 用陈旧 `done.txt` 判定权重就绪 | 文件标记可被半成品/旧运行留下 | FIXED | done 标记永不权威（仅记录其存在）；以 15 个 npz 实文件精确校验为准，回归 N |
| 008 | 每次手工上传 4 个项目文件，易漏易错 | 工件获取依赖人工 | FIXED | notebook Cell C 按精确 pin commit `bc81198` 经 git（Colab Secret token，不打印）获取项目工件并校验 SHA256；手工 tarball 上传仅作 fallback |
| 009 | Cell 10 在运行时重启后失败（`RUNROOT` 未定义） | 可执行逻辑依赖前序 cell 的内核变量 | FIXED | 所有路径来自 `stage2_paths.Paths`（`STAGE2_PERSISTENT_ROOT` 可覆盖） |
| 010 | 门控猜 `RUNROOT/.../Trajectory/Relaxed`，与真实 design_path 脱节 | 路径重复推断 | FIXED | relaxed 目录一律由 config/manifest 里的 `design_path` 推导 |
| 011 | 运行时 reset 抹掉 `/content`（env、bindcraft、PDB、settings 全没了），但历史输出还显示在 notebook 里造成错觉 | Colab 临时盘非持久 | FIXED | 昂贵产物全部落 Drive `persistent/` + job 目录；reset 后按门控重建临时件 |
| 012 | PDL1 成功 run 曾真实持久化到 Drive（`.../pdl1_official_smoke/Trajectory/Relaxed/PDL1_smoke_l65_s909721.pdb`） | 反证昂贵输出必须持久 | EVIDENCE | 持久布局 + 运行前断言 design_path 在 Drive 根下 |
| 013 | 已完成的 PDL1（约 30 分钟）每次重跑 | 无完成检查点 | FIXED | 合法 COMPLETED 检查点自动 SKIP；配置哈希/BindCraft commit 不匹配则重跑 |
| 014 | 曾把“单条轨迹零 MPNN 接受”误判为环境失败 | 混淆环境门控与设计过滤器 | FIXED | PDL1 环境门控 = rc==0 且 ≥1 个非空 relaxed PDB；过滤器结果单独记录 |
| 015 | GPU 配额拒绝（“Cannot connect to GPU backend due to usage limits.”）被当作可继续的情况 | 无受控阻断语义 | FIXED | GPU 缺失/配额拒绝 = `GPU_UNAVAILABLE`/`COMPUTE_QUOTA_BLOCKED`，建环境前停止，绝不 CPU 回退 |
| 016 | 单个 MPNN candidate/model 的 PyRosetta relaxation 未产出预期 per-model relaxed PDB（或 `clean_pdb()` 作用于缺失/空文件）时，异常无任何捕获，直接杀死整个 BindCraft 进程；finalize 再 `copy` 缺失 relaxed PDB 二次崩溃；子进程启动失败时 manifest 停在 RUNNING | 上游 pin `7713aa0` 的 `pr_relax`、trajectory relax、per-model 打分循环、finalize 均零异常处理；删除 unrelaxed PDB 的步骤在打分块内，失败即丢证据 | FIXED（D-019，唯一授权上游窄补丁） | `patches/bindcraft-7713aa0-relax-tolerance.patch`（4 文件）经 `scripts/apply_bindcraft_patch.py` 确定性应用：clean_pdb 前后双重校验+`RelaxationFailure`；失败写 `relax_failures.jsonl`、保留 unrelaxed、continue；finalize 只在现存 relaxed PDB 中选优；`stage2_run_job.py` try/finally 必终结 manifest（`launch_error`）；`stage2_relax_failures.py` 解析汇总 |

## 二、架构（合并后）

- `scripts/stage2_paths.py`：唯一路径来源（持久根 + 临时件常量 + 原子 JSON + 哈希）。
- `scripts/stage2_preflight.py`：GPU/版本/真 matmul 门控（`bindcraft_preflight.py` 为兼容垫片）。
- `scripts/ensure_af2_weights.py`：本地精确 15 文件 → Drive 解包缓存 → Drive 归档 → 可观测 `wget -c` 下载（pid/rc/字节/耗时/日志/观察性 SHA256）。
- `scripts/stage2_configure.py`：确定性生成两份 target + max1/max3 advanced，仅
  `max_trajectories` 与官方默认不同，并断言差异集合。
- `scripts/stage2_checkpoint.py`：manifest 生命周期、检查点校验、legacy 检查点诚实采纳。
- `scripts/stage2_run_job.py`：先写 manifest 再跑；日志/VRAM 落 Drive；OOM 分类；不覆盖完成态。
- `scripts/stage2_analyze.py`：复用 `analyze_bindcraft_run.py` 做几何分析，不复制逻辑。
- `scripts/stage2_orchestrate.py`：单一命令串起 12 步，输出持久 JSON+MD 报告；
  在 env 检查后、preflight 前幂等执行 D-019 补丁步骤（失败态 `BINDCRAFT_PATCH_FAIL`）。
- notebook 仅为 A–H 薄前端；科学算法不在 notebook 内。
- `patches/bindcraft-7713aa0-relax-tolerance.patch`：唯一授权的上游窄补丁
  （D-019/BUG 016），只改异常处理与控制流，不改任何科学参数/过滤器。
- `scripts/apply_bindcraft_patch.py`：补丁唯一入口——HEAD 必须等于 pin，
  `git apply --check` 先行，拒绝漂移/半补丁/错 commit，写 pre/post SHA256 元数据。
- `scripts/stage2_relax_failures.py`：只读解析 `relax_failures.jsonl`（坏行计数
  不中止），列出“有 unrelaxed 无 relaxed”的留存 PDB，供 manifest/报告嵌入。

## 三、持久目录与缓存（BUG 011/012）

```
<STAGE2_PERSISTENT_ROOT>/
  persistent/
    checkpoints/<job>/run_manifest.json
    configs/<config>.json + config_manifest.json
    logs/<job>.log, <job>_vram.csv, download_*.log
    metadata/orchestration_state.json, preflight.json, bindcraft_patch.json
    reports/<job>_geometry.json, stage2_smoke_report.{json,md}
    cache/alphafold/                      # AF2 权重缓存（15 npz）
  pdl1_official_smoke/                    # BindCraft design_path（含 Trajectory/Relaxed、relax_failures.jsonl）
  egfr_d3_B_conservative/
```

权重缓存策略（为何缓存“解包后的文件”而非仅归档）：
见 `scripts/ensure_af2_weights.py` 文档字符串；以恢复到 `bindcraft/params` 后能通过
15 文件精确校验为准；归档若存在则仅作可重复下载的来源，不宣称其真实性。

## 四、PDL1 检查点与 skip 行为（BUG 013/014，§10/§13）

- 校验条件：manifest COMPLETED；target/advanced 配置 SHA256 匹配；BindCraft commit 匹配；
  真实 design_path 下 ≥1 个非空可读 relaxed PDB（有记录时 SHA256 必须匹配）。
- 命中时打印 `PDL1 CHECKPOINT VALID` / `SKIPPING EXPENSIVE PDL1 RERUN`。
- 合并前成功的 run 无 manifest：仅当 Drive 上能验证 relaxed PDB 时，采纳为
  `LEGACY_CHECKPOINT`，不可重建的来源（当时配置哈希等）显式标为未验证，绝不编造。
- 环境门控只看 rc==0 + relaxed PDB；`final_design_count`/过滤器结果单独记录。

## 五、reset / 配额处理与持久化（BUG 011/015）

- reset 后 `/content` 清空：重跑 notebook 建环境/取工件/校验权重缓存，昂贵 job 因检查点而跳过。
- GPU 不可用（含配额拒绝）：orchestrator 退出码 2，状态 `GPU_UNAVAILABLE` +
  `COMPUTE_QUOTA_BLOCKED` 语义，在任何构建/下载前停止；绝不回退 CPU。
- 恢复指引见 RUNBOOK「Stage 2 运行时重置后如何恢复」。

## 六、Per-model relaxation 容错（D-019 / BUG 016）

用户 2026-10-03 明确六条语义，逐条对应实现：

1. **先验证再 clean**：补丁在 `pr_relax` 内 `pose.dump_pdb` 之后、`clean_pdb()`
   之前校验 relaxed PDB 存在且大小 >0（零字节删除并抛 `RelaxationFailure`），
   `clean_pdb` 之后再校验一次；外层 except 清理零字节产物后抛出。
2. **candidate/model 级记录**：每个失败向 `<design_path>/relax_failures.jsonl`
   追加一行 JSON（`time_utc/stage/candidate/model/unrelaxed 与 expected relaxed
   路径及存在性/字节数/error_type/error[:500]/retained_unrelaxed/action`），
   并打印 `[STAGE2_RELAX_FAILURE] ...`。
3. **保留 unrelaxed PDB**：跳过含删除逻辑的打分块，MPNN 未 relaxed 复合体留在盘上。
4. **继续下一个 MPNN candidate**：per-model 循环 `continue`
   （`action=skipped_model_continue`）。
5. **不终止整条 run**：trajectory relax 失败记录后 `trajectory_n += 1;
   gc.collect(); continue`（`skipped_trajectory_continue`）；打分循环对缺失
   relaxed PDB 的模型只跳过 relaxed-only 统计；finalize 仅在**现存** relaxed
   PDB 中按 pLDDT 选优，一个都没有则记录 `mpnn_finalize/RelaxedPDBMissing`
   并跳过该 candidate（`skipped_candidate_continue`），不复制不存在的文件。
6. **manifest 必终结**：`stage2_run_job.py` 子进程段 try/finally——子进程启动
   异常（如解释器不存在）记 `launch_error={error_type,error}`、状态 FAILED，
   无论如何写终态 manifest（returncode/end_time/wall/peak_vram），并嵌入
   `relax_failure_log_present / relax_failure_count /
   relax_failures_by_stage / relax_failures_by_error_type /
   relax_failures_corrupt_lines / relax_failures / unrelaxed_without_relaxed`。

应用纪律：BindCraft pin `7713aa0` 不变；补丁只能由
`scripts/apply_bindcraft_patch.py` 应用（Cell D 在 checkout 校验后、长环境构建前
调用；orchestrator 幂等再调一次），状态 APPLIED/ALREADY_APPLIED/VERIFIED 才放行；
COMMIT_MISMATCH / PATCH_STATE_AMBIGUOUS / APPLY_CHECK_FAILED 一律 rc1 阻断。
补丁前四文件 SHA256 以 `tests/fixtures/bindcraft_7713aa0_pristine/PROVENANCE.txt`
为测试 oracle。**科学参数、过滤器、设置零改动。**

## 七、测试

stdlib `unittest`：`tests/test_stage2.py`（A–Z 合并回归 + 静态检查），并保持
`tests/` 其余套件通过；另跑 `.venv` pytest。伪造 subprocess / PATH 注入 / 临时目录 +
`STAGE2_PERSISTENT_ROOT`；不下载任何权重、不跑 GPU（单元测试/合成数据/dry-run only）。
当前 **124/124**（Checkpoint D 后；在 Checkpoint C 的 109 上新增 15 个：
pristine 夹具 SHA oracle、补丁六指令静态守卫、临时 git 树中的
NOT_PATCHED→APPLIED→ALREADY_APPLIED→VERIFIED 全生命周期、漂移拒绝、半补丁歧义、
commit 不匹配、CLI 元数据落盘、JSONL 解析（坏行容忍/by-stage/by-error-type）、
留存 PDB 列举、子进程启动失败仍终结 FAILED manifest 并嵌入失败记录、
orchestrator 补丁步骤 dry-run/接线、Cell D 补丁锚点与顺序）。

## 八、提交检查点

- Checkpoint A：paths/preflight/configure/checkpoint/run_job/analyze/orchestrate + GPU 门 + manifest。
  已 push 并 ls-remote 核实：`f8b9f0d1b75926b5e83a7c924558fab7980ace85`。
- Checkpoint B：AF2 缓存/下载器/15 文件校验 + matmul 元素级语义修正。
  已 push 并 ls-remote 核实：`bc8119886cc3aaf6f57d9b1f8c548cfcff8dffc9`
  （曾作为 notebook Cell C 的项目工件 pin；Checkpoint E 起改 pin D）。
- Checkpoint C：薄 notebook（A–H）、pin-commit 工件获取与 tarball fallback、
  恢复 UX、README/RUNBOOK/HUMAN_ACTIONS/DECISIONS 文档更新。SHA 以 git log /
  `git ls-remote` 与最终交接报告为准（提交无法自引其 SHA）。
- Checkpoint D（2026-10-03，D-019/BUG 016）：relax-tolerance 补丁 + 应用器 +
  pristine 测试夹具 + JSONL 解析 + run_job 必终结 manifest + orchestrator/Cell D
  接线 + 文档，回归 124/124。已 push 并 ls-remote 核实：
  `452ac95c810614ad5c7602ef652644a4c63382c6`（该提交内 Cell C PROJECT_PIN
  仍指 C `bc81198`）。
- Checkpoint E（2026-10-03）：仅 PROJECT_PIN bump（notebook Cell C +
  `test_frozen_pins_present` 断言）到 Checkpoint D 的 SHA，并回填本文档/
  STATE/RUNBOOK；E 自身 SHA 见 git log / `git ls-remote`（提交无法自引）。

每个检查点：测试 → commit → push → `git ls-remote` 确认远端 SHA。
