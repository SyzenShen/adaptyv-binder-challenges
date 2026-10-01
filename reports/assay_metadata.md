# 实验条件元数据（Stage 1.5 Part F/G）

生成：2026-10-01。机器可读版本：[configs/candidate_metrics.json](../configs/candidate_metrics.json)。

## 1. 来源与证据状态

下列 1–6 条为 **USER_PROVIDED_OFFICIAL_COMPETITION_SLACK**：由用户于 2026-10-01 从官方比赛 Slack 转达（指令文本存档于会话记录）。**截图证据：PENDING（尚未入库）**。在截图归档前，这些条目不得升级为"已独立核实"；如与官方页面/Terms 冲突，以官方页面为准并回改。

- 待用户动作（HUMAN_ACTIONS A6）：把 Slack 原消息截图放入 `reports/slack_provenance/`（文件名带日期），我会回填本文件引用。

## 2. 测定构建与读数

1. 被测试设计在 C 端挂接，顺序约为：**design – 短柔性 linker – GFP11 – 柔性 linker – TwinStrep**。
   - linker 的确切序列/长度：**未公开，null，禁止猜测**（candidate_metrics.json 中保持 null 并注明原因）。
2. 组织方建议：**paratope 尽量放在 N 端一侧**，小 binder 尤其如此。
3. **GFP11 互补（split-GFP）用于表达定量**——表达是与结合**分离的评估轴**：表达低不等于不结合，结合读数也不能当表达证据。
4. **EGFR ECD 在 HEK293 表达，带 human-type 糖基化**——糖基化是真实测定约束（见 [glycan_epitope_audit.md](glycan_epitope_audit.md)）。
5. 低 pH 条件用 **MES 替换 HEPES**；pH 比较为 **6.5 vs 7.4**。
6. 标准缓冲液约含 **150 mM NaCl、Tween-20、3 mM EDTA**（Tween 浓度未给出）。

## 3. 对设计与计算的直接约束

- **C 端构造取向**：paratope 偏 N 端意味着生成后要检查每个设计的界面在序列上的三分布（N/mid/C 各三分之一）、C 端到靶点的最小距离与"出口方向"、C 端是否溶剂暴露——避免设计成 C 端界面被 linker/标签干扰。BindCraft 生成时轨迹方向不可直接控制，因此这些是**排序/检查指标（ranking/inspection），不是硬阈值**（与 Slack 建议口径一致）。
- **不得**给当前设计自行拼接猜测的 GFP11/TwinStrep 序列；提交的仍是裸设计序列（40–100 aa）。
- **EDTA 3 mM**：二价金属被螯合。任何依赖 Mg²⁺/Zn²⁺/Ca²⁺ 等金属配位的结合都不应出现；候选检查项中加入"界面金属依赖巡检"（无金属离子结构证据 + 不出现典型金属螯合几何）。
- **离子强度**：~150 mM 单价盐 ≈ 生理强度；阶段 5 若做静电/pKa 解释，以该量级为背景，不做真空静电推断。
- **MES/HEPES/Tween 不得宣称已被建模**，除非阶段 5 起实际采用并验证了显式缓冲液方法（默认不做）。
- 缓冲液本身对 His pKa 的直接影响通常很小，本项目不把换缓冲液当作 pH 机制证据；pH 证据仍按 MASTER_PROMPT 阶段 5 分级。

## 4. 表达/可开发性计划指标（Part G，阶段 3 起逐候选记录）

split-GFP 定量表达 → **表达独立成轴**。计划记录（工具支持时；预测 ≠ 实测）：

1. 单体折叠与自洽性（monomer self-consistency）；
2. 暴露疏水性（exposed hydrophobicity，结构上外露的大疏水斑块）；
3. 聚集/溶解性 liability 标志；
4. 埋藏的未满足极性基团（buried unsatisfied polar）；
5. 末端无序倾向（terminal disorder，尤其 C 端靠近 linker）；
6. 序列 liability 扫描（如异常重复、蛋白酶基序等，具体规则阶段 3 定版并记录参数）。

纪律：任何可开发性预测都标注 computational evidence；无表达实测数据时 experimentally_validated 永远 false，不拿预测分替代 split-GFP 读数。

## 5. pH 表述边界（再次明示）

- 只能写 pH 6.5 vs 7.4 条件；不得编造 KD_6.5/KD_7.4/选择性倍数；
- pLDDT/ipTM/ipSAE/自洽性都不是 KD，也不是 pH 开关证据；
- PROPKA 只给近似 pKa；机制结论分级按 MASTER_PROMPT 阶段 5（hypothesis / 近似 pKa 支持 / 多构象多方法一致 / 反证）。
