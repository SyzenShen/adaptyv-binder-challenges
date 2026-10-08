# SCIENTIFIC CHECKPOINT A+ — Target + Assay Aware Epitope Audit 终决

日期：2026-10-01。状态：**等待用户科学决策，不启动 EGFR 生产生成。**
证据链：[target_preparation.md](reports/target_preparation.md)（阶段 1）、[human_mouse_ecd_alignment.csv](data/processed/human_mouse_ecd_alignment.csv)、[glycan_epitope_audit.md](reports/glycan_epitope_audit.md)、[ph_target_hotspot_audit.md](reports/ph_target_hotspot_audit.md)、[cetuximab_distance_audit.md](reports/cetuximab_distance_audit.md)、[epitope_3d_continuity.md](reports/epitope_3d_continuity.md)、[assay_metadata.md](reports/assay_metadata.md)、[germinal_assessment.md](reports/germinal_assessment.md)、[geometry_audit.json](data/processed/geometry_audit.json)。

所有"距离"为 6ARU 沉积坐标最小重原子距离；SASA 为全 ECD（链 A 四域完整）上下文 Shrake–Rupley；mouse 映射基于 Q01279 25–647 ECD（Slack 来源，页面仍空，待 A2 截图/官方文本确认）。无加权评分——以下为逐维度科学论证。

## 四个决策

### A. Scheme 1 原样：EPI_H_2 (385–403) + EPI_H_3 (416–431)

- **人鼠保守**：EPI_H_2 17 identical + 2 conservative（Q390R、D393E，后者酸性保留）；EPI_H_3 16/16 identical。
- **糖风险**：段边缘有 6.55–7.78 Å 的近糖距离（P389→N413 糖 6.55；D416→N444 糖 7.78；埋藏 H418→N413 糖 7.36）；所有 patch 残基 occGly=0。成熟 HEK293 糖链更大，边缘存在不确定性。
- **pH 机会**：结合面含 D388/E391/D393/E421/E424（机制 A 的靶点酸性伙伴）；H433 在 3.35 Å 外但不在 hotspot 内（机制 B 未利用）；窗口内 H418 **已证实埋藏，不可用**。
- **3D 连续性**：两段实为一面（最小重原子 2.71 Å，37 个 <5 Å 跨段对，合并 1431 Å²），但原窗口包含多排域内埋藏残基（392/395/398/401–403；417/419/420/423/426/428），交给 BindCraft 的 hotspot 含噪声。
- **完整 ECD 可及性**：暴露判定即在完整四域上下文中成立；tethered 态可及，extended 态 Domain III 同样朝外（文献共识，未自行重算）。
- **assay 标签（靶点阶段可知部分）**：单一面，binder C 端出口方向有选择空间；paratope N 端取向是 binder 侧性质，目标阶段不可知，已列阶段 3 指标。
- **主要不确定**：mouse 构建体未经官方页面证实；成熟糖链体积大于沉积糖；3.2 Å 静态结构。

### B. Scheme 1 精修（向 H433 留门，不纳入）：**390–403 + 421–431**

- **人鼠保守**：同 A（剔除的 385–389 中 P/L/D 均 identical，剔除不损失保守性）。
- **糖风险（相对 A 明确下降）**：段 2 糖最小距离 7.78→**12.58 Å**；段 1 6.55→**7.10 Å**（仅 Q390 边缘）；两段均不再有 <7 Å 的糖接触。缺口 404–415 糖伸入区被完全排除在 hotspot 外。
- **pH 机会（保留且更聚焦）**：机制 A 的酸性暴露面保留（E391/D393、E421/E424）；段 2 末端 K431 与 H433（relSASA 0.676）相邻 3.35 Å——**H433 留在 hotspot 外但物理上紧邻**，阶段 5 若 PROPKA/多构象证据支持机制 B，可做"432–433 定点扩展"的少量变体，而无需重选表位。不现在纳入的理由：Q432/H433 直接位于 Cetuximab 功能表位（2.6/3.47 Å），纳入即主动选择已知治疗抗体接触姿态，新颖性/IP 应留给阶段 6 评估后再决定。
- **3D 连续性**：与 A 同一连续面；hotspot 只保留朝外残基排（段 1：Q390/E391/D393/K396/K399；段 2：E421/N422/E424/R427/R429/T430/K431；暴露 SASA 506+600 Å²），对 BindCraft 是更干净的输入。
- **Fab 距离**：≥9.11 Å（最近点 K431），不接触 Cetuximab。
- **完整 ECD 可及性 / 标签**：同 A。
- **主要不确定**：同上；另：精修后单段残基数较少（14+11），BindCraft 是否需要更宽 hotspot 在阶段 2 smoke test 后按官方建议调整（科学边界变更必须回本检查点，不为跑通擅改）。

### C. Scheme 2：EPI_H_1 (316–343)

- **人鼠保守**：25 identical + 3 conservative（M318V、V323I、E330D）。
- **糖风险（四个方案中最高）**：K335 距 N361 糖 **4.27 Å** 且被沉积糖遮挡 11.3 Å²；I340 距 N352 糖 6.6 Å；331–343 一段 6.6–10 Å。**N361 是人特有 sequon（鼠 361=Y）**——人测定侧糖风险真实存在，鼠测定侧该位点无糖，两物种几何环境系统性不同。成熟复杂型糖链可能把该面变成连续糖被。
- **pH 机会**：距部分暴露的 **H370 仅 3.23 Å**（环区，relSASA 0.155，邻近 E368）——机制 B 在该方案下几何可及，但 H370 暴露度有限且距 N352 糖 7.71 Å。
- **3D 连续性**：单一连续大环/环-螺旋混合面，暴露面积大（多残基 relSASA 0.4–0.86），无跨段问题。
- **Fab 距离**：≥12.58 Å，最远离 Cetuximab。
- **结构代价**：4 Cys（C326/C329/C333/C337）、3 对二硫键（C311–C326、C329–C333、C337–C362）穿过该面，拓扑刚性、可对接面积受二硫键分割。
- **完整 ECD 可及性**：暴露判定在全 ECD 上下文成立。
- **主要不确定**：成熟糖链外推风险最高；二硫键面对 minibinder 设计的实际可设计性未知（只能靠生成结果回答）。

### D. 修订的 Domain III 保守 patch：以 EPI_H_4 (447–460) 为核

- **人鼠保守**：14/14 identical。
- **糖风险**：S447 距 N444 糖 7.46 Å；从 449 起 ≥12.4 Å。
- **Fab 距离**：**8.57 Å（四方案最近）**，D460 为最近点；下游 K467（7 个残基之外）已在 Cetuximab 界面（3.39 Å）。
- **3D 连续性 / 面积（决定性弱点）**：447–453 基本埋藏（relSASA 0.01–0.19），真正暴露仅 K454/E455/S457/D458/D460（395–400 Å²，3–5 残基），作为独立 hotspot 过小且不成片；向 432–442 扩则直接进入 Cetuximab 功能表位与 N444 糖邻近带，性质退化为"沿抗体表位行走"，不构成更优的独立方案。
- **pH 机会**：无 His；酸性 D458/D460 可作机制 A 伙伴但面积小。
- **判定**：记录但不推荐（面太小、边界两侧分别是糖与 Cetuximab 表位）。

## 推荐

**主选：B（Scheme 1 精修，hotspot = 390–403 + 421–431；H433 不纳入初始 hotspot，作为阶段 5 经证据批准后的定点扩展位 432–433）。**

理由（相对其他三项的边际论证）：
1. 对 A：同表位、同 pH 潜力，但糖距离从 6.55/7.78 Å 推到 7.1/12.6 Å，并剔除全部埋藏残基与糖伸入缺口——只减风险不减机会。
2. 对 C：避免了 4.27 Å 近糖、人特有的 N361 物种不对称和四 Cys 拓扑；pH 抓手从"勉强可及的 H370"换成"紧邻的高暴露 H433 + 酸性面"，且不立即承担 Cetuximab 表位代价。
3. 对 D：B 是面积与连续性都成立的真表面，D 不是。

**备选：C（Scheme 2，316–343）**，仅在 B 的 smoke test/小批次出现系统性失败（例如 BindCraft 对双段 hotspot 不收敛）且失败不可通过其官方文档参数解决时启用；启用即接受高糖风险并必须配 glycan-aware 检查，同时 H370 作为机制 B 抓手。

**阶段 2 起对 B 的附加条件（不是硬阈值）**：
- 生成用裁剪靶仍为 Domain III 310–481（保留三对域内二硫键；C470–C499 跨界断裂对该 hotspot 无影响，见阶段 1 报告）；
- 阶段 3 起逐候选记录 [candidate_metrics.json](configs/candidate_metrics.json) 指标（N 端 paratope 比例、C 端出口、糖存在/不存在 clash、EDTA 金属依赖巡检、表达轴分离）；
- 不拼接任何 linker/GFP11/TwinStrep；pH 只说 6.5 vs 7.4；
- hotspot 的任何科学变更回到本检查点重新批准。

## 待用户决策事项

1. 批准 B / 改选 C / 维持 A / 要求进一步分析 D 或新 patch？
2. 是否同意"H433 扩展（432–433）推迟到阶段 5 凭证据决定"这一处理？
3. A2：mouse 构建体 25–647 的 Slack 原文截图（当前为用户转达，页面 2026-10-01 仍空白）。
4. A3：参赛资格 + Track 3 注册状态。
