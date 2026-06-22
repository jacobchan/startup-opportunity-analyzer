## Why

R2(交叉挑战)目前的实现只是"单方面宣战" —— 3 个 agent 各自调用 `challenge` 工具写一条记录,被挑战的 agent 根本看不到,更不会回应。`Challenge` 表里的 `response/verdict/resolved_at` 字段、`protocol.py` 里的 `Verdict` enum、`events.py` 里的 `on_challenge_responded` 事件,以及前端 `ChallengeLog.tsx` 里 `challenge.responded` 的渲染分支 —— 全部是预留好的占位,但代码里**零调用点**。结果是 README 和架构图最显眼的"3 轮 deliberation"卖点,实际只跑了一半:用户在挑战日志里看到的是哑记录,R3 报告里也找不到"这个结论是经过挑战被修正的"的痕迹。

## What Changes

- `ChallengeTool` 扩展为可发起 / 可回应 / 可列出"待回应挑战",`max_challenges` 限制只对"发起"生效
- `DeliberationEngine.run_round2` 拆成两个子回合:R2-A(发起,沿用现有逻辑)+ R2-B(被挑战 agent 回应)
- `EngineState` 增加 `r2_resolved_challenges` 字段并在每个挑战被回应后 checkpoint,R2-B 中途崩溃可继续回应剩下的
- `tasks.yaml` 增加 `round2_respond` 任务模板,`round2_challenge` 不变
- R3 报告(`strategy_report`)的 expected_output 增加"挑战处置摘要"字段,prompt 注入按 accepted / rejected / modified / no_response 分组的挑战列表
- 事件流增加 `challenge.responded`(已有,本次接通)
- 前端 `EvidenceReport` 在最终报告区展示"经过挑战修正的关键结论"小节

## Capabilities

### New Capabilities

- `r2-deliberation-loop`: 定义 R2 必须经历的"发起 → 回应"两个子回合、裁决语义、未回应容忍策略、被挑战方工具的契约

### Modified Capabilities

<!-- 项目暂无已发布 spec 目录,首次建能力无需 deltas -->

## Impact

- **代码**:
  - `src/tools/challenge_tool.py` —— 增 respond / list_open_challenges 接口
  - `src/deliberation/engine.py` —— 拆分 R2 子回合,checkpoint 粒度细化到"每个挑战被回应后"
  - `src/deliberation/state.py` —— `EngineState` 新增 `r2_resolved_challenges` 字段
  - `src/storage/repository.py` —— 新增 `get_unresolved_challenges_for_run` / `mark_challenge_unresolved_if_missing` 等
  - `src/config/tasks.yaml` —— 新增 `round2_respond` 任务,`strategy_report` prompt 改写
  - `src/web/runner.py` —— 暂无改动(沿用现有 engine 接口)
  - `frontend/src/components/EvidenceReport.tsx` —— 新增"挑战修正" section
- **数据库**: `Challenge` 表的 `response/verdict/resolved_at` 字段已被预留,无需迁移
- **LLM 行为**:
  - 每次完整运行多 3 次 kickoff(每个被挑战 agent 一次),每次 kickoff 上下文比 R2-A 小(只看跟自己相关的挑战)
  - 估计每次 run 增加 ~$0.15-0.25,总时长从 12-18 分钟延长到 15-22 分钟(+25% 上限)
- **测试**: `tests/deliberation/test_engine.py` 增加 R2-B 控制流测试,`tests/tools/test_challenge_tool.py` 增加 respond 测试
