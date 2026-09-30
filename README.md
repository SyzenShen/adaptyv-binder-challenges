# EGFR pH-switch binder — Anthropic × Adaptyv Challenge 01, Track 3

De novo 单链 minibinder（40–100 aa）设计项目：目标是人 EGFR 胞外区（Domain III 优先）的酸性条件（pH 6.5）结合、中性（pH 7.4）不结合，并尽量兼顾小鼠 EGFR 交叉反应。

**本项目不承诺产生命中、pH 开关或湿实验入选。** 所有计算结果都是 computational evidence；`experimentally_validated` 在无湿实验时恒为 false。

## 当前阶段

阶段 0（规则 / 环境 / 仓库 / 最小项目）— 详见 [STATE.md](STATE.md)。

## 目录

- `MASTER_PROMPT.md` — 总控指令（项目宪法，每次恢复任务先读它和 STATE.md）
- `configs/` — 已核实的比赛参数（`competition.json`）与预算（`budget.yaml`，当前 paid_budget=0）
- `scripts/` — 流水线脚本（目前仅有提交序列格式校验）
- `notebooks/` — 最薄 Colab 入口（阶段 2）
- `data/raw|processed|inbox/` — 原始目标文件、处理结果、云端产物回传收件箱（大文件不进 git）
- `results/`、`reports/`、`submission/`、`tests/`
- `RUNBOOK.md` / `DECISIONS.md` / `HUMAN_ACTIONS.md` / `ASK_SUPERVISOR.md`

## 快速检查

```bash
python3 -m unittest discover -s tests -v   # 零三方依赖，系统 Python 3.10 可跑
```

## 证据分级（禁止混用）

| 标记 | 含义 |
|---|---|
| software_test_passed | 代码单元测试通过 |
| model_run_completed | 模型真实运行完成（有日志/产物） |
| computational_filter_passed | 通过计算筛选，不代表真实结合 |
| experimentally_validated | 湿实验验证（本项目恒为 false） |

pLDDT/PAE/ipTM/ipSAE/自洽性均不是 KD，也不能证明 pH 切换。
