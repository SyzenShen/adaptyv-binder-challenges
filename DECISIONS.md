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
| D-013 | 2026-10-01 | **用户批准确认点 A+**：主选 B（生物表位包络 human EGFR UniProt 390–403 + 421–431），备选 C（316–343）仅在主选经书面排障后系统性失败时启用；432–433/H433 定向设计推迟到阶段 5，初始 BindCraft hotspot 不强制 H433。用户明确：避开 Cetux 表位不是因为禁止接触，而是第一代 campaign 要先发现独立的 de novo 结合方案、再把 H433 作为机制性 pH 杠杆测试。表位包络 ≠ BindCraft hotspot 列表，后者须经官方文档翻译（见 bindcraft_hotspot_translation.md）；包络外加残基必须回本检查点批准 | 用户 2026-10-01 书面批准；SCIENTIFIC_CHECKPOINT_A_PLUS.md | ✅ A+ 已关闭 |
| D-014 | 2026-10-01 | 阶段 2 只做云端 smoke test（官方最小示例 → 1–3 条 EGFR micro 轨迹，binder 长度取 40–100 aa 内一个合理值），不开始大规模 EGFR 生产；不突变靶点、不用 hardtarget/hard-target hack；OOM 最多 2 次有据尝试后出 compute_escalation.md，付费计算一律先批 | 用户 2026-10-01 Stage 2 指令；paid_budget 仍为 0 | 🟡 尝试 001 环境失败、修复待复测（见 D-017） |
| D-015 | 2026-10-01 | BindCraft 翻译执行决策：①裁剪 PDB 保留 UniProt 编号（resseq 310–481），hotspot 数字即 UniProt 数字（经 ColabDesign prep_pos 源码与 PDL1 非 1 起编示例证实）；②初始保守 hotspot = 390,393,399,421,424,431（6 个，优先 helix/分散）；broad 12 残基配置已备但初始不运行；③binder 单一长度 80 aa；④advanced 仅改 max_trajectories（1/3），其余逐字官方默认；⑤pin BindCraft 7713aa0；ColabDesign 未 pin 是官方安装脚本行为，云端实测回填 | bindcraft_hotspot_translation.md；官方 README/wiki 2026-10-01 实拉 | 已定 |
| D-016 | 2026-10-01 | 包络 B 内无 F/W/Y/M、无 relSASA≥0.20 疏水锚是**待 smoke 检验的假设**，不是改表位理由；禁止发明锚点、禁止为此突变靶点；若轨迹回避 B，按五类原因（编号翻译/hotspot 化学/采样数/裁剪/文档记载行为）先诊断 | 用户指令；domain3_geometry.csv 实测 | 已定 |
| D-017 | 2026-10-01 | 云端尝试 001 环境故障（Colab Py3.13.15/JAX 0.11.1 上 `jax.lib.xla_bridge` 已移除，ColabDesign clear_mem 崩于 PDL1）后：**不修改/不 monkey-patch 任何上游源码**；notebook 在 Colab 内自建隔离 Miniforge **Python 3.10** 环境，精确复刻官方 install_bindcraft.sh 约束（`jax=0.6.0`、`jaxlib=0.6.0=*cuda*`、conda-forge+nvidia、`CONDA_OVERRIDE_CUDA=12.6`、`numpy<2`、`flax<0.10`），ColabDesign pin e31a56f 以 `--no-deps` 装入该 env，PyRosetta 用 cp310 wheel；BindCraft 一律以 env python 子进程运行；权重下载前由 bindcraft_preflight.py 硬门验证（版本/clear_mem/xla_bridge/GPU matmul/PyRosetta）。不采用 issue#376 的 Colab runtime 回退法（不可脚本化、不可复现）。EGFR 一切科学配置零改动 | 官方 install_bindcraft.sh 原文；JAX changelog（0.8.0 移除 xla_bridge）；conda-forge jaxlib 0.6.0 cuda126 py310 构建与依赖；numpy 1.26.4 无 cp313 wheel；BindCraft#376；用户 2026-10-01 环境修复指令 | 已定，待云端复测验证 |

## 待决策（到确认点才需要）

- ~~确认点 A+~~：✅ 2026-10-01 已批准（D-013）。
- 确认点 B（阶段 5 中）：3–5 个有结构依据的 pH 改造方案选择（含 H433/432–433 扩展是否启动）。
- 确认点 C（阶段 6 末）：最终序列、排名、公开材料批准；批准 ID + sequence hash 写入本文件。
- 阶段 2 smoke 报告复核：是否进入阶段 3 小批次（需实测吞吐数据 + 用户批准）。
