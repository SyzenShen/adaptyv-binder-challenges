# 阶段 1 报告：目标准备、残基映射与表位候选

生成时间：2026-09-30（CEST）。状态：computational_filter_passed（计算分析完成；无湿实验）。
所有输入文件 URL/SHA256 见 [targets.manifest.json](../data/raw/targets.manifest.json)。

## 1. 输入与校验

| 文件 | 来源 | 字节 | SHA256（前 16 位） |
|---|---|---|---|
| P00533.fasta | rest.uniprot.org/uniprotkb/P00533.fasta | 1328 | 684e2da1f3ef05d0 |
| Q01279.fasta | rest.uniprot.org/uniprotkb/Q01279.fasta | 1329 | 92bffc461d90e034 |
| 6ARU.cif | files.rcsb.org/download/6ARU.cif | 1548867 | 6cb216f09a7af6ea |

下载脚本 [download_targets.py](../scripts/download_targets.py)，幂等，重跑校验哈希。

## 2. 6ARU 结构实测内容

- 标题：*Structure of Cetuximab Fab mutant in complex with EGFR extracellular domain*（X 射线，3.2 Å）。
- 链组成：A = EGFR ECD（实体 1）；B = Cetuximab 突变轻链；C = 突变重链 Fab；D–H = 糖链（Man5GlcNAc2、GlcNAc2、GlcNAc）。
- **无发表文献引用**（PDB 标注 "To Be Published"）；引用口径只能写 PDB ID。
- chain A 构建体 = UniProt P00533 第 25–640 位（616 aa）+ C 端 His6 标签（label 617–622）。
- 与 UniProt 的两处 conflict（`_struct_ref_seq_dif` 原样记录）：
  - label 516 / UniProt **N540K**（PDB 为 K，UniProt 为 N）
  - label 610 / UniProt **E634R**（PDB 为 R，UniProt 为 E）
- 编号关系（由 `_pdbx_poly_seq_scheme` + `_struct_ref_seq` 推导，非硬编码）：
  **UniProt = label_seq_id = auth_seq_id = PDB 编号**，恒等偏移 +24（即 auth n ↔ UniProt n+24）。无插入码。

## 3. 比赛构建体验证

- 比赛页 human 构建体声明：P00533-1 第 25–645 位，621 aa。
- [verify_competition_construct.py](../scripts/verify_competition_construct.py) 重新抓取比赛页并提取序列，与本地 UniProt 25–645 切片**逐字符一致**（621/621，见 [competition_construct_check.json](../data/processed/competition_construct_check.json)）。
- 注意：6ARU 构建体只到 UniProt 640，**比赛构建体多出的 641–645（GPKIPS）在结构中不存在**，属于 not_in_construct。

## 4. 残基映射表（residue_map.csv）

[build_residue_map.py](../scripts/build_residue_map.py) 输出 621 行（UniProt 25–645），列含：
species / uniprot_pos / uniprot_aa / construct_pos / in_pdb_construct /
pdb_label_asym / pdb_label_seq_id / pdb_auth_asym / pdb_auth_seq_id / pdb_ins_code /
pdb_aa / pdb_vs_uniprot / coord_status / disulfide_partner_uniprot /
glycan_observed_chain / n_glyc_sequon。

关键统计（meta 见 [residue_map.meta.json](../data/processed/residue_map.meta.json)）：

- 有坐标：609/616（构建体内）；缺失密度：UniProt 25–27（N 端）、637–640（C 端）。
- 641–645 不在 PDB 构建体中（上节已述）。
- 观察到的 N-糖基化（`_struct_conn` 共价连接）：**N352、N361、N413、N444**（4 个，全部位于 Domain III）。
- UniProt 全序列 N-糖基化 sequon（N-X-S/T，X≠P）共 11 个：128, 175, 196, 352, 361, 413, 444, 528, 568, 603, 623。结构只解析出 4 个糖链；**未解析不等于无糖基化风险**。
- Domain III（310–481）二硫键：C311–C326、C329–C333、C337–C362 全部域内；**C470–C499 跨界**（C499 在 Domain IV），裁剪时需注意。

## 5. 人鼠序列比对（暂定，PROVISIONAL）

[align_species.py](../scripts/align_species.py)：BLOSUM62、全局比对、gap open −10 / extend −0.5，
human 25–645 对 mouse Q01279 全长（**官方 mouse 构建体未知，HUMAN_ACTIONS A2 待定**）。

- 比对得分 2788.0；**无 gap**；identical 551 (88.7%)、conservative 35、nonconservative 35。
- 结果 [human_mouse_alignment.csv](../data/processed/human_mouse_alignment.csv) 每行一个人类构建体残基。
- 限制：mouse 边界以 Q01279 全长近似，非官方构建体；结论仅供表位选择参考。

## 6. Domain III 表位候选

域边界采用 EGFR ECD 结构共识（UniProt 坐标）：I 25–165、II 166–309、**III 310–481**、IV 482–621。
[analyze_epitopes.py](../scripts/analyze_epitopes.py) 对 Domain III 全部 172 个残基计算：
到 Cetuximab Fab（B/C）最小距离、到糖链（D–H）最小距离、到其他结构域最小距离、人鼠保守类别。

候选 patch 筛选条件（记录于 meta）：连续 ≥10 残基、有坐标、距 Fab ≥ 8 Å、距糖链 ≥ 6 Å、人鼠 identical/conservative。

| ID | UniProt 区间 | 长度 | His | Asp/Glu | Cys（二硫键） | 人鼠非保守位点 | 距 Fab 最小 | 距糖链最小 |
|---|---|---|---|---|---|---|---|---|
| EPI_H_1 | 316–343 | 28 | 0 | 5 | 4（C311/C326、C329/C333、C337/C362） | 无 | 12.6 Å | 6.6 Å |
| EPI_H_2 | 385–403 | 19 | 0 | 4 | 0 | 无 | 12.8 Å | 7.4 Å |
| EPI_H_3 | 416–431 | 16 | **1（H418）** | 3 | 0 | 无 | 9.1 Å | 7.8 Å |
| EPI_H_4 | 447–460 | 14 | 0 | 3 | 0 | 无 | 8.6 Å | 7.5 Å |

补充说明：

- 4 个 patch 在 Q01279 比对下**全部 identical/conservative，无非保守位点**（鼠交叉反应的计算层面障碍低，但 mouse 构建体未官方确认）。
- EPI_H_3 含 H418——Domain III 表面唯一直接位于候选 patch 内的 His；是 pH 开关假设的天然候选位点（仅为几何事实，不构成 pH 证据）。
- EPI_H_1 富含 Cys 与二硫键，结构刚性高，对 minibinder 对接是双刃剑（稳定但可及性/结合面受限）。
- 所有 patch 距 Cetuximab Fab ≥ 8.6 Å，不与已知抗体表位重叠，满足 de novo 表位要求。
- 完整 ECD 遮挡：Domain III 在 tethered/extended 两种 EGFR 构象中均为配体可及面，**预期遮挡风险低**；这是文献共识而非本项目结构计算结果，阶段 4 完整 ECD 复核时再验证。

结构视图：[target_view.html](target_view.html)（NGL，浏览器打开，需联网加载 RCSB 6ARU）。

## 7. 裁剪边界建议

- 推荐生成用 target：**Domain III，UniProt 310–481（auth 286–457），172 残基**，去掉 Fab/糖链/其他域，保留全部域内二硫键（C311–C326、C329–C333、C337–C362）。
- C470–C499 跨界二硫键在裁剪后断裂。若最终 hotspot 选 EPI_H_1/2/3（均 ≤ 431），C470 距结合面 ≥ 39 个残基，且裁剪结构在生成工具中仅作固定几何模板，断裂可接受；**不做**为跑通而随意删残基之外的改动。若后续需要完整 C 端稳定性，可扩展到 310–499（把 C499 含进来）。
- 证据局限：3.2 Å 分辨率；6ARU 是抗体复合物构象；只解析出 4/11 糖链；mouse 比对暂定。

## 8. 测试

见 tests/：序列长度与来源一致、映射往返一致、残基身份匹配、无重复编号、hotspot（各 patch 端点）确有坐标。

## 9. 科学确认点 A（等待批准）

两套方案，**推荐方案 1**：

**方案 1（推荐）— 表位 EPI_H_2 + EPI_H_3 联合 hotspot，裁剪 Domain III（310–481）**
- hotspot 残基（UniProt）：385–403 与 416–431 两段（BindCraft 热点可按这两段指定）。
- 理由：位于 Domain III 中部、无 Cys 简化 binder 对接、人鼠全保守、H418 在 EPI_H_3 内为后续 pH 假设留位、距已知抗体表位远（≥ 9 Å）。
- 主要风险：两段不连续，binder 需同时或择一接触；H418 是否真参与 pH 开关属阶段 5 待验证假设，当前仅为几何事实。

**方案 2（备选）— 表位 EPI_H_1，裁剪 Domain III（310–481）**
- hotspot 残基：316–343。
- 理由：最大连续暴露面（28 aa）、人鼠全保守、距 Fab 最远（12.6 Å）。
- 主要风险：4 个 Cys、3 对二硫键使结合面刚性且拓扑复杂，minibinder 可及性可能较差；距 N352 糖链较近（6.6 Å）。

未经确认不启动针对表位的生产计算（阶段 2/3）。
