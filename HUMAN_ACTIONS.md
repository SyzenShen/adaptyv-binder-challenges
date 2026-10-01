# HUMAN_ACTIONS — 需要本人完成的最短动作清单

更新：2026-09-30。每条都给“为什么、怎么做、完成标志”。未完成前我不会假设其已完成。

## A1 — GitHub 认证 ~~（解除 PUSH_BLOCKED）~~ ✅ 已由用户提供仓库解除（2026-09-30）

用户提供 `https://github.com/SyzenShen/egfr-binder-challenge.git`（私有），push 成功并经 `git ls-remote` 核实（9ff9d43）。剩余可选动作：本机 `gh` token 仍失效，仅当后续需要 `gh api`（如 PR/issue 操作）时再运行 `gh auth login --hostname github.com --git-protocol https --web`；对日常 commit/push 无影响。

## A2 — 获取 mouse EGFR 官方构建体信息（约 5 分钟）

**为什么**：比赛页 Mouse EGFR 标签 2026-09-30 实测为空面板（疑似站点渲染问题），mouse 的 UniProt isoform、残基边界、序列和结构参考均未公开可读；规则要求不能照搬 human 的切片。

**最短步骤**（二选一）：

1. 用浏览器登录 Proteinbase 后打开 https://proteinbase.com/competitions/anthropic-adaptyv-2026/challenges/egfr ，点 “Mouse EGFR” 标签，把该标签下的 **UniProt reference、Target residues (x–y / N aa)、Recommended epitope、Structure reference、完整序列** 复制给我（截图也行）；或
2. 加入官方 Slack（页面上的邀请链接：https://join.slack.com/t/proteinbase/shared_invite/zt-3evw8fs9z-tU9ItWVvw4ySctUuPvIhLQ ），在 challenge 频道问一句：*“Where can I find the mouse EGFR construct details (UniProt isoform, residue boundaries, reference structure) for Challenge 1? The Mouse EGFR tab on the challenge page renders empty.”*

**完成标志**：mouse 字段从 null 更新为官方来源（URL + 访问日期）。在那之前阶段 1 只推进 human 部分。

> 2026-10-01 更新：你已通过指令文件转达 6 条 Slack 信息（含 mouse 构建体 25–647），已按 `USER_PROVIDED_OFFICIAL_COMPETITION_SLACK` 入档并用于阶段 1.5 分析；但**页面当天仍为空、无截图凭据**，A2 未关闭——凭据动作转入 **A6**。

## A6 — 提供 Slack 原文截图/导出（约 5 分钟，阶段 1.5 新阻塞项）

**为什么**：2026-10-01 你转达的 6 条官方 Slack 信息（mouse 25–647、buffer/pH、EDTA、标签等，逐条转录于 [assay_metadata.md](reports/assay_metadata.md)）目前只有转述，没有可入档的一手凭据；项目规则要求区分真实来源与推测。

**最短步骤**：在 Proteinbase Slack 对应频道找到这 6 条原消息，截图（含频道名、日期、发送者）或导出文本，放入 `reports/slack_provenance/`（文件名按 assay_metadata.md 的编号，如 `01_mouse_construct.png`）。拿不到某条就告诉我，我把该条降级回"用户转述/未证实"。

**完成标志**：6 条信息在 assay_metadata.md 中的 provenance 从 PENDING 变为 SCREENSHOT_FILE 并指到具体文件。

## A3 — 确认参赛资格并注册 Proteinbase（约 5 分钟）

**为什么**：Official Terms §3.1 排除 Belarus、China、Cuba、Iran、Myanmar、North Korea、Russia、Sudan、Syria、Crimea、DNR/LNR 的**法定居民/定居者**；提交还需要 Proteinbase 账户。我无法替你判断法律居留状态。

**最短步骤**：

1. 你自行确认不属于上述被排除情形（你当前时区为 Europe/Berlin，但是否为德国/其他允许地区法定居民由你判断，必要时问老师/机构）。
2. 打开 https://proteinbase.com/competitions/anthropic-adaptyv-2026 完成 joint registration form（Track 3，self-supported）。如希望匿名，可用匿名账户注册（FAQ 11 允许，之后可取消匿名）。
3. 回复我“资格确认 + 已注册 Track 3”即可，不需要把账户凭据给我。

**完成标志**：口头确认 + 注册完成；提交门户 https://proteinbase.com/competitions/anthropic-adaptyv-2026/submit 在阶段 7 才需要实际操作。

## A4 — 磁盘清理（非阻塞，建议本周做）

本机可用空间仅 27.5GB。云端方案不受影响，但建议清理出 ≥50GB 余量（系统设置 → 储存空间；清空下载/废纸篓；`brew cleanup`）。不建议为项目购买/外接存储，模型产物本来就不落地本地。

## A7 — 在 Colab 执行 Stage 2 smoke（阶段 2 当前唯一阻塞，约 30–90 分钟）

**为什么**：本机是 Intel Mac、无 NVIDIA GPU，BindCraft 必须在 CUDA GPU 上跑；notebook/配置/分析器我已全部备好并测试（48/48），但**真实 GPU 数据只能由你登录 Colab 产生**。没有实测前不会进入阶段 3，也不会替你推测 GPU 型号、VRAM 或耗时。

**最短步骤**：
1. 打开 https://colab.research.google.com → Upload → 选仓库里的 [cloud/stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb)；Runtime → Change runtime type → **T4 GPU（免费档）**。
2. 从上到下逐格执行（细节见 [RUNBOOK.md](RUNBOOK.md) §7）。Cell 5 会弹窗，选本仓库两个文件：`data/processed/6ARU_chainA_domain3_310-481.pdb` 与 `scripts/analyze_bindcraft_run.py`。
3. **顺序很重要**：先跑官方 PDL1 示例（环境验证），成功后才自动继续 EGFR；若 PDL1 失败，停止并把 log 发我，不要自行改 EGFR 配置。
4. OOM：Factory reset 后最多重试一次；第二次仍 OOM 就停，不要反复撞。
5. 完成后把 Drive 文件夹 `BindCraft/stage2_smoke/` 分享给我（或至少回传 `env_metadata.json`、`stage2_smoke_report.json`、两个 `.log`、一个 relaxed PDB）。

**完成标志**：我拿到上述真实产物并写出 Stage 2 smoke 报告（环境 vs 靶点故障判定 + B 接触/迁移/边缘结论 + 仅按实测吞吐的批次建议）。在此之前 EGFR 生产生成、broad hotspot、付费计算一律不启动。
