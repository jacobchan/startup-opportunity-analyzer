# 系统架构说明

> 本文档深入讲解创业机会分析系统的设计思路、实现细节与演进方向。
> 供项目参与者理解"为什么这样设计"以及"每个部分做了什么"。
>
> 最新的架构决策见 [deliberation_engine.md](deliberation_engine.md)，本文件是 CLI 模式（hierarchical）的历史说明。

## 一、系统全貌

一句话概括：**用户输入一个创业方向描述，系统派 5 个 AI 角色各司其职去调研（市场、竞品、财务、风险），最后由一位"战略顾问"汇总出一份 Go/No-Go/Conditional-Go 评估报告。**

CLI 走 hierarchical 单 Crew 模式；web 端走 3 轮 deliberation 模式。两种入口共享同一份 `agents.yaml` + `tasks.yaml` 配置。

### 1.1 两种执行入口

| 入口 | 文件 | 模式 | 用途 |
|------|------|------|------|
| CLI | `python -m src.crew "..."` | hierarchical 单 Crew | 命令行一次性跑，输出到终端或文件 |
| Web | `POST /runs` | 3 轮 deliberation | SSE 实时推送 + 历史持久化 + 断点续跑 |

两种入口共用 5 个 Agent 角色和 `tasks.yaml` 中的 task 描述。

### 1.2 CLI 模式（hierarchical）

```
用户输入                      5个Agent协作                              最终输出
"AI客服平台"  ─────►  [市场] [竞品] [财务] [风险] ──┬─► [战略汇总(Manager)]  ─────►  JSON报告
                              └──►──►──►──►  (context依赖链)
```

Manager（`strategy_advisor`）调度 4 个 Worker 跑完 `market_analysis` / `competitor_analysis` / `finance_analysis` / `risk_review`，由 `context` 字段自动注入前序输出。所有 Worker 输出为结构化 JSON，最终决策报告也是 JSON Schema 格式。

运行一次约消耗 60-100K tokens（多了财务建模），成本 $0.7-1.2，耗时 12-18 分钟。

### 1.3 Web 模式（3 轮 deliberation）

```
                      DeliberationEngine (stateful + checkpointed)
                                    │
        ┌──────── R1 ─────────┐    ┌┴─────── R2 ─────────┐
        │  market              │    │  market (challenge)   │
        │  competitor          │    │  competitor (challenge)│
        │  finance             │    │  finance (challenge)   │
        │  risk (depends on 3) │    │                       │
        │   ↓ checkpoint       │    │   ↓ checkpoint        │
        └──────────────────────┘    └───────────┬───────────┘
                                               ↓
                                ┌────────── R3 ──────────┐
                                │  strategy_advisor       │
                                │   ↓ checkpoint          │
                                │  → final report         │
                                └─────────────────────────┘
```

每完成一个 agent 立即 checkpoint 到 `Run.deliberation_state`，崩溃后调 `POST /runs/{id}/resume` 从下一个 agent 继续。

## 二、目录结构与每个文件的作用

```
startup-opportunity-analyzer/
├── src/                          # 核心代码
│   ├── crew.py                   # CLI 入口：StartupAnalyzerCrew (hierarchical 模式)
│   ├── schemas.py                # 各 Agent 输出的 Pydantic 模型（Schema 定义）
│   ├── __init__.py
│   ├── config/
│   │   ├── agents.yaml           # 5 个 Agent 的角色定义（role/goal/backstory）
│   │   ├── tasks.yaml            # 5+1 个 Task 的任务描述（含 JSON Schema）
│   │   └── settings.py           # 环境变量（LLM 模型、API Key）
│   ├── deliberation/             # Web 模式：3 轮 deliberation 引擎
│   │   ├── engine.py             # DeliberationEngine（核心）
│   │   ├── state.py              # EngineState（Pydantic，可序列化）
│   │   ├── checkpoint.py         # CheckpointStore（SQLite 持久化）
│   │   ├── rounds.py             # RoundOrchestrator（兼容旧测试）
│   │   ├── evidence.py           # 证据捕获装饰器
│   │   └── protocol.py           # ChallengeDraft / Verdict
│   ├── tools/
│   │   ├── search_tool.py        # Serper 搜索工具
│   │   ├── web_scraper.py        # 网页抓取工具
│   │   └── challenge_tool.py     # R2 交叉挑战工具
│   ├── storage/                  # SQLite 持久化
│   │   ├── db.py                 # 引擎 + 轻量级迁移
│   │   ├── models.py             # Run / Evidence / Challenge ORM
│   │   └── repository.py         # CRUD 封装
│   └── web/                      # FastAPI 应用
│       ├── app.py                # create_app 工厂
│       ├── runner.py             # run_deliberation / resume_deliberation
│       ├── events.py             # EventBus（SSE）
│       ├── run_registry.py       # run_id → EventBus 映射
│       └── routes/               # /runs, /stream, /evidence, /resume
├── frontend/                     # React + Vite + TypeScript
│   └── src/
│       ├── App.tsx
│       ├── components/           # StartupForm, HistoryList, AgentCard, ...
│       └── lib/                  # sse.ts, types.ts
├── examples/                     # CLI 示例入口
│   ├── analyze_ai_agent.py       # 分析"AI Agent 客服平台"
│   ├── analyze_saas.py           # 分析"产业园区 SaaS"
│   └── output/                   # 生成的报告样例
├── tests/                        # 90 个测试，全套 < 3 秒
│   ├── deliberation/             # 状态机 + 引擎（17 个）
│   ├── web/                      # API 层（19 个）
│   ├── storage/                  # 仓储层
│   ├── tools/                    # 工具层
│   ├── integration/              # 端到端（2 个）
│   └── test_agents.py            # 配置加载
└── docs/
    ├── architecture.md           # 本文件
    ├── design_decisions.md       # 设计决策记录
    ├── deliberation_engine.md    # 引擎架构 + 故障恢复手册
    └── superpowers/              # 历史设计文档
```

## 三、CLI 模式执行流程

以 `python -m examples.analyze_ai_agent` 为例：

### 第 1 步：入口调用

```python
from src.crew import run_analysis
report = run_analysis(
    startup_idea="面向中小企业的AI Agent客服平台...",
    save_to="examples/output/ai_agent_analysis.md",
)
```

### 第 2 步：`run_analysis()` 构建并启动 Crew

```python
def run_analysis(startup_idea, save_to=None):
    analyzer = StartupAnalyzerCrew()
    analyzer._save_to = save_to
    result = analyzer.crew().kickoff(
        inputs={"startup_idea": startup_idea}
    )
    return result.raw
```

### 第 3 步：`@CrewBase` 装饰器自动加载

- `agents.yaml` → `self.agents_config`
- `tasks.yaml` → `self.tasks_config`

### 第 4 步：`@crew` 方法组装

```python
@crew
def crew(self) -> Crew:
    market, competitor, finance, risk, strategy = self.tasks
    risk.context = [market, competitor, finance]
    strategy.context = [market, competitor, finance, risk]

    manager = self.strategy_advisor()
    worker_agents = [
        self.market_analyst(),
        self.competitor_researcher(),
        self.finance_analyst(),
        self.risk_reviewer(),
    ]

    return Crew(
        agents=worker_agents,
        tasks=self.tasks,
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=True,
    )
```

### 第 5 步：生命周期钩子

- `@before_kickoff` — 保存 `startup_idea` 供后续使用
- `@after_kickoff` — 如果设置了 `save_to` 就把报告写入文件

## 四、Web 模式执行流程

以 `POST /runs` 为例：

### 第 1 步：HTTP 创建 run

`src/web/routes/runs.py::create_run_endpoint` 接收 `{"startup_idea": "..."}`，写入 `Run` 行（status=queued），创建 `EventBus`，后台启动 `run_deliberation`。

### 第 2 步：web runner 构造 engine

`src/web/runner.py::_build_engine` 装配：
- 共享 LLM 实例
- 5 个 Agent 的 configs（来自 `StartupAnalyzerCrew` 实例的 yaml 加载）
- 5+1 个 Task 的 configs
- 每个角色的工具列表（market/compet/finance: search+scrape；risk: search；strategy: 无）
- challenge_tool 工厂（用于 R2）

### 第 3 步：engine 跑 3 轮

```
engine.run_round1()  → 4 个 agent → 4 次 checkpoint
  ↓
engine.run_round2()  → 3 个 agent (带 challenge_tool) → 3 次 checkpoint
  ↓
engine.run_round3()  → strategy_advisor → 1 次 checkpoint
```

每轮 `engine.state.current_round` 推进，事件通过 `publisher` 推到 `EventBus`，SSE 流把事件推给前端。

### 第 4 步：断点恢复

`POST /runs/{id}/resume` 重新构造 engine，从 `Run.deliberation_state` 加载 state，根据 `r1_completed_agents` / `r2_completed_agents` 跳过已完成 agent。

详见 [deliberation_engine.md](deliberation_engine.md) 第 5 节"故障恢复手册"。

## 五、5 个 Agent 的分工与工具分配

```
┌─────────────────┬──────────────────────────────┬────────────┬──────────┐
│ Agent           │ 职责                          │ CLI R1     │ Web R1+R2│
├─────────────────┼──────────────────────────────┼────────────┼──────────┤
│ market_analyst  │ TAM/SAM/SOM、增长、用户画像    │ search+    │ R1 + R2  │
│                 │                              │ scrape     │ challenge│
│ competitor_     │ 竞品列表、竞争格局、差异化机会  │ search+    │ R1 + R2  │
│ researcher      │                              │ scrape     │ challenge│
│ finance_analyst │ LTV/CAC 模型、定价、资金需求   │ search+    │ R1 + R2  │
│                 │                              │ scrape     │ challenge│
│ risk_reviewer   │ 多维度风险评估（依赖前三项）   │ search     │ R1 only  │
│ strategy_       │ 汇总输出 Go/No-Go 决策报告     │ —          │ R3 only  │
│ advisor         │                              │            │          │
└─────────────────┴──────────────────────────────┴────────────┴──────────┘
```

## 六、未来改进方向

- [x] 状态化引擎 + checkpoint 写入（v0.2 已完成）
- [x] 断点续跑 API（v0.2 已完成）
- [ ] 证据可追溯闭环（v0.3 计划）
- [ ] LLM 输出质量评估体系（v0.3 计划）
- [ ] 插件化 Agent（v0.4 计划）
- [ ] 历史案例相似度匹配 / RAG（v0.5 计划）
