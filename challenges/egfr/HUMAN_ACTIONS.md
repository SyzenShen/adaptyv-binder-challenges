# HUMAN_ACTIONS — 需要本人完成的最短动作清单

更新：2026-10-04（A7 已随收口重构 H 更新：notebook 每 cell 有 markdown 说明，README 双语攻略为新手入口）。每条都给“为什么、怎么做、完成标志”。未完成前我不会假设其已完成。

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

## A7 — 在 Colab 跑/恢复 Stage 2 smoke（阶段 2 当前唯一算力阻塞；首次约 40–60 分钟，恢复重跑通常很短）

**为什么**：本机无 NVIDIA GPU，BindCraft 必须在 CUDA GPU 上跑。此前四次尝试的环境与
harness 问题（JAX 0.11.1、set 索引、不可观测下载、14/15 文件计数）已全部修复并模块化；
2026-10-02 可靠性合并后 notebook 只剩 A–H 八个薄 cell，昂贵工作全部 checkpoint 到 Drive，
reset/配额中断后可安全续跑。已观测到一次 PDL1 成功 run 持久化在 Drive
（`PDL1_smoke_l65_s909721.pdb`，rc 0、零最终接受），合并流程会把它识别为
LEGACY_CHECKPOINT 并跳过约 30 分钟的重跑。

**最短步骤（一次性准备，约 3 分钟）**：
1. Colab 左栏钥匙图标 → Notebook Secrets → 新建 `GITHUB_TOKEN`（对私有仓库
   `SyzenShen/egfr-binder-challenge` 有读权限的 PAT）。token 只经 git header 使用，
   notebook 不会打印它；不想配 token 也可在 Cell C 提示时手工上传仓库快照 tarball。
2. Runtime → Change runtime type → **T4 GPU** → 上传新版
   [cloud/stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb)。

**运行（只需记住"从上到下，一个恢复 cell"；新手先读 [README.md](README.md) 的
10-minute orientation 与 Quick start）**：
3. 顺序运行 **Cell A→H**，不要改任何数字。A=GPU 门（无 GPU/配额拒绝会打印
   `GPU_UNAVAILABLE`/`COMPUTE_QUOTA_BLOCKED` 并停止，不会跑 CPU）；B=Drive；
   C=按 notebook 内 `PROJECT_PIN` 精确 commit 取项目工件（以 Cell C 打印的
   PROJECT PIN 为准）；D=BindCraft `7713aa0` + 隔离
   py3.10/jax0.6.0 环境（首次 10–25 分钟，幂等）+ 幂等应用 D-019 补丁；
   E=preflight；F=权重（本地→Drive 缓存→可观测续传下载，精确 15 npz）；
   **G=唯一昂贵 cell**，PDL1 完成即跳过、失败即阻断 EGFR；H=报告+三维目检
   （表位高亮已自动经残基映射换算到输出 PDB 的 local 编号）。
4. 若中途断连/reset/配额被拒：重新连上 GPU 后**从 A 再跑到 G 即可**——权重走 Drive
   缓存，PDL1 检查点自动 skip，不会静默重跑或覆盖完成态。详见
   [RUNBOOK.md](RUNBOOK.md) §7.3/§7.4。
5. OOM：factory reset 后最多重试一次；第二次仍 OOM 就停，把日志发我。

**完成标志**：G 打印 `STAGE 2 SMOKE COMPLETE`，Drive
`BindCraft/stage2_smoke/persistent/` 下有 `reports/stage2_smoke_report.{json,md}`、
`metadata/`、`logs/`；把这些（或整个文件夹链接）发我。我据此写 Stage 2 smoke 判读
（环境 vs 靶点故障、B 接触/迁移/边缘、仅按实测吞吐的批次建议）。在此之前 EGFR 生产
生成、broad hotspot、付费计算一律不启动。

> 2026-10-08: the GitHub repository was renamed from `egfr-binder-challenge` to `adaptyv-binder-challenges`. Entries above keep the original name as written at the time.
