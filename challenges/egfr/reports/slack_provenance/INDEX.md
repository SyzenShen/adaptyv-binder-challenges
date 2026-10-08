# Slack 凭据索引（official competition Slack 截图）

创建：2026-10-01。规则：本目录只放用户从**官方比赛 Proteinbase Slack** 获取的原始截图/导出（不改写、不重排、不 OCR 替换原件）。这些信息来自 Slack，**不得**表述为来自 Proteinbase 网站。截图缺失时，相关结论在仓库中一律保持 `USER_PROVIDED_OFFICIAL_COMPETITION_SLACK` + provenance `PENDING`，不得升级为"已独立核实"。

状态：**截至 2026-10-01，用户尚未提供任何截图文件（本目录除本索引外为空）。** 用户 2026-10-01 指令文件为文本转述，不能代替原始截图。

| ID | 事实主张（转述） | 期望截图文件名 | 截图文件 | 入档状态 | 影响的产物 |
|---|---|---|---|---|---|
| SL01 | mouse EGFR 实验构建体为 Q01279 残基 25–647（623 aa） | `SL01_mouse_construct_YYYY-MM-DD.png` | — | **PENDING** | [human_mouse_ecd_alignment.csv](../../data/processed/human_mouse_ecd_alignment.csv)、DECISIONS D-009；阻塞正式 mouse-target 验证（不阻塞 human smoke） |
| SL02 | C 端构造顺序约 design–短柔性 linker–GFP11–柔性 linker–TwinStrep；linker 序列/长度未公开 | `SL02_cterm_construct_YYYY-MM-DD.png` | — | **PENDING** | [assay_metadata.md](../assay_metadata.md) §2.1；candidate_metrics.json linker=null |
| SL03 | 组织方建议 paratope 尽量放在 N 端一侧（小 binder 尤其） | `SL03_paratope_nterm_YYYY-MM-DD.png` | — | **PENDING** | assay_metadata §2.2/§3；candidate_metrics 排名指标 |
| SL04 | GFP11 split-GFP 互补用于表达定量；表达为独立评估轴 | `SL04_splitgfp_expression_YYYY-MM-DD.png` | — | **PENDING** | assay_metadata §2.3 |
| SL05 | EGFR ECD 在 HEK293 表达、带 human-type 糖基化 | `SL05_hek293_glycosylation_YYYY-MM-DD.png` | — | **PENDING** | [glycan_epitope_audit.md](../glycan_epitope_audit.md) |
| SL06 | 低 pH 用 MES 替换 HEPES；pH 比较 6.5 vs 7.4 | `SL06_mes_ph_YYYY-MM-DD.png` | — | **PENDING** | assay_metadata §2.5 |
| SL07 | 标准缓冲液约 150 mM NaCl、Tween-20、3 mM EDTA（Tween 浓度未给） | `SL07_buffer_edta_YYYY-MM-DD.png` | — | **PENDING** | assay_metadata §2.6 |

截图要求：包含 Slack 频道名、发送者、日期时间与完整消息；放入本目录后把文件名回填"截图文件"列、状态改为 `SCREENSHOT`，并同步更新 assay_metadata.md 与 DECISIONS D-009（SL01）。拿不到原件的条目降级为"用户转述/未证实"并在相关报告中明示。

对应人工动作：[HUMAN_ACTIONS.md A6](../../HUMAN_ACTIONS.md)。
