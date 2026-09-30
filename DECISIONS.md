# DECISIONS — 关键决策记录（只记录已定，不记录设想）

| ID | 日期 (UTC) | 决策 | 依据 | 状态 |
|---|---|---|---|---|
| D-001 | 2026-09-30 | 以用户已创建的 `egfr-binder-challenge/` 作为项目根目录（MASTER_PROMPT 默认名 `egfr-ph-switch-2026` 仅作建议；用户已把主控指令放入本目录）。远端仓库名待 A1 认证时确认，默认与本地目录同名，不覆盖任何同名仓库 | 用户在本目录放置并指令执行 提示词.md；§4“默认”措辞 | 已定，远端名 A1 再确认 |
| D-002 | 2026-09-30 | 本地 Intel Mac 只承担 CPU 分析、Git 写入与轻量查看；GPU 计算走 Colab（免费档先行）；不装 CUDA/虚拟机，不改全局 Python | 实测无 CUDA、磁盘仅 27.5GB；MASTER_PROMPT §3C/§5 | 已定 |
| D-003 | 2026-09-30 | paid_budget=0；任何 Colab 付费方案、付费 GPU/API 在书面批准前不开通 | MASTER_PROMPT §3C | 已定 |
| D-004 | 2026-09-30 | 生产生成主线只搭 BindCraft 官方流程一条；RFdiffusion/AF3/Chai 不并行安装；Boltz 仅作阶段 4 的独立复核候选 | MASTER_PROMPT §7/§9 | 已定（阶段 2 执行前再按官方文档复核版本） |
| D-005 | 2026-09-30 | 提交长度目标锁定官方 minibinder 分类 40–100 aa；CSV 三列最低 schema 已写入 configs/competition.json | EGFR 页 Submission requirements + FAQ 1/2/5（2026-09-30 核实） | 已定 |
| D-006 | 2026-09-30 | mouse 实验构建体在官方信息获取前保持 null，不照搬 human 25–645、不假定 Q01279 isoform | EGFR 页 mouse 标签实测为空；MASTER_PROMPT §2/§6 | 阻塞项，待 A2 |
| D-007 | 2026-09-30 | 阶段 0 测试仅用标准库，保证无网络/无安装也可运行；重依赖隔离在项目 `.venv`（不入 git） | 最小可用流水线、§3D | 已定 |
| D-008 | 2026-09-30 | Terms §5.3 的 “Oct 31” 视为全比赛通用日期；Challenge 1 以 challenge 页/FAQ 的 Oct 4 23:59 AoE 为准，提交前再次核实 | 两个官方页面原文，均记录于 competition_rules.md | 已定，待复核 |

## 待决策（到确认点才需要）

- 确认点 A（阶段 1 末）：表位 + 裁剪方案（最多两套，推荐一套）。
- 确认点 B（阶段 5 中）：3–5 个有结构依据的 pH 改造方案选择。
- 确认点 C（阶段 6 末）：最终序列、排名、公开材料批准；批准 ID + sequence hash 写入本文件。
