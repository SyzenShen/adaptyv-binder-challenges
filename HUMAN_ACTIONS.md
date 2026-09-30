# HUMAN_ACTIONS — 需要本人完成的最短动作清单

更新：2026-09-30。每条都给“为什么、怎么做、完成标志”。未完成前我不会假设其已完成。

## A1 — GitHub 认证（解除 PUSH_BLOCKED，约 2 分钟）

**为什么**：`gh` 保存的 token 已失效（账户 SyzenShen），SSH key 也未在 GitHub 注册；我无法替你完成浏览器/设备码授权。

**最短步骤**（在本机终端，当前目录即可）：

```bash
gh auth login --hostname github.com --git-protocol https --web
```

按提示选择 HTTPS、用浏览器打开设备码页面、登录你的**个人账户**（确认是 SyzenShen，不是任何组织账户）。若提示上传 SSH key 可选 No（HTTPS + gh 凭据即可）。

**完成后告诉我**，我会执行（你可以先看再让我做）：

```bash
gh auth status                      # 确认认证账户
gh repo create egfr-binder-challenge --private --source=. --remote=origin
git push -u origin main             # 分支名以本地实际为准
gh api repos/SyzenShen/egfr-binder-challenge/commits/main   # 远端核实
```

仓库名：默认 `egfr-binder-challenge`（与本地目录同名）。主控指令里的默认名是 `egfr-ph-switch-2026`，如果你想用那个名字，认证时告诉我即可。两种情况下我都会先查远端不存在同名仓库再创建，绝不覆盖。

**完成标志**：远端能查到首个 commit SHA；STATE.md 移除 PUSH_BLOCKED。

## A2 — 获取 mouse EGFR 官方构建体信息（约 5 分钟）

**为什么**：比赛页 Mouse EGFR 标签 2026-09-30 实测为空面板（疑似站点渲染问题），mouse 的 UniProt isoform、残基边界、序列和结构参考均未公开可读；规则要求不能照搬 human 的切片。

**最短步骤**（二选一）：

1. 用浏览器登录 Proteinbase 后打开 https://proteinbase.com/competitions/anthropic-adaptyv-2026/challenges/egfr ，点 “Mouse EGFR” 标签，把该标签下的 **UniProt reference、Target residues (x–y / N aa)、Recommended epitope、Structure reference、完整序列** 复制给我（截图也行）；或
2. 加入官方 Slack（页面上的邀请链接：https://join.slack.com/t/proteinbase/shared_invite/zt-3evw8fs9z-tU9ItWVvw4ySctUuPvIhLQ ），在 challenge 频道问一句：*“Where can I find the mouse EGFR construct details (UniProt isoform, residue boundaries, reference structure) for Challenge 1? The Mouse EGFR tab on the challenge page renders empty.”*

**完成标志**：mouse 字段从 null 更新为官方来源（URL + 访问日期）。在那之前阶段 1 只推进 human 部分。

## A3 — 确认参赛资格并注册 Proteinbase（约 5 分钟）

**为什么**：Official Terms §3.1 排除 Belarus、China、Cuba、Iran、Myanmar、North Korea、Russia、Sudan、Syria、Crimea、DNR/LNR 的**法定居民/定居者**；提交还需要 Proteinbase 账户。我无法替你判断法律居留状态。

**最短步骤**：

1. 你自行确认不属于上述被排除情形（你当前时区为 Europe/Berlin，但是否为德国/其他允许地区法定居民由你判断，必要时问老师/机构）。
2. 打开 https://proteinbase.com/competitions/anthropic-adaptyv-2026 完成 joint registration form（Track 3，self-supported）。如希望匿名，可用匿名账户注册（FAQ 11 允许，之后可取消匿名）。
3. 回复我“资格确认 + 已注册 Track 3”即可，不需要把账户凭据给我。

**完成标志**：口头确认 + 注册完成；提交门户 https://proteinbase.com/competitions/anthropic-adaptyv-2026/submit 在阶段 7 才需要实际操作。

## A4 — 磁盘清理（非阻塞，建议本周做）

本机可用空间仅 27.5GB。云端方案不受影响，但建议清理出 ≥50GB 余量（系统设置 → 储存空间；清空下载/废纸篓；`brew cleanup`）。不建议为项目购买/外接存储，模型产物本来就不落地本地。

## A5 — Colab 登录（阶段 2 时再做，无需现在操作）

阶段 2 我会准备好 notebook 与清单，届时你登录 colab.research.google.com、挂载专用 Drive 结果目录即可；我不会要求保活脚本、代理或多账户（官方明文禁止）。
