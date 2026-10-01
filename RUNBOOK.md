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

## 7. 阶段 2 BindCraft smoke（2026-10-01 起）

背景：云端尝试 001 在**环境层**失败——Colab 滚动镜像 Py 3.13.15 / JAX 0.11.1 已移除
`jax.lib.xla_bridge`（JAX 0.8.0 起移除），ColabDesign `clear_mem()` 崩在官方 PDL1 示例。
完整根因/证据见 [reports/stage2_environment_failure_001.md](reports/stage2_environment_failure_001.md)。
notebook 现自建隔离 Python 3.10 + JAX 0.6.0(CUDA 12.6) 环境，等价官方 install_bindcraft.sh。

本机制备（本机可复现）：

```bash
.venv/bin/python scripts/make_domain3_pdb.py      # 生成裁剪 PDB + manifest（幂等）
python3 -m unittest discover -s tests             # 62/62 期望
```

云端执行（用户 A7，首次建环境约 10–25 分钟，之后总时长按实测，免费 T4）：

1. **先 Disconnect and delete runtime**（清掉尝试 001 的 JAX 0.11.1 残留）→ Runtime → Change runtime type → **T4 GPU** → Upload 新版 `cloud/stage2_bindcraft_smoke.ipynb`。
2. 顺序执行 Cell 1–13，**不要改任何数字**：
   - Cell 2 在 `/content/bindcraft_env` 自建 Miniforge **Python 3.10** 环境：conda-forge/nvidia `jax=0.6.0 jaxlib=0.6.0=*cuda*`（`CONDA_OVERRIDE_CUDA=12.6`）、`numpy<2`、`flax<0.10`、ColabDesign pin e31a56f `--no-deps`、PyRosetta cp310 wheel；Colab 系统 Python 3.13/JAX 0.11 不参与任何计算；
   - Cell 5 上传**三个**文件：`data/processed/6ARU_chainA_domain3_310-481.pdb`、`scripts/analyze_bindcraft_run.py`、`scripts/bindcraft_preflight.py`；
   - **Cell 6 pre-flight 硬门**（先于 5.3 GB 权重下载）：必须打印 `PRE-FLIGHT PASSED on Tesla T4 | jax 0.6.0 | cuda backend 12.6...`；失败即停，回传 `preflight.json`，不要继续；
   - Cell 9 跑**官方最小示例 PDL1（65 aa / hotspot 56 / cap 1）**——失败=环境故障，**停**，不要碰 EGFR；Cell 10 断言 relaxed PDB 存在才放行；
   - Cell 11 才跑 EGFR micro（B 保守 hotspot 6 残基 / 80 aa / cap 3）。
3. OOM 纪律：Factory reset 后**最多再试 1 次**（累计 2 次）即停；把 preflight.json、env_metadata 与 log 交回，我写 `reports/compute_escalation.md`——该文件在观察到 OOM 前不存在。
4. 产物落在 Drive `BindCraft/stage2_smoke/`：`preflight.json`、`env_metadata.json`（含 `pip_freeze.txt`/`conda_list.txt`）、`stage2_smoke_report.json`、`*_vram.csv`、两个 `.log`、`Trajectory/` PDB。
5. 判读纪律：completed ≠ success；binder 是否接触 B、是否迁移、是否抱裁剪边缘、有无严重 clash 以 analyzer JSON + Cell 13 三维目检为准；接受/拒绝看官方 filters 的 `Accepted/` 与 CSV。
6. smoke 复核前：不跑 broad（12 残基）配置、不加轨迹数、不改表位、不回退 Colab runtime 版本、不 monkey-patch 上游、不付费；依赖升级先记录实际版本再决定。

本地分析回传产物（无 GPU 也能跑，纯标准库）：

```bash
python3 scripts/analyze_bindcraft_run.py \
  --run-dir data/inbox/egfr_d3_B_conservative \
  --out results/stage2/egfr_d3_B_conservative_geometry.json
```
