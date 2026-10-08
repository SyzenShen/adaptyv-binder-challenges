# Cetuximab 距离与编号审计（Stage 1.5 Part D）

生成：2026-10-01。脚本：[audit_geometry.py](../scripts/audit_geometry.py)；原始逐残基数值：[domain3_geometry.csv](../data/processed/domain3_geometry.csv)。

## 1. 编号体系（明确声明，全文一致）

| 体系 | 取值 | 来源 |
|---|---|---|
| UniProt 全长（P00533-1） | 本文一切残基编号的默认体系 | rest.uniprot.org P00533.fasta |
| 6ARU label_asym / label_seq_id | chain A，label_seq_id 1..622 | mmCIF `_pdbx_poly_seq_scheme` |
| 6ARU auth chain / auth_seq_id | A，1..622，无插入码 | 同上；实测 label = auth |
| 换算 | **UniProt = label_seq_id + 24 = auth_seq_id + 24** | `_struct_ref_seq`（entity 1 ↔ P00533，25..640），推导而非假定 |
| 比赛构建体 | UniProt 25..645（621 aa） | 比赛页，逐字符核对通过 |
| 6ARU 构建体 | UniProt 25..640 + C 端 His6 标签（label 617..622） | `_struct_ref_seq_dif` |

## 2. 距离定义与原子选择（复现说明）

- 结构：6ARU（X 射线 3.2 Å）。EGFR = label_asym A；**Cetuximab Fab = label_asym B（突变轻链）+ C（突变重链 Fab）**；糖链 D–H 不参与 Fab 距离。
- 主指标：**最小重原子–重原子距离**（6ARU 全部沉积原子均为非氢原子）。对 EGFR 残基 r，`dFab(r) = min ||a_i − b_j||`，a_i 遍历 r 的全部重原子，b_j 遍历 B/C 全部重原子；并记录最近原子对（残基名+原子名）。
- 对照指标：Cα–Cα 最小距离（同样的链选择）。
- 不是 centroid，不是表面距离，不是溶剂距离。SASA 遮挡（occFab）作为第三维信息单列。
- 阶段 1 报告中的 8.57–12.77 Å 与本次复算**逐值一致**（阶段 1 用的也是全原子 min，本次审计确认其定义正确、无编号错误）。

## 3. 文献功能表位残基编号核对

用户给出的文献残基 Q384/P387/Q408/H409/F412/V417/S418/K443 出自 EGFR 抗体热点综述/Tydings et al. 2024 *Protein Sci* 33:e5141 等引用的 Cetuximab 晶体结构编号，即 **PDB auth 编号（= UniProt − 24）**，不是 UniProt 编号。逐一对账：

| 文献（auth） | UniProt | 实测氨基酸一致？ | dFab 重原子 (Å) | Cα 距离 (Å) | 最近原子对（示例） |
|---|---|---|---|---|---|
| Q384 | 408 | 是（Q） | **3.43** | 6.85 | GLN408.O–C:ASN.ND2 |
| P387 | 411 | 是（P） | 10.75 | 12.48 | PRO411.N–C:ASN.ND2 |
| Q408 | 432 | 是（Q） | **2.60** | 10.23 | GLN432.NE2–C:TYR.OH |
| H409 | 433 | 是（H） | **3.47** | 9.03 | HIS433.ND1–C:TYR.OH |
| F412 | 436 | 是（F） | **3.85** | 9.79 | PHE436.CE2–C:TYR.CE2 |
| V417 | 441 | 是（V） | **3.59** | 7.22 | VAL441.CG2–C:TYR.CD1 |
| S418 | 442 | 是（S） | **3.26** | 7.49 | SER442.OG–C:ASN.ND2 |
| K443 | 467 | 是（K） | **3.39** | 5.46 | LYS467.CE–C:ASP.OD1 |

8/8 氨基酸在 +24 换算后全部吻合，证实编号解释正确。其中 7 个残基侧链与 Fab 直接接触（≤3.9 Å），P411（10.75 Å）属功能表位边缘/间接接触。这与 Cetuximab 表位位于 Domain III 的经典结论一致。

## 4. EPI_H_2 / EPI_H_3 的真实 Fab 距离

| Patch | dFab 重原子 min | 最近残基 | <5 Å 残基 | <8 Å 残基 | Cα min (Å) |
|---|---|---|---|---|---|
| EPI_H_2 (385–403) | 12.77 | 403（G，端缘） | 无 | 无 | 14.54 |
| EPI_H_3 (416–431) | 9.11 | 431（K，端缘） | 无 | 无 | 13.12 |
| EPI_H_1 (316–343) | 12.58 | 340 | 无 | 无 | 15.68 |
| EPI_H_4 (447–460) | 8.57 | 460 | 无 | 无 | 11.96 |

紧邻 EPI_H_3 下游的悬崖：**432 Q（2.60 Å）、433 H（3.47 Å）、435 Q（3.88 Å）、436 F（3.85 Å）** 即在 Fab 界面上；缺口侧 406 L（3.55 Å）、408 Q（3.43 Å，occFab 64 Å²）同样在界面上。即：EPI_H_3 的 K431 与 Fab 接触残基 Q432 仅一个肽键之隔，结合面边缘到 Fab 界面是一个陡峭过渡。

## 5. 结论与边界

1. 阶段 1 的距离计算在编号、链选择与距离定义上**经审计无误**；两个方案的 patch 残基均不与 Cetuximab 直接接触（重原子 ≥8.57 Å、Cα ≥11.96 Å）。
2. 若把 hotspot 扩展到 432–433（为 pH 机制 B 接触 H433），binder 将直接占据 Cetuximab 功能表位（规则未禁止，距离不是优化目标；此条只做几何事实记录）。
3. 6ARU 中的 Fab 是**突变体** Fab；上述是几何距离，不构成对野生型 Cetuximab 竞争关系或结合强度的任何推断。
4. 不以"远离 Cetuximab"作为筛选加分项；新颖性/IP 风险在阶段 6 独立评估。
