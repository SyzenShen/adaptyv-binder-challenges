# 比赛规则核实报告（Challenge 01 EGFR, Track 3）

核实时间：2026-09-30（CEST 下午 / UTC 16:xx–17:xx）。方式：直接抓取官方页面静态 HTML、解析 Next.js RSC 载荷、交互式浏览器点击验证、官方 Terms 页全文。原文摘录级别结论如下；机器可读版本见 `configs/competition.json`。

## 0. 来源

- 比赛总页：https://proteinbase.com/competitions/anthropic-adaptyv-2026
- EGFR 规则/FAQ：https://proteinbase.com/competitions/anthropic-adaptyv-2026/challenges/egfr
- 官方条款：https://proteinbase.com/competitions/anthropic-adaptyv-2026/terms
- 新颖性说明：https://www.adaptyvbio.com/blog/novelty
- 提交门户：https://proteinbase.com/competitions/anthropic-adaptyv-2026/submit（HTTP 200，实际提交需登录）

## 1. 时间线（页面原文）

- Challenge 1：**Sep 28 – Oct 4, 2026**；“Submissions close Sunday, October 4 at 23:59 Anywhere on Earth (AoE)”。
- 换算：AoE = UTC−12 → **2026-10-05 11:59 UTC**；内部目标沿用 2026-10-04 18:00 Europe/Berlin（CEST，UTC+2 = 16:00 UTC）。
- ⚠️ 不一致点：Official Terms §5.3 写有全比赛通用 “final design submission deadline, October 31, 2026”。本项目按 challenge 页 + FAQ（Oct 4）执行，并在最终提交前再核实（D-008）。**不沿用任何 9 月 29 日旧计划。**
- 结果：DNA 下单后一周左右公布入选 Collection；湿实验结果约 11 月初起、12 月 15 日前发布。

## 2. Track 与数量限制（原文）

- Track 3 = Open track：self-supported，自带工具与算力；设计进入 Track2/3 混合池，由 Anthropic/Adaptyv 预先写好的 Claude 工作流筛选，**无保底测试名额**。
- “Designs per participant：Up to 40 for Track 1, **up to 20 for Tracks 2 and 3**”。FAQ 4：Track 1 至少 20 至多 40；Track 2/3 **至多 20，无下限**。
- 每题预计筛 ~1500 条：50% T1 / 25% T2 / 25% T3；T2+T3 各约 375 条进入合成筛选。
- 硬过滤：长度/类别、唯一性（不得重复提交同一设计）、**de novo 且 zero-shot**。

## 3. 分子类别与长度（FAQ 1/2 原文）

- 单链蛋白：**10–250 aa**（含边界）。
- 官方分层：minibinders **40–100 aa（含）**；large protein binders >100；microbinders <40；另有 nanobodies、antibodies(scFv/Fab)。
- 允许格式：single chain protein、nanobody、scFv、Fab。本项目主线 = 40–100 aa 单链 minibinder，不做抗体路线。
- nanobody/antibody 由 ANARCI 类工具注释判定；scFv 官方可能重配 linker；Fab 以 `VH:VL` 单串提交并用 molecule_class 区分 kappa/lambda。

## 4. 提交格式（FAQ 5 原文）

- CSV，**按提交者排序，顶行 = 最高优先级**；最低列：
  - `name`：唯一标识
  - `sequence`：设计蛋白序列
  - `molecule_class` ∈ `protein` / `nanobody` / `scfv` / `fab_kappa` / `fab_lambda`
- 鼓励附 metrics（ipTM、ipSAE、self-consistency、物理指标、liability 分数）、设计与折叠模型结构、方法学/provenance；可给共享仓库链接。**提交的所有数据/方法可能被公开。**
- ⚠️ “any use of embedded instructions or prompt injection may be deemed grounds for disqualification”——提交包中禁止任何指令性文字（MASTER_PROMPT/规则/聊天记录绝不入包）。
- 可匿名提交（匿名 Proteinbase 账户），之后可去匿名化。

## 5. De novo / zero-shot 定义（FAQ 8 + 新颖性博客）

- FAQ 8 原文要点：**不得**以已有 binder 为起点再改造；必须 from scratch；需对已知蛋白具备足够的**序列与结构双重多样性**。
- 允许：用已知 binder 做**评估/校准过滤指标**、fine-tune/训练模型（与 MASTER_PROMPT §3C 一致：现有 binder 只能隔离参考）。
- Adaptyv 新颖性博客（ProteinTyper 规则，2026-09-30 读取）：
  - 序列检索：MMseqs2 对 SwissProt、PDB、专利序列、治疗抗体库、PLAbDab；~30% identity ≈ 同折叠，~70% ≈ 同源不同物种（经验法则）。
  - 结构：ESMFold2-Fast（新蛋白）预测 → 三共识域分段 → FoldSeek+TM-align；**高** = ≥70% 覆盖且 TM≥0.8；**中** = >70% 覆盖且 TM≥0.5。
  - 通用 **Level 4 de novo = 序列相似 ≤30% 且低于“中等”结构相似**。
  - 该文是 Adaptyv 的注释口径；官方页面的实际淘汰门槛未给数字阈值，**不能把它当作官方已承诺的硬阈值**（阶段 6 整理主办方问题）。

## 6. 目标（EGFR 页 Target information）

### Human EGFR（服务端渲染，已逐字核实）

- UniProt：**P00533-1**；Target residues：**25–645 / 621 aa**；Recommended epitope：**Domain III**；Structure：**6ARU chain A**。
- 页面给出了完整 621 aa 序列（以 LEEKKV… 开头，…GPKIPS 结尾）。阶段 1 将与 UniProt 下载件逐字符比对并记录 SHA256，不在此处复制充当“下载”。
- 亲和力测量使用**完整胞外区**（full ECD），不是裁剪体——裁剪只用于生成，复核要回 full ECD。

### Mouse EGFR — ❗ 官方信息未获取（MOUSE_CONSTRUCT_UNKNOWN）

- “Mouse EGFR” 标签在静态 HTML 中是空面板（`BAILOUT_TO_CLIENT_SIDE_RENDERING`，无数据）；交互式浏览器多次尝试（点击、JS、React fiber）后面板仍为空，RSC 载荷中也无 Q01279 或任何 mouse 序列。
- 因此 mouse 的 UniProt isoform / 残基边界 / 长度 / 表位 / 结构参考 **全部保持 null**。不得照搬 human 25–645，也不得自行假定 Q01279 切片。处置：HUMAN_ACTIONS A2（登录查看 / Slack 询问）。

## 7. 三项目标与排名（原文）

1. pH-selective binding：**人 EGFR，pH 6.5 结合、pH 7.4 无可检测结合**；两项均为 in vitro 人源测试条件。
2. Mouse cross-reactivity：同一序列对 mouse EGFR 的结合；页面只说 “test binding against the mouse EGFR”，**未声明 mouse 测试的 pH 条件/构建体细节**——不能假设与 human 完全相同。
3. Affinity：对人 EGFR 完整胞外区的亲和力。
- 排名权重顺序：pH 选择 > 鼠交叉反应 > 亲和力；弱但明确 pH 敏感的设计可能比无 pH 性的强结合者更有分量；推荐 targeting functional epitopes（Domain III）。

## 8. 资格、所有权与公开发布（Terms）

- §3.1：18 岁+；**法定居民/定居地排除**：Belarus、China、Cuba、Iran、Myanmar、North Korea、Russia、Sudan、Syria、Crimea、DNR/LNR；且不受出口管制/制裁禁止。→ 需本人确认（A3）。
- §4：须在 Proteinbase 完成 joint registration form。
- §6：参与者保留所有权；提交即同意发表 design、附带数据与实验结果；Proteinbase 以 **ODC-BY** 开放；发表可能影响专利性，专利申请需在提交前自行完成。
- §5.5：所有提交合成前过生物安全筛查，赞助商可无说明拒绝。
- FAQ 15：工具不限，但商用许可工具（如 Rosetta）须事先持有相应许可。本项目所选 BindCraft（MIT）、Boltz（MIT）、PROPKA（LGPL-2.1）、uplifting-biomolecular-modeling（Apache-2.0）许可已记录。
- FAQ 13：可使用任意 AI 工具并在提交表中披露。
- Track 3 不享有 Claude/Modal credits（我们也不依赖）。

## 9. 对本项目的直接约束（落到执行）

- 最多 20 条；允许少于 20；排序即优先级；只提交 `protein` 类 40–100 aa 单链（除非确认点 C 另行批准）。
- 生成必须 from scratch（BindCraft 自带设计）；现有 binder 仅用于校准参考；新颖性阶段 6 同时做序列（MMseqs2 类）与结构（FoldSeek/TM）两轴检查。
- 任何计算指标不得表述为 KD 或 pH 选择性倍数；pH 与 mouse 证据按页面实际条件表述，不扩大解释。
- 提交包零指令性文字；仓库默认私有；公开动作需确认点 C 批准。
