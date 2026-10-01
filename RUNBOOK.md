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

本机制备（本机可复现）：

```bash
.venv/bin/python scripts/make_domain3_pdb.py      # 生成裁剪 PDB + manifest（幂等）
python3 -m unittest discover -s tests             # 48/48 期望
```

云端执行（用户 A7，约 30–90 分钟，免费 T4 即可起步）：

1. Colab → File → Upload notebook：`cloud/stage2_bindcraft_smoke.ipynb`；Runtime → Change runtime type → **T4 GPU**。
2. 顺序执行 Cell 1–11，**不要改任何数字**：
   - Cell 2 安装 BindCraft **pin 7713aa0** + ColabDesign（解析版本自动记录）+ PyRosetta + AF2 权重（5.3 GB）；
   - Cell 5 上传两个文件：`data/processed/6ARU_chainA_domain3_310-481.pdb`、`scripts/analyze_bindcraft_run.py`；
   - Cell 7 先跑**官方最小示例 PDL1（65 aa / hotspot 56 / cap 1）**——它失败=环境故障，**停**，不要碰 EGFR；
   - Cell 9 才跑 EGFR micro（B 保守 hotspot 6 残基 / 80 aa / cap 3）。
3. OOM 纪律：Factory reset 后**最多再试 1 次**（累计 2 次）即停；把 Cell 1/3 元数据与 log 交回，我写 `reports/compute_escalation.md`——该文件在观察到 OOM 前不存在。
4. 产物落在 Drive `BindCraft/stage2_smoke/`：`env_metadata.json`、`stage2_smoke_report.json`、`*_vram.csv`、两个 `.log`、`Trajectory/` PDB。回传这些文件（下载或共享 Drive 链接均可）。
5. 判读纪律：completed ≠ success；binder 是否接触 B、是否迁移、是否抱裁剪边缘、有无严重 clash 以 analyzer JSON + Cell 11 三维目检为准；接受/拒绝看官方 filters 的 `Accepted/` 与 CSV。
6. smoke 复核前：不跑 broad（12 残基）配置、不加轨迹数、不改表位、不付费；ColabDesign 若升级导致接口变化，先在报告中记录实际 commit 再决定是否适配。

本地分析回传产物（无 GPU 也能跑，纯标准库）：

```bash
python3 scripts/analyze_bindcraft_run.py \
  --run-dir data/inbox/egfr_d3_B_conservative \
  --out results/stage2/egfr_d3_B_conservative_geometry.json
```
