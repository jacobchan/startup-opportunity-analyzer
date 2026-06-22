## 1. 工具与仓储层

- [x] 1.1 在 `src/tools/challenge_tool.py` 把 `ChallengeTool` 重构为支持三个动作:`challenge`、`respond`、`list_open_challenges`,只有 `challenge` 消耗 `max_challenges`
- [x] 1.2 在 `src/storage/repository.py` 新增 `get_unresolved_challenges_for_run(run_id, target=None)` 返回 `response IS NULL` 的挑战列表
- [x] 1.3 在 `src/storage/repository.py` 新增 `mark_unresolved_as_no_response(session, run_id, target)` 把指定 target 下所有 `response IS NULL` 的挑战批量填 `verdict='no_response' / resolved_at=now`
- [x] 1.4 跑 `pytest tests/tools/test_challenge_tool.py`,补三个动作的单元测试(发起/拒绝/respond 失败情形/ list_open)

## 2. 状态模型

- [x] 2.1 在 `src/deliberation/state.py` 的 `EngineState` 新增字段 `r2_resolved_challenge_ids: list[str]` 和 `r2b_completed_targets: list[str]`,default 工厂保证旧 checkpoint 反序列化兼容
- [x] 2.2 在 `src/schemas.py` 的 `StrategyReportOutput` 新增 `challenge_disposition: dict` 字段(下游校验用,Pydantic 不驱动 prompt)
- [x] 2.3 跑 `pytest tests/deliberation/test_state.py` 验证 schema 兼容老 snapshot(老 EngineState JSON 仍能 load)

## 3. tasks.yaml

- [x] 3.1 在 `src/config/tasks.yaml` 新增 `round2_respond` 任务,description 模板含 `{open_challenges_for_me}` 占位 + system 规则说明 accepted/rejected/modified 语义 + 强制 respond
- [x] 3.2 修改 `strategy_report` 任务的 `expected_output` JSON 模板,增加 `challenge_disposition` 4-桶对象,并在 description 末尾追加"key_risks 必须显式 cite 至少 1 个 accepted/modified 挑战"
- [x] 3.3 跑 `tests/test_agents.py` 验证 yaml 仍可被 CrewBase 解析

## 4. 引擎核心:R2-B 子回合

- [x] 4.1 在 `src/deliberation/engine.py` 把 `run_round2` 拆为内部 `_run_round2_issue()` + `_run_round2_respond()`,公共 `run_round2` 串联
- [x] 4.2 实现 `_run_round2_respond()`: 拉 DB 中所有 `response IS NULL` 挑战 → 按 target 分组 → 字典序遍历 target → 对每个有未回应挑战的 target 调一次 `_kickoff_for_response(target, open_challenges)` → kickoff 完调 `mark_unresolved_as_no_response` 兜底 → checkpoint + `r2b_completed_targets.append`
- [x] 4.3 实现 `_kickoff_for_response(target, open_challenges)`: 构造 `ChallengeTool(issuer=target, max_challenges=0)` → 用 `_get_agent(target, tools_override=[...])` 拿 fresh agent(不污染缓存) → 走 `_build_task_with_extras` 注入 `{open_challenges_for_me}` 列表到 `round2_respond` 描述 → 跑 Crew.kickoff
- [x] 4.4 在 `_kickoff_for_response` 后扫 DB,对该 target 新产生 `response IS NOT NULL` 的挑战 emit `challenge.responded` 事件,字段为 `{challenge_id, target, response, verdict}`
- [x] 4.5 实现 resume 时的 R2-B 入口:`_reconcile_r2b_state_from_db()` 从 `Challenge.response IS NULL` 状态反推当前应跑的 target 集合(以 DB 为准,忽略 state 里的 `r2b_completed_targets` 不一致项)
- [x] 4.6 在 `resume()` 的 ROUND_2 分支先调 `_reconcile_r2b_state_from_db()`,再进入 R2-A / R2-B
- [x] 4.7 跑 `pytest tests/deliberation/test_engine.py`,补 5+ 用例:R2-B 三个 target 全跑 / 某 target 无挑战跳过 / R2-B 中途 crash + resume 续跑 / R2-B 完成后 ROUND_COMPLETE / 同一挑战 resume 两次仍幂等

## 5. R3 prompt 注入

- [x] 5.1 在 `run_round3` 内构造 `challenge_disposition_json` 四桶(accepted/rejected/modified/no_response),从 `state.r2_resolved_challenge_ids` + DB `Challenge` 行组装,每桶元素 `{challenge_id, claim, response}`
- [x] 5.2 修改 R3 的 extras 注入,按 system 约定格式把四桶附加到 strategy_advisor prompt
- [x] 5.3 跑端到端 e2e 测试: mock agent factory 在 R2-B 回应出 accepted 一次,断言 R3 收到的 prompt extras 含 `challenge_disposition.accepted[0].challenge_id`

## 6. 事件 / 前端

- [x] 6.1 验证 `src/web/events.py.CrewCallbackAdapter.on_challenge_responded` 的事件 schema 与本次 emit 的字段一致;若需要,在 `on_challenge_responded` 调用点直接构造 dict(走 `_publisher` 即可,不需要新 adapter 方法)
- [x] 6.2 在 `frontend/src/components/EvidenceReport.tsx` 新增 section: 当 `report.challenge_disposition.modified` 非空时,展示"经挑战修正的关键结论",列出 challenge_id + claim + response
- [x] 6.3 跑 `pytest tests/web/` + `cd frontend && npm run build` 确认前端编译通过

## 7. 端到端与回归

- [x] 7.1 跑 `pytest tests/ -q` 全套,确认 90+ 老测试无回归
- [x] 7.2 跑 `ruff check src/ tests/` 无新增 lint 错误
- [x] 7.3 写一个端到端测试(可放 `tests/integration/test_r2_loop.py`): in-memory DB + mock agent factory,R2-A 让 market 发起一条 challenge 指向 finance,R2-B 让 finance kickoff 调用 respond 工具,断言 DB 里 `Challenge.response/verdict/resolved_at` 都填了,R3 prompt extras 含 `challenge_disposition.modified[0].challenge_id`
- [x] 7.4 README 里"3 轮 deliberation"小节增加一句"R2 包含发起 + 回应两个子回合,挑战的接受/拒绝/修正会显式记入最终报告",与代码对齐

## 8. 收尾

- [x] 8.1 手动跑一次完整 run(用 examples/analyze_ai_agent.py 改走 web 入口也行),观察 5 个 R2-B kickoff + 挑战.responded 事件 + R3 报告里有 challenge_disposition
- [x] 8.2 估算本次 run cost / 时长,确认 +25% 上限内,记到 PR description
- [x] 8.3 在 tasks.md 中加一条 follow-up(不在本 PR):"`round2_challenge` 任务的 `agent: market_analyst` 硬编码是历史遗留,后续清理"
