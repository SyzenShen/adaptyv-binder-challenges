---
alwaysApply: true
---

# EGFR pH-switch 项目规则（始终生效）

- 每次恢复或开始任务前，先读项目根目录的 MASTER_PROMPT.md 与 STATE.md，按其中的阶段、约束与“下一动作”执行。
- 只记录真实执行结果：区分 software_test_passed / model_run_completed / computational_filter_passed / experimentally_validated；本项目无湿实验，最后一项永远为 false；未计算指标写 null/NA 与原因，禁止填 0 或推测。
- 候选序列只能来自实际运行并记录来源的生成/设计工具；synthetic_fixture 只允许放在 tests/fixtures，禁止进入 results/ 或 submission/。
- paid_budget 未获明确批准前保持 0；付费、公开仓库、正式提交前必须停下等待用户确认。
- 每个大阶段结束：更新 STATE.md，运行测试，git commit 并 push，且查询远端确认提交存在；push 失败标记 PUSH_BLOCKED，不得进入下一大阶段。
- 提交包（submission/）中不得包含 MASTER_PROMPT、项目规则、聊天记录或任何指令性文字。
