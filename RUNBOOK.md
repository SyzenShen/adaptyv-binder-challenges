# RUNBOOK — 命令手册（在本机 Mac 执行；云端命令另行标注）

约定：所有命令从仓库根目录执行。token/凭据一律不写入本文件、代码、notebook 输出或日志。

## 1. 日常测试

```bash
# 零三方依赖：系统 Python 3.10 直接跑（阶段 0 验收命令）
python3 -m unittest discover -s tests -v

# 隔离分析环境（可选，需要时才创建；不修改全局 Python）
python3 -m venv .venv
.venv/bin/pip install -r requirements-min.txt
.venv/bin/python -m pytest -q
```

参数说明：`-m unittest` 以模块方式运行标准库测试框架；`discover -s tests` 自动发现 tests/ 下用例；`-v` 显示每个用例名。正常输出末尾是 `OK`；停止条件：任何 `FAILED`。

## 2. 环境复核（怀疑机器状态变化时）

```bash
sw_vers && uname -m                       # macOS 版本与架构（期望 x86_64）
sysctl -n hw.memsize                      # 物理内存字节数（34359738368 = 32GB；这是内存不是显存）
df -h /System/Volumes/Data                # 真实可用磁盘
python3 --version; git --version; gh --version
gh auth status                            # 期望：Logged in to github.com as <个人账号>
curl -sS -o /dev/null -w '%{http_code}\n' https://proteinbase.com   # 期望 200
```

## 3. Git 阶段协议（每个大阶段末尾）

```bash
git status --short                        # 只暂存本阶段相关文件
git diff --cached                         # 复核：无密钥、无大文件、无 synthetic 数据混入
git commit -m "phaseN: <真实完成项>"
git push
# push 后必须远端核实（二选一）：
gh api repos/<owner>/<repo>/commits/<branch> --jq '.sha'
git ls-remote origin <branch>
```

- push 失败 → STATE.md 写 **PUSH_BLOCKED**，不得进入下一大阶段。
- 禁止 `--force`、清理式 reset、覆盖他人历史。
- 大文件策略：`git status` 前确认 `.gitignore` 覆盖 weights/models/data 大文件；大产物写 manifest（路径、字节数、SHA256、生成配置）。

## 4. 数据下载（阶段 1 起，端点已在阶段 0 验证 200）

```bash
# 原始文件必须保留 URL、下载时间与 SHA256；示例（阶段 1 正式执行时落盘 data/raw/）：
curl -fSL "https://rest.uniprot.org/uniprotkb/P00533.fasta" -o data/raw/P00533.fasta
shasum -a 256 data/raw/P00533.fasta
# 结构（mmCIF，约数十 MB；.gitignore 已排除，文件留本地/云端，不入库）
curl -fSL "https://files.rcsb.org/download/6ARU.cif" -o data/raw/6ARU.cif
```

`-f` HTTP 错误即失败退出；`-S` 显示错误；`-L` 跟随跳转。停止条件：SHA256 与 manifest 记录不一致则重下并记录。

## 5. Colab（阶段 2，云端 Linux/NVIDIA runtime 内执行）

- notebook 第一格必须打印：GPU 型号、显存、`nvidia-smi` 驱动/CUDA、磁盘、Python/JAX 版本、BindCraft commit。
- 无 GPU → 直接标记失败，不降级伪装成功。
- 输入/运算放 runtime 盘；阶段产物复制到**专用 Drive 结果目录**并写 manifest；回传到本机 `data/inbox/` 后由 importer 校验，再进入 results/。
- 禁止 SSH 隧道、保活脚本、多账户；空闲断连属官方策略，靠断点续跑（不可覆盖 run_id + sequence hash）而不是防断开。

## 6. 失败处理纪律

安装/构建最多两次有依据的尝试；仍失败即记录现象、已试方案、替代路径并停下，不随机改依赖。任何命令输出若意外包含 token，立即作废该日志并轮换凭据。

## 7. 阶段 2 BindCraft smoke（2026-10-02 可靠性合并版）

背景：云端尝试 001–004 的环境/harness 问题与修复历史见
[reports/stage2_environment_failure_001.md](reports/stage2_environment_failure_001.md)；
2026-10-02 按用户合并指令把流程重构为**可复现、可重启安全、持久化、幂等**的形态，
缺陷台账 BUG 001–015 见
[reports/stage2_reliability_consolidation.md](reports/stage2_reliability_consolidation.md)。
科学配置冻结不变（PDL1 hotspot 56/65 aa/cap 1；EGFR B 包络 6 hotspot/80 aa/cap 3；
官方 default filters + 4stage multimer，仅 `max_trajectories` 不同）。

### 7.1 架构一句话

notebook [cloud/stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb)
只是 A–H 八个薄 cell；所有可执行逻辑在 pin 的 `scripts/stage2_*.py` +
`ensure_af2_weights.py` 中。昂贵产物全部落 Drive
`MyDrive/BindCraft/stage2_smoke/`（`persistent/{checkpoints,configs,logs,metadata,reports,cache}`
与两个 job 目录）；`/content` 下一切都可重建。

### 7.2 首次运行（用户 A7）

1. 准备 Colab Secret：左栏钥匙图标 → Secrets → 添加 `GITHUB_TOKEN`（对私有仓库
   `SyzenShen/egfr-binder-challenge` 有读权限的 PAT；notebook 只通过 git header
   使用，绝不打印）。无 token 时 Cell C 支持手工上传仓库快照 tarball 作为 fallback。
2. Runtime → Change runtime type → **T4 GPU**；上传新版 notebook。
3. 自上而下运行 **Cell A→H，数字一律不改**：
   - **A** GPU 门：无 GPU / 配额拒绝立即打印 `GPU_UNAVAILABLE` /
     `COMPUTE_QUOTA_BLOCKED` 并以退出码 2 停止，**绝不回退 CPU**；
   - **B** 挂载 Drive 并设定 `STAGE2_PERSISTENT_ROOT`；
   - **C** clone/fetch 项目**精确 pin commit** `bc81198`，校验 SHA，记录
     crop PDB 与脚本 SHA256；
   - **D** BindCraft pin `7713aa0` + 隔离 Miniforge py3.10/jax 0.6.0 环境
     （幂等，首次 10–25 分钟）+ 冻结 crop PDB 就位与身份校验；
   - **E** 隔离 env 内 preflight 硬门（版本/clear_mem/xla_bridge/真 GPU
     matmul，逐元素 ≈2048）；
   - **F** AF2 权重：本地精确 15 npz → Drive 缓存恢复 → Drive 归档解包 →
     可观测 `wget -c` 续传下载（pid/rc/字节/耗时/日志/SHA256 全记录；
     `done.txt` 永不权威；14/16/空文件均拒绝）；
   - **G** **唯一昂贵 cell，"RUN OR RESUME STAGE 2 SMOKE"**：一个 orchestrator
     子命令；PDL1 合法检查点自动 skip（约 30 分钟不重跑）；PDL1 环境门
     （rc==0 且 ≥1 relaxed PDB；零 MPNN 接受不算环境失败）不过则阻断 EGFR；
   - **H** 读持久 JSON/MD 报告并 py3Dmol 目检。
4. 完成后回传 `persistent/reports/`、`persistent/metadata/`、`persistent/logs/`
   与 relaxed PDB（或分享整个 Drive 文件夹）。

### 7.3 Stage 2 运行时重置（reset）后如何恢复

Colab 释放/reset runtime 会抹掉 `/content`（env、bindcraft、权重、PDB、settings
全没了；notebook 历史输出仍可见**不代表当前状态**）。恢复步骤：

1. 重新连接 **GPU** runtime（不是 CPU）。
2. 打开 pin 的同一个 notebook，**从 A 顺序跑到 G**。
3. A–D 自动重建临时件（环境若 Miniforge 层也被抹则重建，约 10–25 分钟；
   Drive 文件不受影响）。
4. F 从 Drive 缓存恢复 15 个权重文件，通常**零下载**。
5. G 读 `persistent/checkpoints/<job>/run_manifest.json`：PDL1 合法 COMPLETED
   检查点（配置哈希 + BindCraft commit + relaxed PDB SHA 匹配）直接
   `CHECKPOINT_REUSED`/`SKIPPING EXPENSIVE PDL1 RERUN`；合并前已成功但无
   manifest 的 PDL1 run（Drive 上有真实 relaxed PDB）被诚实采纳为
   `LEGACY_CHECKPOINT`（不可重建的来源明确标注未验证，不编造）。
6. 看到 `STAGE 2 SMOKE COMPLETE` 或 quota 提示即止；把报告发回。

### 7.4 GPU 配额被拒时

现象："Cannot connect to GPU backend due to usage limits." 或 nvidia-smi 缺失。
语义：`GPU_UNAVAILABLE` / `COMPUTE_QUOTA_BLOCKED`（Cell A 退出码 2；orchestrator
同样 rc=2）。这是算力分配状态，**不是** BindCraft 失败；不建环境、不下载权重、
不跑 CPU。等待配额恢复后只需重跑 A→G，完成的工作不会重做。

### 7.5 未来在自有 Linux GPU 服务器上运行（无 Colab/Drive 时）

orchestrator 不依赖 Colab：把持久根指到本机持久盘，直接运行

```bash
export STAGE2_PERSISTENT_ROOT=/data/bindcraft/stage2_smoke
/opt/bindcraft_env/bin/python scripts/stage2_orchestrate.py \
  --repo-dir /path/to/egfr-binder-challenge \
  --bindcraft-dir /opt/bindcraft \
  --bindpy /opt/bindcraft_env/bin/python
```

环境按 D 格同一 conda spec 手工建；权重走同一缓存/下载模块；GPU 门同样是
nvidia-smi 第一关，rc=2 即阻断。不需要 Cell B（drive.mount）与 C（Colab secret）。

### 7.6 判读与纪律

completed ≠ accepted；`final_design_count` 只数 BindCraft `Accepted/` 目录，
零接受要与环境失败分开记录；pLDDT/ipTM/PAE 不是亲和力。OOM 两次（factory reset
后最多再试 1 次）即停并交回 preflight/metadata/log，由我写 compute_escalation.md。
smoke 复核前不跑 broad、不加轨迹、不改表位、不付费。

本机制备（本机可复现）：

```bash
.venv/bin/python scripts/make_domain3_pdb.py      # 生成裁剪 PDB + manifest（幂等）
python3 -m unittest discover -s tests             # 109/109 期望
```

本地分析回传产物（无 GPU 也能跑，纯标准库）：

```bash
python3 scripts/analyze_bindcraft_run.py \
  --run-dir data/inbox/egfr_d3_B_conservative \
  --out results/stage2/egfr_d3_B_conservative_geometry.json
```
