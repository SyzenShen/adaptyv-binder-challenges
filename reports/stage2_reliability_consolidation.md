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

## 一、缺陷台账 BUG 001–015

| ID | 现象 | 根因 | 状态 | 修复位置 |
|----|------|------|------|----------|
| 001 | Colab Python 3.13 + JAX 0.11.1 下 `jax.lib.xla_bridge` 被移除，BindCraft/colabdesign 链式崩溃 | JAX 0.8.0 起删除 xla_bridge；Colab 默认版本不受我们控制 | FIXED | 隔离 py3.10 / jax 0.6.0 conda env；`stage2_preflight.py` 版本上限策略 |
| 002 | `y.devices()[0]` 抛 `TypeError: 'set' object is not subscriptable` | `jax.Array.devices()` 返回 `set[Device]`，不是 list | FIXED | `stage2_preflight.gpu_devices()` 一律迭代，静态检查禁止 `devices()[` |
| 003 | 上游检查失败后连锁报假错，掩盖根因 | 下游探测在依赖不可用时仍当 FAIL | FIXED | 失败根因记 FAIL；不可执行的探测记 `status=SKIP` 并指向根因 |
| 004 | 权重下载 `Popen` 后 fire-and-forget，盲目 30 分钟轮询，进程死了也不知道 | 下载不可观测 | FIXED | `ensure_af2_weights.py`：阻塞观察下载，记录 pid/rc/耗时/字节/日志 |
| 005 | `aria2c` 在运行时不一定存在 | 假设预装 | FIXED | 预检下载器；无则用可保证的 `wget -c`（PATH 注入可测试） |
| 006 | 旧逻辑只数权重文件数（`==14`），官方 tar 实际**恰好 15 个 npz** | 计数过弱，缺/多/改名都会漏判 | FIXED（Checkpoint B） | 校验精确 15 个文件名集合（5 base + 5 `_ptm` + 5 `_multimer_v3`） |
| 007 | 用陈旧 `done.txt` 判定权重就绪 | 文件标记可被半成品/旧运行留下 | FIXED（Checkpoint B） | done 标记永不权威；以 15 个 npz 实文件 + 校验为准 |
| 008 | 每次手工上传 4 个项目文件，易漏易错 | 工件获取依赖人工 | FIXED（Checkpoint C） | notebook 按 pin 的 git commit 获取项目工件；手工上传仅作 fallback |
| 009 | Cell 10 在运行时重启后失败（`RUNROOT` 未定义） | 可执行逻辑依赖前序 cell 的内核变量 | FIXED | 所有路径来自 `stage2_paths.Paths`（`STAGE2_PERSISTENT_ROOT` 可覆盖） |
| 010 | 门控猜 `RUNROOT/.../Trajectory/Relaxed`，与真实 design_path 脱节 | 路径重复推断 | FIXED | relaxed 目录一律由 config/manifest 里的 `design_path` 推导 |
| 011 | 运行时 reset 抹掉 `/content`（env、bindcraft、PDB、settings 全没了），但历史输出还显示在 notebook 里造成错觉 | Colab 临时盘非持久 | FIXED | 昂贵产物全部落 Drive `persistent/` + job 目录；reset 后按门控重建临时件 |
| 012 | PDL1 成功 run 曾真实持久化到 Drive（`.../pdl1_official_smoke/Trajectory/Relaxed/PDL1_smoke_l65_s909721.pdb`） | 反证昂贵输出必须持久 | EVIDENCE | 持久布局 + 运行前断言 design_path 在 Drive 根下 |
| 013 | 已完成的 PDL1（约 30 分钟）每次重跑 | 无完成检查点 | FIXED | 合法 COMPLETED 检查点自动 SKIP；配置哈希/BindCraft commit 不匹配则重跑 |
| 014 | 曾把“单条轨迹零 MPNN 接受”误判为环境失败 | 混淆环境门控与设计过滤器 | FIXED | PDL1 环境门控 = rc==0 且 ≥1 个非空 relaxed PDB；过滤器结果单独记录 |
| 015 | GPU 配额拒绝（“Cannot connect to GPU backend due to usage limits.”）被当作可继续的情况 | 无受控阻断语义 | FIXED | GPU 缺失/配额拒绝 = `GPU_UNAVAILABLE`/`COMPUTE_QUOTA_BLOCKED`，建环境前停止，绝不 CPU 回退 |

## 二、架构（合并后）

- `scripts/stage2_paths.py`：唯一路径来源（持久根 + 临时件常量 + 原子 JSON + 哈希）。
- `scripts/stage2_preflight.py`：GPU/版本/真 matmul 门控（`bindcraft_preflight.py` 为兼容垫片）。
- `scripts/ensure_af2_weights.py`：本地 → Drive 缓存 → 可观测下载（Checkpoint B）。
- `scripts/stage2_configure.py`：确定性生成两份 target + max1/max3 advanced，仅
  `max_trajectories` 与官方默认不同，并断言差异集合。
- `scripts/stage2_checkpoint.py`：manifest 生命周期、检查点校验、legacy 检查点诚实采纳。
- `scripts/stage2_run_job.py`：先写 manifest 再跑；日志/VRAM 落 Drive；OOM 分类；不覆盖完成态。
- `scripts/stage2_analyze.py`：复用 `analyze_bindcraft_run.py` 做几何分析，不复制逻辑。
- `scripts/stage2_orchestrate.py`：单一命令串起 12 步，输出持久 JSON+MD 报告。
- notebook 仅为 A–H 薄前端；科学算法不在 notebook 内。

## 三、持久目录与缓存（BUG 011/012）

```
<STAGE2_PERSISTENT_ROOT>/
  persistent/
    checkpoints/<job>/run_manifest.json
    configs/<config>.json + config_manifest.json
    logs/<job>.log, <job>_vram.csv, download_*.log
    metadata/orchestration_state.json, preflight.json
    reports/<job>_geometry.json, stage2_smoke_report.{json,md}
    cache/alphafold/                      # AF2 权重缓存（15 npz）
  pdl1_official_smoke/                    # BindCraft design_path（含 Trajectory/Relaxed）
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

## 六、测试

stdlib `unittest`：`tests/test_stage2.py`（A–Z 合并回归 + 静态检查），并保持
`tests/` 其余套件通过；另跑 `.venv` pytest。伪造 subprocess / PATH 注入 / 临时目录 +
`STAGE2_PERSISTENT_ROOT`；不下载任何权重、不跑 GPU（单元测试/合成数据/dry-run only）。

## 七、提交检查点

- Checkpoint A：paths/preflight/configure/checkpoint/run_job/analyze/orchestrate + GPU 门 + manifest。
- Checkpoint B：AF2 缓存/下载器/15 文件校验 + matmul 元素级语义修正。
- Checkpoint C：薄 notebook + 恢复 UX + 文档。

每个检查点：测试 → commit → push → `git ls-remote` 确认远端 SHA。
