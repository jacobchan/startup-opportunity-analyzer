## Context

R2 当前结构: 3 个 agent (`market_analyst` / `competitor_researcher` / `finance_analyst`) 各用一把 `ChallengeTool` (限 3 次) kickoff 一次,prompt 是同一个 `round2_challenge` 任务 (tasks.yaml 里 `agent` 字段硬编码为 `market_analyst`,实际通过 `_get_agent(agent_name, tools_override=...)` 替换)。kickoff 后引擎扫 `Challenge` 表里 issuer=该 agent 的新行塞进 `state.r2_challenges`,然后 `r2_completed_agents.append(...)` + checkpoint。R3 把 `r2_challenges` 当 JSON 字符串塞进 strategy_advisor 的 prompt extras。

`ChallengeTool` 当前只有 `_run(target, claim, reason)`,写完就返回。`storage` 里已有 `update_challenge_response()` 但无调用点;`events.py` 已有 `on_challenge_responded` 但无调用点;`protocol.py` 已有 `Verdict.{ACCEPTED,REJECTED,MODIFIED}` 但无调用点;前端 `ChallengeLog.tsx` 已经在 `responses` 上做了 find + 渲染,只缺数据。

恢复机制: `EngineState` 用 `r2_completed_agents` 决定 R2 哪些 agent 已跑过,resume 时按 `if name in r2_completed_agents: continue` 跳过。本次升级要再加一层细粒度:**R2-B 也要对每个被挑战的 agent 单独记录"回应完成"**,并且对**每个挑战**记一条 "resolved" 标记,这样能精准续跑。

## Goals / Non-Goals

**Goals:**
- R2 产出完整的辩论: 发起 (R2-A) + 回应 (R2-B),回应必须写入 `Challenge.response / verdict / resolved_at`
- 裁决语义由被挑战 agent 自决: accepted / rejected / modified,可选 `no_response` 兜底
- R3 prompt 拿到按裁决分组的挑战,要求 `strategy_report.key_risks` 至少引用 1 个 accepted/modified 挑战
- 现有 resume 协议不破坏,R2-B 中途崩溃能继续回应剩余的挑战
- 前端 ChallengeLog 已有 `challenge.responded` 渲染,本次只需让后端发出对应事件
- 每次 run 成本 + 时长增加 ≤ 25%

**Non-Goals:**
- 不做 AI 裁判 (LLM 二次打分),裁决由被挑战方产出
- 不做多轮辩论 (R2-B 单回合就停,后续由 R3 战略汇总)
- 不改 R1 / 现有 R2-A 流程的 agent 集合或顺序
- 不引入新数据库表 / 字段 / 外部依赖
- 不动 CLI (hierarchical) 模式,该模式本就不走 R2-A/B

## Decisions

**D1. ChallengeTool 扩为"发起 + 回应"二合一**

`ChallengeTool` 增加两个动作:
- `list_open_challenges(target: str)` —— 读取 run_id 下 `target == self.issuer AND response IS NULL` 的挑战,返回 `[{challenge_id, issuer, claim, reason}]`。**不消耗 max_challenges**
- `respond(challenge_id, response, verdict)` —— 调用 `update_challenge_response()`,verdict ∈ `accepted|rejected|modified`。**不消耗 max_challenges**

发起动作 `challenge(target, claim, reason)` 行为完全不变,仍受 `max_challenges=3` 限制。

工具描述同步更新,告知 LLM 这是一把"既能宣战也能回应"的工具。

**D2. R2 拆为 R2-A + R2-B**

`run_round2()` 内部分两阶段:
- R2-A: 沿用现有循环,3 个 agent 各自 kickoff 一次 + checkpoint
- R2-B: 收集 R2-A 产出的所有 challenge,按 `target` 分组,依次为**每个有被挑战记录的 agent** 跑一次 kickoff
  - prompt 模板: `round2_respond` (新增),注入 `open_challenges_for_<agent>` 列表
  - 工具: R2-B 专属 `ChallengeTool(issuer=target_agent, max_challenges=0)`,把发起动作彻底禁掉 (max_challenges=0 → 任何发起都 RuntimeError)
  - kickoff 后扫 `Challenge` 表,把该 target 原本 `response IS NULL` 的全部填 `response/verdict/resolved_at`(被 LLM 调 respond 工具的会真填,LLM 没调的将标 `verdict='no_response'`)
  - 每填一条就 emit `challenge.responded` 事件
  - 全部填完才 checkpoint + `r2_completed_agents` 推入该 agent

如果某个 agent 在 R2-A 阶段没被任何人挑战,跳过该 agent 的 R2-B。

**D3. R2-B 顺序: 按 target agent 的字典序**

3 个候选 target 排好固定顺序 (market_analyst → competitor_researcher → finance_analyst),保证 resume 行为可预测;同时所有 SSE 消费者看到的 agent.start 顺序也是确定的。

**D4. 状态与恢复**

`EngineState` 新增 `r2_resolved_challenge_ids: list[str]` 字段。R2-B 中每 `respond` 成功一个就 append,checkpoint。

Resume 协议在 R2-B 内:
- 重新拉 `Challenge` 表里 response IS NULL 的所有挑战(以 DB 为准,不依赖 state 字段)
- 已 resolved 的从 open 集合里剔除
- 然后按 D3 顺序,只对"还有未回应挑战"的 target 跑 kickoff

新增 `r2b_completed_targets: list[str]` 字段(类似 `r2_completed_agents`),控制"已经完整回应过的 target 不重跑"。

**D5. R3 报告增强**

`strategy_report` 任务的 expected_output JSON 增加两个新字段:
```json
{
  "challenge_disposition": {
    "accepted": ["挑战 id 列表 + 短摘要"],
    "rejected": ["..."],
    "modified": ["..."],
    "no_response": ["..."]
  },
  "key_risks": ["... 至少 1 条必须显式 cite 一个 accepted/modified 挑战的 id"]
}
```

extras 注入:
```
以下是 4 个 R1 agent 的输出: {r1_json}

以下是 R2 交叉辩论的处置结果(已按裁决分组):
{challenge_disposition_json}

必须在 key_risks 中显式引用至少 1 个被接受 (accepted) 或被修正 (modified) 的挑战的 challenge_id。
```

`StrategyReportOutput` Pydantic 模型同步加字段(下游校验用,prompt 仍是描述驱动)。

**D6. 事件与前端**

事件类型沿用现有 `challenge.responded` 字段,本次接通:
- 前端 `ChallengeLog.tsx` 已能渲染 response + verdict,无需改
- 新增前端 `EvidenceReport.tsx` 在最终报告区下方一个"关键辩论回顾"section,展示 `challenge_disposition.modified` 中的所有挑战 + 修改后结论

**D7. tasks.yaml 设计**

- `round2_challenge` (R2-A) 保持不变
- 新增 `round2_respond`: description 模板用 `{open_challenges_for_me}` 占位,prompt 告知 LLM 你被谁挑战、必须用 respond 工具逐条回应
- 引擎在 R2-B 用 `_build_task_with_extras` 把 open 列表 inline 注入 description(对齐现有 R1 risk_reviewer 的模式)

**D8. 不改的事项**
- `Challenge` 表结构 (字段已预留)
- 仓储层 `update_challenge_response()` (已存在)
- 事件总线 API
- LLM 模型选择
- CLI hierarchical 入口

## Risks / Trade-offs

[R1] **R2-B 中 agent 永远不调 respond 工具** → 兜底:kickoff 结束后扫 `response IS NULL` 的挑战,自动 `verdict='no_response'`,不阻塞流程。R3 报告里这些会被列在 `no_response` 桶里,前端灰色显示。
   **Mitigation**: prompt 写"必须为每条挑战调用 respond 工具,否则视为弃权";no_response 计数埋点,如果某次 run 出现 > 50% no_response,降级提示"建议人工审视"。

[R2] **R2-B 增加 3 次 LLM 调用,延迟和成本上升** → 接受。已对齐决策(cost +25% 上限),且该成本换"报告可信度"是高杠杆。
   **Mitigation**: R2-B 上下文只塞"跟自己相关的挑战",prompt 比 R2-A 小很多。

[R3] **裁决语义模糊: `modified` 和 `accepted` 边界** → R3 报告 prompt 显式约定: `modified` = 接受挑战但给出修正后结论; `accepted` = 接受挑战并撤回原结论(等价于自己否定自己,实际少用);`rejected` = 不接受。LLM 在 R2-B 的 system prompt 里会拿到这条规则。

[R4] **现有 `tasks.yaml.round2_challenge` 的 `agent: market_analyst` 硬编码是历史遗留** → 引擎用 `_get_agent(agent_name, tools_override=...)` 覆盖,R2-A 实际跑三个 agent 不受影响。本次不动它(避免无关 diff),但 tasks.md 里加一条"待清理"备注。
   **Mitigation**: 后续清理在独立 PR 做。

[R5] **Resume 时重复处理 challenge** → 状态以 DB 为准(state.r2_resolved_challenge_ids 仅做加速,启动时重算)。Kickoff 前的过滤用 `response IS NULL` 而不是 `challenge_id NOT IN resolved_ids`,保证幂等。

[R6] **前端 ChallengeLog 已经有渲染但 reports section 没加 "挑战修正"** → 单独动 EvidenceReport.tsx,低风险。
   **Mitigation**: 写测试验证 R3 报告里出现 `challenge_disposition` 字段 + 至少 1 个 accepted/modified 引用。
