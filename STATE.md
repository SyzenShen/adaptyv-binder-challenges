# STATE — 项目状态

最后更新：2026-09-30 20:29 CEST (UTC+2) ｜ 阶段：**0 已交付（本地 commit + 远端核实通过）**；剩余阻塞项为 A2 mouse 构建体与 A3 注册资格

## 总体里程碑

| 阶段 | 状态 | 说明 |
|---|---|---|
| 0 规则/环境/仓库/最小项目 | ✅ 完成（push 已核实） | 远端 main @ 9ff9d43 |
| 1 目标/映射/表位候选 | ⏳ 未开始 | |
| 2 云端 smoke test | ⏳ 未开始 | |
| 3 小批次生成与筛选 | ⏳ 未开始 | |
| 4 双物种复核 / 完整 ECD | ⏳ 未开始 | |
| 5 pH 假设与有限重设计 | ⏳ 未开始 | |
| 6 新颖性/组合/人工终审 | ⏳ 未开始 | |
| 7 冻结与提交包 | ⏳ 未开始 | |

截止（已核实，2026-09-30 页面）：**2026-10-04 23:59 AoE = 2026-10-05 11:59 UTC**；内部目标 10-04 18:00 Europe/Berlin。

## 阶段 0 已完成（真实执行）

- 本机环境实测：macOS 15.6 / Intel x86_64 / i7-9750H 6C12T / 32GB RAM / 磁盘可用仅 27.5GB / 无 CUDA（AMD 5300M 4GB 不可用于模型）/ Python 3.10.11(python.org) / git 2.50.1 / gh 2.87.3 / Homebrew 7.0.6 / 无 conda。详见 [environment_audit.md](reports/environment_audit.md)。
- 官方来源核实（S1/S2 比赛与 EGFR 页、Terms、S10 新颖性博客、S11 Colab FAQ、S13/S14 TRAE 文档，及 S6/S7/S9/S12 仓库 HEAD 与 S3/S4/S5 端点连通性）：见 [sources_register.md](reports/sources_register.md)、[competition_rules.md](reports/competition_rules.md)。
- 目录骨架、7 个状态文件、`configs/competition.json`、`.gitignore`、TRAE always-apply 项目规则（`.trae/rules/egfr-project.md`）。
- 最小流水线代码 `scripts/seqvalidate.py` + `tests/test_smoke.py`（系统 Python 12/12 通过；`.venv` 下 pytest 12/12 通过）。
- 本地 git 仓库初始化，首个 commit **be3359b35a78032a861ee05525948ae214339d58**（分支 main，26 个文件，已做暂存体积/密钥检查）。
- 隔离分析环境 `.venv`（156MB，不入库），精确版本锁定于 configs/requirements-lock.txt：biopython 1.88 / pandas 2.3.3 / numpy 2.2.6 / PyYAML 6.0.3 / requests 2.34.2 / pytest 8.4.2。

## 当前 Blockers（真实阻挡）

1. ~~PUSH_BLOCKED~~ **已解除（2026-09-30）** — 用户提供了已创建的私有仓库 `https://github.com/SyzenShen/egfr-binder-challenge.git`；push 成功，`git ls-remote origin main` 返回 `9ff9d436d32fcdcb49ec11bab78d4adf2f9ba5eb` 与本地 HEAD 一致，仓库页面 HTTP 200。注：`gh` keyring token 仍失效（不影响 HTTPS push；后续若需 `gh api` 操作再做 A1 的 `gh auth login`）。
2. **MOUSE_CONSTRUCT_UNKNOWN** — 官方 EGFR 页 Mouse EGFR 标签在静态 HTML 与交互式浏览器中均为空面板，未给出 mouse UniProt isoform / 构建体边界 / 序列；不得照搬 human 25–645 或自行假定 Q01279 切片。需登录后查看或向 Proteinbase Slack 询问（A2）。
3. **ELIGIBILITY/REGISTRATION_PENDING** — Terms §3.1 排除中国等地区的法定居民；Track 3 需在 Proteinbase 注册。需本人确认资格并注册（A3），这是后续一切提交的前提。
4. **DISK_TIGHT** — 本地容器仅 27.5GB 可用。模型权重/数据集一律走云端，本地只放轻量产物；必要时人工清理磁盘（A4，非阻塞）。

## 依赖

- 阶段 1（不依赖人工，可先行）：UniProt/RCSB 下载（端点已验证 200），需要网络与 ~少量磁盘。
- 阶段 2：需要本人登录 Colab、授权 Drive 结果目录；付费必须先批准。
- 远端备份：已完成（origin = 用户提供的私有仓库）。

## 下一动作（按优先级）

1. ~~A1 gh 重新认证~~ → push 已通过用户提供的仓库完成；gh token 失效仅影响 `gh api` 类操作，非阻塞。
2. 启动阶段 1 中不依赖 mouse 官方构建体的部分：human P00533-1 序列与 6ARU mmCIF 下载、SHA256、初步解析与残基映射（mouse 部分留到 A2 回复后补齐）。
3. A2（mouse 构建体）/A3（资格+注册）为用户侧异步动作，不阻塞本地分析，但 A2 阻塞双物种复核设计、A3 阻塞最终提交。

## 批准记录

- 无付费/公开/提交类批准。paid_budget=0。
