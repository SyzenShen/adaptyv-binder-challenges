# 环境审计报告（阶段 0）

- 审计时间：2026-09-30 18:00–18:10 CEST（UTC+2）
- 审计方式：本机终端实测命令（非转述、非假设）。命令清单见 RUNBOOK.md §2。

## 1. 硬件 / 系统（实测）

| 项目 | 实测值 | 备注 |
|---|---|---|
| 机型标识 | Darwin `bio-mac`，x86_64 | 确认 Intel，非 Apple Silicon |
| macOS | 15.6 (Build 24G84)，Darwin 24.6.0 | |
| CPU | Intel Core i7-9750H @ 2.60GHz，6 物理核 / 12 逻辑核 | |
| 物理内存 | 34,359,738,368 B = **32 GB** | 系统内存，**不是显存** |
| GPU | Intel UHD Graphics 630（1536MB 动态）+ AMD Radeon Pro 5300M（4GB，Metal 3） | **均非 NVIDIA/CUDA**，不用于 BindCraft/Boltz 推理 |
| 磁盘可用 | APFS 容器可用 **27.5 GB**（Data 卷 334Gi/374Gi 已用，93%） | 偏紧；权重/数据库禁止落地，见 D-002/A4 |

结论：与用户给定条件一致（Intel MBP / 32GB / 4GB 显存）。本机定位为 CPU 分析 + Git 写入端，模型计算必须在云端 NVIDIA GPU。

## 2. 软件（实测）

| 工具 | 版本 / 路径 | 状态 |
|---|---|---|
| Python | 3.10.11，`/Library/Frameworks/Python.framework/...`（python.org 安装） | ✅ 可用；阶段 0 测试已在其上通过 |
| pip | 23.0.1 | 可用，建议后续在项目 `.venv` 内使用 |
| conda | 无 | 不需要；项目用 venv 隔离 |
| Homebrew | 7.0.6（`/usr/local/Homebrew`） | ✅ |
| git | 2.50.1 (Apple Git-155)，`/usr/bin/git` | ✅ |
| gh（GitHub CLI） | 2.87.3 | ⚠️ 已安装但**认证失效**，见 §4 |
| git 全局身份 | name=`lvoryLexicon` / email=`shenyizhuozhanghaibo@gmail.com` | 本地 commit 使用；与 gh 账户 SyzenShen 的对应关系待本人确认 |

未做任何全局 Python/conda 修改；分析依赖仅计划安装到项目内 `.venv`（requirements-min.txt，阶段 1 前按需创建）。

## 3. 网络（实测，2026-09-30）

| 端点 | HTTP | 耗时 |
|---|---|---|
| https://github.com | 200 | 2.5s |
| https://proteinbase.com（比赛页） | 200 | 1.7s |
| https://www.google.com | 200 | 1.2s |
| https://rest.uniprot.org/uniprotkb/P00533.fasta | 200 | 2.5s |
| https://rest.uniprot.org/uniprotkb/Q01279.fasta | 200 | —（仅端点连通，内容阶段 1 核验） |
| https://files.rcsb.org/download/6ARU.cif（Range 0-200） | 200 | 1.5s |
| 提交门户 /submit | 200 | — |

注：阶段初曾用错误路径 `6ARU.cif.header` 得到 404；正确文件路径 `6ARU.cif` 实测 200。

## 4. GitHub 权限（实测）— PUSH_BLOCKED

- `gh auth status`：账户 **SyzenShen**，keyring 中 token **invalid**（`Failed to log in ... The token in keyring is invalid`）。
- `ssh -T git@github.com`：`Permission denied (publickey)`——本机 `~/.ssh` 有 id_ed25519 / id_rsa 密钥，但未在 GitHub 侧授权（或未加载）。
- 当前目录在审计时**不是** git 仓库（阶段 0 已执行 `git init`，见 STATE.md）。

→ 最短解除动作：HUMAN_ACTIONS.md **A1**（`gh auth login ... --web`，约 2 分钟）。认证完成前远端私有仓库无法创建/推送，阶段 0 保持 PUSH_BLOCKED。

## 5. 最小依赖方案

- **本地轻量分析环境**（项目 `.venv`，不进 git）：biopython（序列/mmCIF 处理）、pandas（表格）、PyYAML（配置）、requests（下载校验）、pytest（测试）。系统 Python 标准库即可跑阶段 0 全部测试。
- **云端 GPU 环境**：阶段 2 按 BindCraft 官方 README 在 Colab Linux/NVIDIA runtime 内隔离安装，锁定当时 commit（当前上游 HEAD 见 sources_register.md，不等于届时锁定版本）；本地不安装 JAX/CUDA 栈。
- **复核环境**：Boltz 独立环境（阶段 4），与 BindCraft 分开。
- PROPKA（阶段 5）：可 CPU 运行，届时单独轻量环境，LGPL-2.1 已记录。

## 6. 本机无法完成 / 明确不做

- 不运行任何需要 CUDA 的模型；AMD 4GB 显存不尝试（OpenCL/DirectML 等路线不在官方支持内）。
- 不装 Linux 虚拟机“获得 GPU”，不重装系统，不修改全局 Python。
- 不把模型权重下载到仅剩 27.5GB 的本地盘。
