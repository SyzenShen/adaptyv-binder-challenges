# DECISIONS — 关键决策记录（只记录已定，不记录设想）

| ID | 日期 (UTC) | 决策 | 依据 | 状态 |
|---|---|---|---|---|
| D-001 | 2026-09-30 | 以用户已创建的 `egfr-binder-challenge/` 作为项目根目录；远端私有仓库 `SyzenShen/egfr-binder-challenge`（用户创建并提供 URL），与本地目录同名 | 用户在本目录放置并指令执行 提示词.md；§4“默认”措辞 | ✅ 已定并落实 |
| D-002 | 2026-09-30 | 本地 Intel Mac 只承担 CPU 分析、Git 写入与轻量查看；GPU 计算走 Colab（免费档先行）；不装 CUDA/虚拟机，不改全局 Python | 实测无 CUDA、磁盘仅 27.5GB；MASTER_PROMPT §3C/§5 | 已定 |
| D-003 | 2026-09-30 | paid_budget=0；任何 Colab 付费方案、付费 GPU/API 在书面批准前不开通 | MASTER_PROMPT §3C | 已定 |
| D-004 | 2026-09-30 | 生产生成主线只搭 BindCraft 官方流程一条；RFdiffusion/AF3/Chai 不并行安装；Boltz 仅作阶段 4 的独立复核候选 | MASTER_PROMPT §7/§9 | 已定（阶段 2 执行前再按官方文档复核版本） |
| D-005 | 2026-09-30 | 提交长度目标锁定官方 minibinder 分类 40–100 aa；CSV 三列最低 schema 已写入 configs/competition.json | EGFR 页 Submission requirements + FAQ 1/2/5（2026-09-30 核实） | 已定 |
| D-006 | 2026-09-30 | mouse 实验构建体在官方信息获取前保持 null，不照搬 human 25–645、不假定 Q01279 isoform | EGFR 页 mouse 标签实测为空；MASTER_PROMPT §2/§6 | 部分更新见 D-009；仍待官方凭据 |
| D-007 | 2026-09-30 | 阶段 0 测试仅用标准库，保证无网络/无安装也可运行；重依赖隔离在项目 `.venv`（不入 git） | 最小可用流水线、§3D | 已定 |
| D-008 | 2026-09-30 | Terms §5.3 的 “Oct 31” 视为全比赛通用日期；Challenge 1 以 challenge 页/FAQ 的 Oct 4 23:59 AoE 为准，提交前再次核实 | 两个官方页面原文，均记录于 competition_rules.md | 已定，待复核 |
| D-009 | 2026-10-01 | 人鼠 ECD 比对采用 mouse Q01279 25–647（623 aa）边界，证据等级 `USER_PROVIDED_OFFICIAL_COMPETITION_SLACK`（用户转达 Slack 原文）；官方页当天仍空，所有结论标注"待 A6 截图/官方文本证实" | 用户 2026-10-01 指令文件附带的 Slack 信息；不满足即不能当作官方已核实 | 暂定，凭据未到 |
| D-010 | 2026-10-01 | **撤回阶段 1"H418 为表面 His"结论**：6ARU 全 ECD SASA 显示 H418 relSASA=0.022（埋藏，不可被外部 binder 接触）；pH 机制几何聚焦 H370（部分暴露 0.155、近 E368）与 H433（0.676 高暴露、8 Å 内无 Asp/Glu，机制 B 需 binder 自带酸性残基） | audit_geometry.py 实测；ph_target_hotspot_audit.md | 已定（结构事实） |
| D-011 | 2026-10-01 | 生产生成主线仍只保留 BindCraft；Germinal（VHH/scFv 抗体路线，Mille-Fragoso 2026）不上主线，仅在用户明确批准时作为可选侧枝做小 smoke test；其 ≥40–60 GB VRAM + PyRosetta 学术许可与免费 Colab/40–100 aa 非抗体赛题不匹配 | germinal_assessment.md（论文+仓库实测调研） | 已定 |
| D-012 | 2026-10-01 | 不猜 GFP11/TwinStrep 等标签连接序列；candidate_metrics.json 中所有 linker/标签字段保持 null 并注明原因；表达/可开发性作为与 pH 分离的独立评分轴 | assay_metadata.md；MASTER_PROMPT §6 禁止推测 | 已定 |
| D-013 | 2026-10-01 | A+ 推荐（非用户已批）：主选 B = 精修 Scheme 1 hotspot 390–403 + 421–431（H433 不纳入初始 hotspot，432–433 扩展推迟到阶段 5 凭 PROPKA/多构象证据决定）；备选 C = EPI_H_1 316–343（高糖/Cys 风险）；A 原样与 D(EPI_H_4) 不推荐，理由见 checkpoint | SCIENTIFIC_CHECKPOINT_A_PLUS.md | **待用户批准** |

## 待决策（到确认点才需要）

- 确认点 A+（阶段 1.5 末）：批准主选 B / 备选 C / 维持 A / 再分析 D；并裁定 H433 扩展推迟处理是否同意。
- 确认点 B（阶段 5 中）：3–5 个有结构依据的 pH 改造方案选择。
- 确认点 C（阶段 6 末）：最终序列、排名、公开材料批准；批准 ID + sequence hash 写入本文件。
