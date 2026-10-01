# Stage 2 环境故障 001 — Colab PDL1 官方示例失败（JAX API 移除）

- 日期：2026-10-01（用户实测回传）
- 分类：**ENVIRONMENT_FAILURE**（非 EGFR 靶点/配置故障）
- 阶段：Stage 2，第一步最小官方示例 PDL1，未产生任何 relaxed 轨迹
- EGFR 科学配置：本次故障中**未做任何改动**（表位 B / hotspot `390,393,399,421,424,431` / 80 aa / 默认 filters / 仅改 max_trajectories 的 4stage multimer / 310–481 裁剪全部保持不变）

## 1. 实测环境（用户 Colab runtime，真实值）

| 项目 | 值 |
|---|---|
| GPU | Tesla T4，15360 MiB VRAM |
| Python（Colab 内核） | 3.13.15 |
| CUDA / nvcc | 12.8 |
| BindCraft commit | `7713aa0d0d351e4117a8befeb8541f3a8ebd3368` |
| ColabDesign | 1.1.3（git main，notebook 未 pin） |
| JAX | 0.11.1（Colab 预装，notebook 未 pin） |
| jaxlib | 0.11.1 |
| PyRosetta | 安装成功 |
| AlphaFold 权重 | 安装成功（alphafold_params_2022-12-06） |

## 2. 故障点与原始 traceback

PDL1 在产出 relaxed 轨迹之前崩溃。Cell 8（我们 notebook 的 PDL1 relaxed 断言）只是下游后果，**不是根因**。

```
AttributeError: module 'jax.lib' has no attribute 'xla_bridge'

Call path:
BindCraft functions/colabdesign_utils.py
→ binder_hallucination
→ clear_mem()
→ colabdesign/shared/utils.py
→ jax.lib.xla_bridge.get_backend()
```

## 3. 根因（2026-10-01 逐项核实，官方来源）

1. **ColabDesign 当前 main（`e31a56f`）`colabdesign/shared/utils.py::clear_mem()` 仍直接调用**
   `jax.lib.xla_bridge.get_backend()`（原文核实，未做兼容分支）。
2. **JAX 官方 changelog：`jax.lib.xla_bridge` 等半公开模块在 JAX 0.8.0（2025-10-15）被移除**；0.6.0 中仍存在（仅弃用）。因此 JAX 0.11.1 上必然 `AttributeError`。
   来源：https://docs.jax.dev/en/latest/changelog.html （0.8.0 breaking changes：
   “The deprecated functions in `jax.dlpack`, `jax.errors`, `jax.lib.xla_bridge`,
   `jax.lib.xla_client`, and `jax.lib.xla_extension` were removed.”）
3. **BindCraft 官方安装脚本（pin 7713aa0 仓库内 `install_bindcraft.sh`）明确约束**：
   - conda 环境 `python=3.10`；
   - `'jax>=0.4,<=0.6.0' 'jaxlib>=0.4,<=0.6.0=*cuda*'`，通道 conda-forge + nvidia；
   - `'numpy<2.0.0'`、`'flax<0.10.0'`；
   - ColabDesign 用 `pip3 install git+...ColabDesign.git --no-deps`。
   而仓库内官方 Colab notebook 的单元格只做未 pin 的 `pip install git+ColabDesign`，
   依赖 Colab 预装 JAX——Colab 滚动镜像升级到 0.11.1 后即破坏。
4. **上游已知同错误 issue**：martinpacesa/BindCraft#376（2026-09-01 报，2026-09-02 关），
   现象与版本（A100、JAX 0.11.1、同一 traceback）与本次完全一致；关闭方式是用户自行把
   Colab runtime 版本切回 **2026.07**。这不是维护者发布的可脚本化修复，runtime 版本回退
   不受 notebook 控制、不可复现，因此我们不采用。
   https://github.com/martinpacesa/BindCraft/issues/376
5. **Python 3.13 无法满足官方完整约束**：jaxlib 0.6.0 虽有 cp313 wheel（requires_python>=3.10），
   但官方栈同时要求 `numpy<2.0.0`；PyPI 上 numpy 1.26.4 **没有 cp313 wheel**（numpy 自 2.1 起才支持 3.13），
   即官方 pin 集合在 3.13 上不可解。这与上游脚本创建 Python 3.10 环境一致。
6. conda-forge `jaxlib 0.6.0` linux-64 有 CUDA 构建 `cuda126py310..._200`，依赖
   `cuda-version >=12.6,<13`、cudnn 9.10；conda-forge `jax 0.6.0`（noarch）精确要求
   `jaxlib 0.6.0`。Colab 驱动 580（nvidia-smi 报 CUDA 13.0）向后兼容 12.6 用户态运行时，
   `CONDA_OVERRIDE_CUDA=12.6` 可解。PyRosetta 官方 quarterly 索引提供 cp310 linux x86_64 wheel
   （2026-07-24 仍在更新）。

**结论**：故障 = Colab 滚动镜像（Py 3.13 + JAX 0.11.1）超出 BindCraft 7713aa0 官方支持区间
（py3.10 + jax/jaxlib ≤0.6.0），且 ColabDesign 尚未适配已移除的 `xla_bridge`。
不是 EGFR 靶点、hotspot、长度或裁剪问题；PDL1 在触及任何靶点逻辑前就崩在显存清理函数。

## 4. 处置（不打上游源码补丁）

按用户要求“优先与官方支持区间一致的可复现环境”，notbook 现自建**隔离 Miniforge 环境**，
等价于在 Colab 内执行官方 `install_bindcraft.sh`：

- Miniforge3（装在 `/content/miniforge3`，不修改 Colab 系统 Python 3.13）
- env 前缀 `/content/bindcraft_env`，**Python 3.10**
- `jax=0.6.0`、`jaxlib=0.6.0=*cuda*`（conda-forge/nvidia，`CONDA_OVERRIDE_CUDA=12.6`）
- `numpy<2.0.0`、`flax<0.10.0`，其余包与官方脚本逐项一致
- ColabDesign pin `e31a56fe1d9b4de25c8697f3a28b75892941cc72`，env 内 pip `--no-deps`
- PyRosetta env 内 pip（官方 find-links，cp310 wheel）
- 所有 BindCraft 子进程以 `/content/bindcraft_env/bin/python` 运行；Colab 内核不 import jax/colabdesign
- 新增 **pre-flight 硬门**（[scripts/bindcraft_preflight.py](../scripts/bindcraft_preflight.py)），
  在下载 5.3 GB 权重与任何轨迹之前，于隔离 env 内验证：
  Python 3.10、jax/jaxlib ∈ [0.4,0.6.0]（明确拒绝 0.11.x 与 ≥0.8）、numpy<2、flax<0.10、
  `colabdesign.clear_mem()` 成功、直接调用 `jax.lib.xla_bridge.get_backend()` 成功、
  GPU 可见、2048³ matmul 在 GPU 上数值正确、PyRosetta 可导入；任一失败即非零退出并写 `preflight.json`。
- 版本策略函数有本地回归测试（0.6.0 接受；0.6.1/0.7/0.8/0.10/0.11 拒绝；拒绝信息指明 0.8.0 移除）。

## 5. 复测要求（用户 A7 更新版）

1. Colab 先 **Disconnect and delete runtime**（清掉旧 0.11.1 残留），重新选 T4 GPU。
2. 上传更新后的 [cloud/stage2_bindcraft_smoke.ipynb](../cloud/stage2_bindcraft_smoke.ipynb)，
   Cell 5 上传**三个**文件：裁剪 PDB、`analyze_bindcraft_run.py`、`bindcraft_preflight.py`。
3. 顺序执行。预期：Cell 2 建环境约 10–25 分钟（conda 包 + PyRosetta wheel 下载）；
   Cell 6 打印 `PRE-FLIGHT PASSED on Tesla T4 | jax 0.6.0 | cuda backend 12.6...`；
   之后才下载权重并跑 PDL1。
4. 若 pre-flight 失败：停止，回传 `preflight.json`（不要碰 EGFR 配置）。
5. PDL1 产出 relaxed PDB 后才允许 EGFR micro；判据与之前完全相同。

## 6. 未变更项（再次确认）

表位包络 B（390–403 + 421–431）、fallback C、H433 推迟、hotspot 6 残基、binder 80 aa、
PDL1 65 aa/hotspot 56、默认 filters、4stage multimer 默认（仅 max_trajectories=1/3）、
裁剪 PDB 310–481、无 hardtarget、无目标突变、无付费计算——全部不变。

## 7. 来源清单（2026-10-01 抓取）

- BindCraft 安装脚本：https://github.com/martinpacesa/BindCraft/blob/7713aa0d0d351e4117a8befeb8541f3a8ebd3368/install_bindcraft.sh
- ColabDesign clear_mem：https://github.com/sokrypton/ColabDesign/blob/e31a56fe1d9b4de25c8697f3a28b75892941cc72/colabdesign/shared/utils.py
- JAX changelog：https://docs.jax.dev/en/latest/changelog.html
- BindCraft issue #376：https://github.com/martinpacesa/BindCraft/issues/376
- conda-forge jaxlib 0.6.0 构建：https://anaconda.org/conda-forge/jaxlib/files （cuda126 py310）
- PyPI jaxlib 0.6.0 / numpy 1.26.4 文件清单（cp313 有无）：https://pypi.org/project/jaxlib/0.6.0/ ， https://pypi.org/project/numpy/1.26.4/
- PyRosetta wheel 索引：https://west.rosettacommons.org/pyrosetta/quarterly/release.cxx11thread.serialization/
