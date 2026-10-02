# HUMAN_ACTIONS — 需要本人完成的最短动作清单

更新：2026-10-01。每条都给“为什么、怎么做、完成标志”。未完成前我不会假设其已完成。

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

## A7 — 在 Colab 重跑 Stage 2 权重下载（阶段 2 当前唯一阻塞；runtime 存活时约 5–15 分钟）

**为什么**：本机无 NVIDIA GPU，BindCraft 必须在 CUDA GPU 上跑。四次尝试的定位：①Colab 预装环境（Py3.13 + JAX 0.11.1）跑不了官方流程 → 已由隔离 py3.10/jax 0.6.0 环境修复；②preflight 脚本 set 索引 bug → 已修复；③Cell 7 权重下载用不可观测的 `Popen(aria2c…)` + 盲等 30 分钟，子进程秒退且错误被丢弃 → attempt-004 已改为内联可观测 wget harness。**四次都不是科学配置问题，环境本身已验证健康。**

**最短步骤（当前 runtime 还在，Python/JAX 环境不重装）**：
1. **整格替换 Cell 7**：把仓库新版 [cloud/stage2_bindcraft_smoke.ipynb](cloud/stage2_bindcraft_smoke.ipynb) 里 **Cell 7** 的代码整段复制覆盖当前 notebook 的 Cell 7（旧格是盲等下载，必须换掉）。新格是自包含的：已存在完整 15 个官方 .npz 则跳过；否则保证 wget、`wget -c` 续传、观测子进程（PID/按大小进度/returncode/`download.log`）、非零即停打印日志尾部、解包前 `tar -tf` 校验完整性、校验**恰好 15 个**官方 .npz（5 base + 5 pTM + 5 Multimer-v3）才写 `done.txt`，校验通过后删归档。
2. **运行 Cell 7**：会周期性打印进度；看到 `OK: 15 required AlphaFold .npz files validated` 即成功。若失败，错误会**立即**打印真实日志尾部——停止，把输出和 `/content/bindcraft/params/download.log` 发我，不要继续、不要自行改包。
3. 从 Cell 8 继续：PDL1 官方示例 → 成功（Cell 10 过）后才自动跑 EGFR micro。
4. OOM：Factory reset 后最多重试一次；第二次仍 OOM 就停。
5. 完成后把 Drive 文件夹 `BindCraft/stage2_smoke/` 分享给我（或至少回传 `preflight.json`、`env_metadata.json`、`stage2_smoke_report.json`、两个 `.log`、一个 relaxed PDB）。

**若 runtime 已被释放**：按 [RUNBOOK.md](RUNBOOK.md) §7 完整流程重跑（Disconnect and delete → T4 → 上传新版 notebook → 逐格执行，Cell 2 重建环境 10–25 分钟，Cell 5 传 3 个文件）。

**完成标志**：我拿到上述真实产物并写出 Stage 2 smoke 报告（环境 vs 靶点故障判定 + B 接触/迁移/边缘结论 + 仅按实测吞吐的批次建议）。在此之前 EGFR 生产生成、broad hotspot、付费计算一律不启动。
