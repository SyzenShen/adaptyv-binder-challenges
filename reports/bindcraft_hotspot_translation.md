# BindCraft Hotspot Translation — 已批准生物表位 B → BindCraft 配置

日期：2026-10-01。确认点 A+ 用户已批准（见 [DECISIONS.md D-013](../DECISIONS.md)）。
**本文只做翻译，不改变已批准的生物表位包络。包络外新增任何残基必须回科学检查点重新批准。**

## 0. 官方文档版本（均为 2026-10-01 实际拉取）

- BindCraft 仓库：`martinpacesa/BindCraft`，main HEAD **`7713aa0d0d351e4117a8befeb8541f3a8ebd3368`**（2026-09-21）。云端安装将 pin 此 commit 并在环境元数据中记录实际检出 SHA。
- ColabDesign（BindCraft 依赖，install 脚本未 pin）：`sokrypton/ColabDesign` main HEAD **`e31a56fe1d9b4de25c8697f3a28b75892941cc72`**（2025-10-23）；云端记录实际解析到的 commit。
- AF2 权重：`alphafold_params_2022-12-06.tar`，来源 `https://storage.googleapis.com/alphafold/`（官方安装脚本固定），约 5.3 GB。
- PyRosetta：pip 自 `west.rosettacommons.org` 季度发行；**商业用途需许可证**，本项目学术参赛按非商业处理。

官方原文（README + wiki "Target preparation & Hotspot selection"）：

> "target_hotspot_residues -> which position to target … `1,2-10` or chain specific `A1-10,B1-20` … better to select multiple target residues or a small patch"
> "hotspots can be either defined individually ('23,25,27,29,30'), as residue ranges … We recommend defining several surface residues within a radial patch as hotspots … We generally recommend targeting secondary structures, as opposed to loops, and hydrophobic residues with few rotameric states. Ideal target patches contain either a phenylalanine, tyrosine, tryptophan, isoleucine, leucine, or methionine at the binding site."
> "the user hotspot definition can be ignored if the choice of target site is suboptimal … the hotspot contact loss is part of a larger composite loss function"（binder 迁移是已知、预期行为，不等于配置错误）

## 1. 已批准的生物表位包络（envelope）

human EGFR UniProt P00533-1 **390–403（14 残基）+ 421–431（11 残基）**。
这是生物学决策边界，**不是** BindCraft hotspot 列表。证据链见 [SCIENTIFIC_CHECKPOINT_A_PLUS.md](../SCIENTIFIC_CHECKPOINT_A_PLUS.md)、[domain3_geometry.csv](../data/processed/domain3_geometry.csv)。

## 2. 包络内实际暴露残基（全 ECD 上下文 Shrake–Rupley relSASA ≥ 0.20）

| 段 | 残基 | relSASA | SASA Å² | 二级结构 |
|---|---|---|---|---|
| 390–403 | **Q390** 0.607 / 136.7 / helix；**E391** 0.300 / 66.9 / helix；**D393** 0.367 / 70.9 / helix；**K396** 0.254 / 59.9 / helix；**K399** 0.263 / 62.0 / coil | | | |
| 421–431 | **E421** 0.213 / 47.6 / helix；**N422** 0.385 / 75.0 / coil；**E424** 0.457 / 101.9 / coil；**R427** 0.250 / 68.4 / coil；**R429** 0.621 / 170.0 / coil；**T430** 0.386 / 66.3 / coil；**K431** 0.222 / 52.3 / helix | | | |

共 12 个，与 Stage 1.5 审计识别并经用户列名的 12 个逐一核对一致（身份、SASA、二级结构取自 [domain3_geometry.csv](../data/processed/domain3_geometry.csv)，未重新估计）。

### 疏水/芳香锚：明确不存在，不虚构

包络内全部疏水残基的暴露度（relSASA / SASA）：L392 0.006/1.3、I394 0.145/28.6、L395 0/0、V398 0/0、I401 0/0、L423 0/0、I425 0.096/18.9、I426 0/0（T397/T402/G403/G428 另计）。

**包络内没有 F/W/Y/M；L/I/V 没有一个 relSASA ≥ 0.20（最高 I394=0.145，28.6 Å²）。即不存在官方所建议的疏水/芳香锚。** 这不是拒绝该表位的理由，而是 smoke test 要检验的假设：一个几乎全极性/带电、两段式、部分位于 coil 的 patch 能否被 BindCraft 稳定靶向。初始 smoke 不为此做任何目标突变或 hard-target 处理。

## 3 & 4. 实际 BindCraft hotspot 与 PDB 编号（同一编号，翻译为恒等映射）

**裁剪 PDB**：[6ARU_chainA_domain3_310-481.pdb](../data/processed/6ARU_chainA_domain3_310-481.pdb)，由 [make_domain3_pdb.py](../scripts/make_domain3_pdb.py) 从 6ARU chain A auth 286–457 原样提取，**resseq 重写为 UniProt 位置 310–481**（依据：6ARU chain A auth_seq_id + 24 = UniProt，struct_ref_seq 推导，无 insertion），chain A，172 残基全部有 CA，坐标未改，无残基增删/突变。

编号已用 ColabDesign 源码核实（`shared/prep.py::prep_pos`，commit e31a56f）：hotspot 字符串按 **PDB 文件中的 resseq + 链字符**匹配，支持 `390,393-399`、`A390` 语法；官方 PDL1 示例本身从非 1 编号起（文件 18–132，hotspot `"56"` 即文件中 A56 TYR）。因此我们的 crop 保留 UniProt 编号，hotspot 数字即 UniProt 数字，无偏移需要心算：

| | UniProt / 6ARU auth+24 | crop PDB resseq（BindCraft JSON） |
|---|---|---|
| 编号 | 390 / 393 / … / 431 | **390 / 393 / … / 431（恒等）** |

### 配置 1（初始 smoke 唯一使用，保守小集，6 残基）

[egfr_d3_B_conservative.json](../configs/bindcraft/egfr_d3_B_conservative.json)

```
"target_hotspot_residues": "390,393,399,421,424,431"
```

- 两段各 3 点，沿面展开（390→399 跨第一段，421→431 跨第二段），符合"radial patch 内多个表面残基"；
- 优先 helix：390/393/421/431 为 helix；仅 399/424 取 coil 以覆盖两段衔接区与面中心；
- 化学上 4 酸/碱 + Q，刻意小而分散，给复合损失留出空间；
- binder 长度单一值 **80**（`"lengths": [80,80]`；官方 wiki 最优区间 60–180 aa，80 落在赛题 40–100 内且近官方推荐下沿）。

### 配置 2（备比较，已准备但初始 smoke 不运行）

[egfr_d3_B_broad.json](../configs/bindcraft/egfr_d3_B_broad.json)

```
"target_hotspot_residues": "390,391,393,396,399,421,422,424,427,429,430,431"
```

依据官方"several surface residues"建议取全部 12 个 relSASA≥0.20 残基。**仅当配置 1 的轨迹系统性回避 B、且排障排除了编号/裁剪/采样数原因后**，作为同一表位上的第二次假设检验运行；它不扩大包络、不引入任何包络外残基。

两套目标配置都配 [advanced_smoke_max3.json](../configs/bindcraft/advanced_smoke_max3.json)：**逐字节复制官方 `default_4stage_multimer.json`，仅把 `"max_trajectories": false` 改为 `3`**（该开关官方注释为 benchmarking 用；注意它计数的是 *relaxed* 轨迹，LowConfidence/Clashing 不计入）。过滤器用官方 `default_filters.json` 原样。`predict_initial_guess=false`、非 hardtarget 文件、无目标突变、无 K→Lys 改造、无裁剪扩展。

## 5. 考虑过但排除的残基与原因

| 残基 | 排除原因 |
|---|---|
| 全部 404–415（含 R404…T415） | 在包络外（缺口段）；N413 糖链伸入区，occGly 最高 75.7 Å²，A+ 明确排除 |
| 416–420（含埋藏 H418） | 包络外；H418 relSASA 0.022 埋藏，阶段 1 结论已撤回；D416 距糖 7.78 Å |
| 432 Q / 433 H | 包络外（用户决定：H433 定向设计推迟阶段 5；第一代先找独立 de novo 解） |
| L392/L395/V398/I401/L423/I426/G403/G428 | 基本埋藏（relSASA ≤0.145，多数 0.00），作为 hotspot 无表面可接触性 |
| I394（relSASA 0.145） | 包络内最暴露的疏水残基，但低于 0.20 阈值且面积小（28.6 Å²）；不满足"表面残基"，**不作为伪疏水锚填入** |
| E391 / K396（保守集） | relSASA 0.30/0.25 暴露，但与 390/393（E391）和 399（K396）在 helix 上空间聚集；保守集优先空间分散性，二者保留在 broad 集 |
| N422 / R429 / T430（保守集） | coil 残基，官方明确"优先二级结构而非 loop"；R429 虽高暴露（0.621）但位于柔性 coil 末端，保守集不锚定，保留在 broad 集 |
| R427（保守集） | 同上，coil；broad 集保留 |
| 434–481 其余 Domain III 残基 | 包络外；含 C470（断键边缘）、向 Cetux 表位 432–467 过渡区 |
| 糖链 D–H、Fab B–C、His-tag、水 | 非蛋白设计目标/非本构建体，裁剪 PDB 不含 |

## 6. smoke 判读注意（先验写清楚，避免事后移动门柱）

- hotspot 是复合损失的一部分，binder 可能被"更好"的附近位点吸引（官方明示）。3 条轨迹不能用于评估亲和力或成功率，只用于：环境可用性、配置编号正确性、binder 是否几何上落于 B 附近、裁剪边缘是否产生伪影。
- 判读由 [analyze_bindcraft_run.py](../scripts/analyze_bindcraft_run.py) 做几何量化（B 接触残基数、界面落在 B 的比例、迁移、严重 clash、裁剪边缘接触），**completed ≠ success**，是否 pass 官方 filters 看 `Accepted/` 与 CSV，另有 py3Dmol 人工目检。
- 若轨迹反复回避 B，按用户指令先在"编号翻译 / hotspot 化学 / 采样数 / 裁剪制备 / 文档记载行为"五类原因中诊断，不改表位、不突变靶点、不上 hardtarget。
