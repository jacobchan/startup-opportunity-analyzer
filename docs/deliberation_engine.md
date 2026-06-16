# Deliberation Engine

> 状态化的 3 轮 deliberation 编排器，替代了原 `StartupAnalyzerCrew.run_round1/2/3` 的 8 次冷启动模式。

## 为什么需要这个引擎

老的 3 轮实现有个核心问题：每个 round 内的每个 agent 都重新构造一个独立的 `Crew`，调用 `crew.kickoff()`。这导致：

- **8 次冷启动**（R1 跑 4 个 agent + R2 跑 3 个 + R3 跑 1 个），每次都重新解析 yaml、构建 LLM client、加载工具
- **不可恢复** — 任何一步失败（网络抖动、LLM 超时、OOM）都得从头开始，已经消耗的 $0.3-0.5 全部白费
- **不可测** — 单个 round 没法独立测试，必须跑完整 12-18 分钟
- **状态分散** — round 状态在 `RoundOrchestrator`、challenges 在 SQLite、agent outputs 在内存 dict 里

`DeliberationEngine` 把这些收敛成一个有状态、可恢复、可单测的单元。

## 状态机

```
              ┌──────────┐
              │   none   │  ← 新建 run
              └────┬─────┘
                   │ run_round1 (第一遍)
                   ▼
        ┌──────────────────┐
        │     round1       │  ← 4 个 agent 顺序执行
        │  (current)       │    每次完成 → checkpoint
        └────────┬─────────┘
                 │ 全部 R1 完成
                 ▼
        ┌──────────────────┐
        │     round2       │  ← 3 个 agent 顺序执行
        │  (current)       │    每次完成 → checkpoint
        └────────┬─────────┘
                 │ 全部 R2 完成
                 ▼
        ┌──────────────────┐
        │     round3       │  ← 1 个 agent 汇总
        │  (current)       │    完成 → checkpoint
        └────────┬─────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   ┌──────────┐    ┌──────────┐
   │ complete │    │  failed  │  ← 异常被 catch，state 落库
   └──────────┘    └──────────┘
```

`current_round` 字段持久化在 `Run.deliberation_state` JSON 列里。`r1_completed_agents` / `r2_completed_agents` 列表记录每个 round 内已完成的具体 agent — 恢复时跳过这些。

## 关键文件

| 文件 | 作用 |
|------|------|
| `src/deliberation/state.py` | `EngineState` Pydantic 模型 — 可序列化的引擎状态 |
| `src/deliberation/checkpoint.py` | `CheckpointStore` — 把 `EngineState` 持久化到 `Run.deliberation_state` |
| `src/deliberation/engine.py` | `DeliberationEngine` — 3 轮编排 + 缓存 + 恢复 |
| `src/web/runner.py` | `run_deliberation` / `resume_deliberation` — web 层入口 |
| `src/web/routes/resume.py` | `POST /runs/{id}/resume` — HTTP API |

## 公开 API

### 一次性跑完

```python
from src.deliberation.engine import DeliberationEngine

engine = DeliberationEngine(
    run_id=run_id,
    startup_idea="AI Agent 客服平台",
    llm=llm,
    agents_config=agents_config,
    tasks_config=tasks_config,
    tools_map=tools_map,
    challenge_tool_factory=challenge_factory,
    publisher=event_publisher,
    session_factory=get_session,
)
report = engine.run_all()
```

### 断点恢复

```python
# 假设某个 run 在 R1 market_analyst 完成后崩了
# Engine 重新构造时自动从 Run.deliberation_state 加载 state
engine = DeliberationEngine(
    run_id=run_id,
    ... # 其他参数一样
)
report = engine.resume()  # 自动从 R1 的下一个 agent 继续
```

### 通过 HTTP

```bash
# 启动一次新分析
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"startup_idea": "AI Agent 平台"}'

# 崩溃后从断点恢复
curl -X POST http://localhost:8000/runs/{run_id}/resume
```

## 设计要点

### Agent 缓存

`engine._agent_cache` 缓存"无 override"的 Agent 实例。R2 需要给 agent 加 `challenge_tool`，走 `tools_override` 路径**总是构造新 Agent**，不污染 cache。

```python
def _get_agent(self, name, tools_override=None):
    if self._agent_factory_override is not None:
        return self._agent_factory_override(name, tools_override)
    if tools_override is None:
        # 走 cache
        ...
    # Override 路径：fresh Agent，cache 不动
    return Agent(config=..., tools=tools_override, ...)
```

### Checkpoint 频率

**每个 agent 完成后写一次 checkpoint**（不是每轮、不是每步）。权衡：
- 粒度太粗（每轮）：单 round 内 3-4 个 agent 任何一个崩了都得重跑
- 粒度太细（每步）：checkpoint 写入开销大、状态噪声多
- agent 粒度：R1 market 跑完崩了，重启后从 competitor 继续 — 性价比最优

### 失败状态

任何 round 抛异常都会被 `run_all` / `resume` 捕获：
- `state.current_round = "failed"`
- `state.error = repr(exception)`
- 写入 checkpoint
- 重新抛给调用方，由 web runner 发 `run.failed` SSE 事件

下次调用 `engine.resume()` 时会从 `failed` 状态开始重新走（而不是从 `current_round` 上一个 round）— 失败时不重试已经成功的 round。

## 故障恢复手册

### 场景 1：服务 OOM / 进程被 kill

```bash
# 1. 重启服务
uvicorn src.web.app:create_app --factory

# 2. 找到中断的 run_id（前端历史列表里能看到）
# 3. 触发 resume
curl -X POST http://localhost:8000/runs/{run_id}/resume
```

恢复时：
- 已完成的 agent 不重跑
- 完成的 round 不重跑
- 从 `state.current_round` 的下一个未完成 agent 继续
- 最终 SSE 流会发送 `run.complete` 事件，前端如果还连着会自动收

### 场景 2：LLM 持续失败

`Run.status == "failed"`，调用 `POST /runs/{id}/resume`：
- `resume_deliberation` 把状态置回 `running`
- `engine.resume()` 重新走未完成的 rounds
- 如果还是失败，状态再次落库为 `failed`，等下次修好再试

### 场景 3：需要从头开始

目前没有"reset"接口 — 简单办法是删除 run 再创建：
```bash
curl -X DELETE http://localhost:8000/runs/{run_id}
curl -X POST http://localhost:8000/runs -d '{"startup_idea": "..."}'
```

未来可以加 `POST /runs/{id}/reset`。

## 测试

`tests/deliberation/test_state.py` — 状态机 + CheckpointStore 单元测试（7 个）
`tests/deliberation/test_engine.py` — engine 控制流 + 恢复 + 缓存 + 失败处理（10 个）
`tests/web/test_runner.py` — runner 函数层（5 个）
`tests/web/test_resume.py` — HTTP 接口层（5 个）
`tests/integration/test_end_to_end.py` — 端到端（2 个）
