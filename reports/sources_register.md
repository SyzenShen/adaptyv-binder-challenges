# 来源登记表（sources register）

规则：比赛网站与当前安装版本官方文档优先于 MASTER_PROMPT；访问失败如实记录。所有访问日期 2026-09-30（UTC/CEST 同日）。

| 编号 | 来源 | 访问方式/状态 | 版本 / commit / 标识 | 相关结论（摘要） |
|---|---|---|---|---|
| S1 | 比赛总页 proteinbase.com/competitions/anthropic-adaptyv-2026 | ✅ WebFetch 200 | 页面（无版本号） | 五周五道题；Track 1/2/3 定义；Challenge 1 Sep28–Oct4；周日 23:59 AoE 关闭；ODC-BY 发表、无现金奖 |
| S2 | EGFR 挑战页 …/challenges/egfr | ✅ WebFetch + 原始 HTML 解析 + 交互浏览器 | 页面（无版本号） | human: P00533-1, 25–645/621aa, Domain III, 6ARU-A；Track3 ≤20；10–250aa；CSV schema；de novo+zero-shot；三目标与排名；**mouse 标签为空面板 → A2** |
| S3 | Human UniProt P00533 | ✅ REST 端点 200（`.fasta`） | 阶段 1 下载后记录 entry version + SHA256 | 端点可用；页面引用 isoform P00533-1；未在阶段 0 落文件 |
| S4 | Mouse UniProt Q01279 | ✅ REST 端点 200（`.fasta`） | 同上 | **仅证明端点存在；是否使用该条目/哪条 isoform 以官方 mouse 信息为准（A2），不得先验采用** |
| S5 | RCSB 6ARU | ✅ Range GET 200 `https://files.rcsb.org/download/6ARU.cif` | mmCIF 完整文件阶段 1 下载并记录 SHA256；结构版本以 RCSB 当时 archive 为准 | 正确路径是 `6ARU.cif`（`.cif.header` 404 是错误路径，已记录） |
| S6 | BindCraft github.com/martinpacesa/BindCraft | ✅ GitHub API | branch `main`，HEAD **7713aa0d0d35**（2026-09-21，“Update Multi_BC_Original.ipynb”），License **MIT**，未归档 | 阶段 2 唯一生产主线；安装时再读 README、`--help` 并锁定 commit（HEAD 不自动等于锁定版） |
| S7 | Boltz github.com/jwohlwend/boltz | ✅ GitHub API | branch `main`，HEAD **b1ebfc46ecf5**（2026-05-29，PR#654 merge），License **MIT** | 阶段 4 独立复核候选；其小分子 affinity 模块不用于蛋白-蛋白 KD |
| S8 | Boltz prediction.md 文档 | ⏳ 排期阶段 4 | — | 复核时按当时文档确认复合物输入与置信度输出字段/量纲 |
| S9 | PROPKA github.com/jensengroup/propka | ✅ GitHub API | branch `master`，HEAD **58ceb7ba5cbf**（2026-07-31），License **LGPL-2.1** | 阶段 5 近似 pKa；只作机制旁证，不据此宣称 pH 切换 |
| S10 | Adaptyv 新颖性博客 adaptyvbio.com/blog/novelty | ✅ WebFetch 全文 | 页面（2026-09 数据口径，PDA ~2000、Proteinbase 3000 binders） | ProteinTyper Level 1–4；序列 ≤30% + 结构低于中等(Level 4)；结构阈值 ≥70%覆盖/TM≥0.8 高、>70%/TM≥0.5 中；抗体看 CDRH3；非官方硬淘汰线 |
| S11 | Colab FAQ research.google.com/colaboratory/faq.html | ✅ WebFetch 全文 | 在线文档（无版本号） | GPU best-effort、可无预警断供；空闲超时/VM 寿命上限不公布且变动；禁止 SSH 代理、保活滥用、多账户；Drive 挂载有配额/超时注意 |
| S12 | uplifting-biomolecular-modeling github.com/anthropics/... | ✅ GitHub API | branch `main`，HEAD **f4f62fa6592a**（2026-09-17 初始公开），License **Apache-2.0** | 仅可选加速；阶段 2 先核兼容性，小样本对比后才允许并入，不得偷换基线 |
| S13 | TRAE 项目规则 docs.trae.cn/ide_rules | ✅ WebFetch 全文 | 在线文档（无版本号） | 项目规则目录 `.trae/rules/`，Markdown + frontmatter；`alwaysApply: true` = 始终生效；支持子目录与 ≤3 层嵌套 → 已创建 `.trae/rules/egfr-project.md` |
| S14 | TRAE SSH 远程 docs.trae.cn/ide_ssh-remote | ✅ WebFetch 全文 | 在线文档（无版本号） | 远端仅支持 Linux（Ubuntu 20.04+/Debian10+/Fedora42/RHEL9），出站 443；学校/付费 GPU 服务器阶段 2 后可切换，复用批处理脚本 |

## 附：其他已核实官方链接

- Terms：https://proteinbase.com/competitions/anthropic-adaptyv-2026/terms ✅ 全文已读（ODC-BY、资格排除、生物安全筛查等见 competition_rules.md §8）
- 提交门户：https://proteinbase.com/competitions/anthropic-adaptyv-2026/submit ✅ HTTP 200（登录后才能实际提交）
- Proteinbase Slack 邀请：https://join.slack.com/t/proteinbase/shared_invite/zt-3evw8fs9z-tU9ItWVvw4ySctUuPvIhLQ ✅（链接取自页面 HTML；加入动作由用户执行，A2）
- ANARCI：github.com/oxpig/ANARCI（抗体注释工具，本项目不走抗体路线，仅登记）

## 失败/缺口记录（不掩盖）

1. Mouse EGFR 官方构建体：静态抓取与交互点击均未取得（站点面板为空）→ MOUSE_CONSTRUCT_UNKNOWN / A2。
2. 选择用的 Claude 设计筛选 prompt：官方明确不提前公开（FAQ 8），无法核实，属预期。
3. Terms §5.3 与 challenge 页截止日期文字不一致（Oct 31 vs Oct 4）→ D-008，按 challenge 页执行并在提交前复核。
