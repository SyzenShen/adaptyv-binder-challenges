# Germinal 评估（Stage 1.5 Part H）

生成：2026-10-01。来源：论文与官方仓库（核实日期 2026-10-01），见末尾来源表。**结论先行：不替换 BindCraft 主线；VHH smoke test 仅在 ≥40GB NVIDIA VRAM、许可齐备且用户明确批准时作为可选侧枝。**

## 1. 实验协议 ≠ 计算管线（按指示明确区分）

- **A. Slack 提到的 "Germinal protocol"**：据用户 2026-10-01 转达，Adaptyv Slack 引用的是 Germinal 论文里的**实验验证流程**（基因合成→表达→split-luciferase 结合初筛→SPR/BLI 复核，论文图中按表达/结合分层）。这是"设计如何被湿实验检验"的参照，与比赛 GFP11 表达定量 + TwinStrep 的测试构建思路同源（split reporter 类思路），**它不是本项目要运行的软件**。我们尚未直接看到该 Slack 原文（待截图，见 HUMAN_ACTIONS）。
- **B. Germinal 计算管线**：GitHub `SantiagoMille/germinal`，三阶段**抗体**设计：ColabDesign/AlphaFold-Multimer **hallucination**（AbLang/IgLM 语言模型约束抗体样序列，CDR 特异 loss）→ **AbMPNN** 选择性重设计 → Chai-1（或 AF3/Protenix）**共折叠复核**，并用 **PyRosetta FastRelax/界面指标**过滤；Hydra 配置，持续循环直到产出通过过滤的设计。

## 2. 设计格式与验证状态

- 格式：**VHH（nanobody）与 scFv**（`run=vhh` / `run=scfv`），hotspot 按 `target.target_hotspots` 指定。不是 40–100 aa 单链 minibinder。
- 论文报告实验成功率 4–22%（PD-L1、IL3、IL20、BHRF1 四个靶，每靶 43–101 个设计），VHH 经 split-luciferase + BLI；scFv 直接以 Fab 形式做 SPR/BLI。这是其自报命中率，不是对本靶的承诺。
- 与本项目主线差异：BindCraft 产出**任意折叠的单链 de novo minibinder（40–100 aa，molecule_class=protein）**；Germinal 产出**抗体框架**（VHH ~110–130 aa 或 scFv ~230+ aa，molecule_class=nanobody/scfv）。比赛允许这些类别，但本项目既定主线是 minibinder；Germinal 若上，只作为侧枝，且其产物在提交 CSV 中必须用对应 molecule_class。

## 3. 工程需求（官方 README 当前口径）

- GPU：**NVIDIA，README 明确 40GB+ VRAM**；实测环境 A100 40/80GB、H100 40GB MIG、L40S 48GB；官方注明其测试为 130 aa 靶 + 131 aa VHH，**更大体系建议 60GB+**（我们的 Domain III 裁剪靶 ~172 aa）。
- 软件/数据：PyRosetta（**学术许可，需自行申请**）、JAX CUDA、AlphaFold-Multimer 参数（手动下载，~数 GB）、可选 AF3 参数；IgLM 为自定义许可、管线整体对商用/再分发有限制；仓库代码 Apache-2.0，模型权重 CC-BY-4.0（以仓库 LICENSE 为准，商用前需逐条核对）。
- 运行模型：连续循环至 accepted；`failure_counts.csv` 记录每步淘汰——单次作业耗时无界，需要持久 GPU，不适合会断连的交互会话。
- 仓库状态（2026-10-01）：活跃开发，README 标注 "last user-validated commit 2c0a13b"，其后多个修复 PR 与在途分支；默认配置"不是开箱即用的好参数，只是起始点"。

## 4. 我们当前算力能否现实运行？

| 资源 | 现状 | 判断 |
|---|---|---|
| 本机 Intel Mac / AMD 4GB | 无 CUDA | 不可行 |
| Colab 免费层 | T4 16GB | 不可行（<40GB） |
| Colab Pro/Pro+ | L4 22GB 常见，A100 40GB 偶发且限时 | 40GB 仅"可能"；172 aa 靶官方建议 60GB+；PyRosetta 许可与参数下载、无界循环、断连风险叠加；免费/Pro 不现实 |
| 学校/付费 ≥40GB Linux GPU | 当前无 | 唯一现实路径，需用户批准预算与许可 |

## 5. 决定（与 MASTER_PROMPT §7 主线一致）

- **MAIN：BindCraft de novo minibinder 工作流不变。**
- **OPTIONAL SIDE BRANCH：Germinal VHH smoke test，仅当同时满足：**
  1. 可稳定使用 ≥40GB（更大体系建议 60GB+）NVIDIA GPU；
  2. PyRosetta 学术许可与所需权重许可已由用户持有/接受；
  3. 用户明确批准计算与时间成本（paid_budget 当前 = 0）。
- 不启动 Germinal 生产采样；不安装到本机；若未来侧枝启动，锁定 commit（参考其 validated commit）、隔离云端环境、独立记录 provenance，并先核对 molecule_class 与提交上限（≤20 条，与主线合计）。

## 6. 来源（2026-10-01 核实）

- Mille-Fragoso LS. et al., "Efficient generation of epitope-targeted antibodies with Germinal", *Nature Biotechnology* 2026, doi: [10.1038/s41587-026-03187-0](https://doi.org/10.1038/s41587-026-03187-0)；PubMed 42337361；bioRxiv 预印本 2025.09.19.677421。
- 官方仓库：https://github.com/SantiagoMille/germinal （README，requirements/setup/docker/singularity 段；2026-10-01 读取）。
- 第三方文档（仅交叉参考，不作权威）：proto.evodesign.org/docs/tools/binder-design/germinal；docs.tamarind.bio/tools/germinal。
