# 多轮辩论 + 证据追踪 Web Demo 设计

> **Status**: Draft v0.1
> **Date**: 2026-06-12
> **Author**: chenqiaofeng
> **Goal**: 把当前"5 Agent 单轮 + Manager 综合"的 CrewAI 实现，升级为"3 轮辩论 + 证据追踪 + Web 可视化"的社区 Demo，明确与「直接用 Agent SDK 写」相比的差异化。

---

## 一、背景与动机

### 1.1 现状
项目当前有 5 个 CrewAI Agent（市场/竞品/财务/风险/战略），`Process.hierarchical` 模式跑单轮：4 个 worker 并行做调研，1 个 manager 综合输出 JSON。CLI 入口，输出 Markdown。

### 1.2 痛点
- **从外部观察者视角**：5 个 Agent 的核心价值（角色化 prompt + 工具调用）用 ~200 行 Anthropic SDK 也能实现，"用 CrewAI" 没有可感知的差异化。
- **从用户视角**：报告里的 TAM/LTV/CAC 数字无法追溯证据，创始人无法判断"这是 AI 幻觉还是真调研"。
- **从传播视角**：CLI 跑 15 分钟出 JSON，对非技术用户不友好，更不适合做社区分享。

### 1.3 设计意图
让用户（**非技术创始人**）能直接体验到**裸 Agent SDK 难以实现**的两件事：
1. **3 轮多 Agent 辩论**——Agent 互相 challenge、修正、捍卫
2. **每条结论带可追溯证据**——点开链接看搜索结果 / 抓取的网页原文

---

## 二、目标用户与成功标准

| 维度 | 决策 |
|------|------|
| **主要用户** | 想验证创业方向的非技术创始人 |
| **次要用户** | 关注 Agent 技术的开发者（社区 / 招聘可见性） |
| **项目定位** | 可分享的完整 Demo（社区驱动，非商业产品） |
| **部署目标** | 阿里云单台服务器 |
| **成功标准** | (a) 任何用户通过 URL 可启动分析并看到完整辩论过程<br>(b) 报告内每条关键数字带可点击证据<br>(c) 10-20 分钟内拿到 Go/No-Go/Conditional-Go 结论 |

### 显式不做（YAGNI）
- ❌ 用户账号 / 登录 / 付费
- ❌ 行业垂直模板（v2）
- ❌ 多语言（中文 v1）
- ❌ RAG / 历史分析记忆（v2）
- ❌ Eval 闭环 / 飞轮（v2）
- ❌ 字符级流式输出（v1 只做事件级流式）

---

## 三、架构总览

```
┌──────────────────────────────────────────────────┐
│  Web 前端  (Vite + React + TypeScript)            │
│  - 想法输入表单                                   │
│  - 5 Agent 实时活动卡片 + 工具调用可视化           │
│  - 挑战滚动日志（"@风险评审员 你...那不对..."）    │
│  - 最终报告（每个数字是可点击证据链接）             │
└────────────────┬─────────────────────────────────┘
                 │  SSE 事件流
┌────────────────▼─────────────────────────────────┐
│  FastAPI 后端                                     │
│  - POST /runs    → 启动一次分析                   │
│  - GET /runs/{id}/stream  → 实时事件（SSE）        │
│  - GET /runs/{id}/report  → 最终报告              │
│  - GET /evidence/{id}  → 证据原文                 │
└────────────────┬─────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  CrewAI 核心（增强版）                            │
│  5 Agent × 3 轮：                                │
│    R1 独立分析（4 worker 并行）                    │
│    R2 交叉挑战（5 agent 互发 @challenge）          │
│    R3 Manager 综合（产出最终报告）                  │
│  + 证据追踪层（每个 tool 调用产出 evidence_id）     │
│  + 挑战协议（自定义 tool 路由挑战到目标 agent）     │
└────────────────┬─────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  存储 + LLM                                       │
│  - SQLite：runs / reports / evidence / challenges │
│  - 沙盒目录：抓取的 HTML / 截图                    │
│  - LLM：DeepSeek (默认) / Anthropic               │
└──────────────────────────────────────────────────┘
```

---

## 四、模块划分

```
src/
├── crew.py                  # 现有（5 Agent 定义 + Crew 装配）
├── schemas.py               # 现有（JSON Schema 定义）
├── deliberation/            # 🆕 辩论协议层
│   ├── protocol.py          # Challenge 数据结构 + 路由
│   ├── rounds.py            # 3 轮编排逻辑
│   └── evidence.py          # 证据追踪包装
├── tools/
│   ├── search_tool.py       # 现有
│   ├── web_scraper.py       # 现有
│   ├── challenge_tool.py    # 🆕 @challenge 路由工具
│   └── evidence_capture.py  # 🆕 工具结果自动落库
├── web/                     # 🆕 FastAPI 后端
│   ├── app.py
│   ├── routes/
│   │   ├── runs.py
│   │   ├── stream.py
│   │   └── evidence.py
│   └── events.py            # 事件总线（CrewAI → SSE）
└── frontend/                # 🆕 Vite + React 前端
    ├── src/
    │   ├── App.tsx
    │   ├── main.tsx
    │   ├── components/
    │   │   ├── AgentCard.tsx
    │   │   ├── ActivityFeed.tsx
    │   │   ├── ChallengeLog.tsx
    │   │   └── EvidenceReport.tsx
    │   └── lib/sse.ts
    ├── index.html
    ├── package.json
    └── vite.config.ts
data/                        # 🆕 SQLite + 沙盒目录
```

---

## 五、3 轮辩论协议

### Round 1：独立分析（4 worker 并行）
- 触发者：`market_analyst` / `competitor_researcher` / `finance_analyst` / `risk_reviewer`
- 任务：各自做调研，产出 JSON（结构与现状相同）
- 工具：search + scrape（market/competitor/finance 三者），search only（risk）
- 证据：每次工具调用通过 `evidence_capture` 自动落库，Agent 在 JSON 中用 `evidence_ids: [...]` 引用
- `strategy_advisor` 旁观，不参与

### Round 2：交叉挑战（5 agent 全部参与）
- 输入：R1 全部 JSON + 全部 evidence
- 每个 agent 跑一次 LLM：
  - 默认行为：接受其他 agent 结论
  - 可选行为：调用 `@challenge(target_agent, claim, reason)` 自定义工具
- 被挑战的 agent 收到 challenge 后必须回应：接受并修正 / 反驳并保留
- 约束（编排层硬性执行，不依赖 agent 自觉）：
  - **每 agent 最多发 3 次 challenge**
  - **每个 challenge 至多 2 轮 sub-exchange**（"你反挑战" / "我再回应"）
- 产出：challenge_log（每条含 issuer, target, claim, reason, response, verdict）

### Round 3：综合（仅 strategy_advisor）
- 输入：R1 JSON + R2 全部 challenge + 回应
- 任务：输出最终 `StrategyReportOutput` JSON
- 约束：所有数据点必须带 `evidence_ids`，否则 Manager 重试一次

---

## 六、关键数据结构

### Challenge
```python
@dataclass
class Challenge:
    challenge_id: str          # 内部 UUID
    issuer: str                # agent 名
    target: str                # 被挑战的 agent 名
    claim: str                 # 被挑战的具体论断（引用源 JSON 的字段路径）
    reason: str                # 挑战理由
    response: str | None       # 目标 agent 的回应
    verdict: Literal["accepted", "rejected", "modified"]
    issued_at: datetime
    resolved_at: datetime | None
```

### Evidence
```python
@dataclass
class Evidence:
    evidence_id: str           # 内部 UUID
    run_id: str
    source_type: Literal["search", "scrape"]
    query: str                 # 搜索词 / 抓取 URL
    url: str | None
    title: str | None
    content_excerpt: str       # 前 500 字 / 关键摘要
    captured_at: datetime
    url_hash: str              # 用于跨 run dedup
```

### Run
```python
@dataclass
class Run:
    run_id: str
    startup_idea: str
    status: Literal["queued", "running", "complete", "failed", "partial"]
    created_at: datetime
    completed_at: datetime | None
    round1_outputs: dict[str, JSON]   # agent → JSON
    challenges: list[Challenge]
    final_report: JSON | None
    error: str | None
```

---

## 七、API 设计

| Endpoint | Method | 用途 |
|----------|--------|------|
| `/runs` | POST | 启动分析，请求体 `{startup_idea: str}`，返回 `{run_id: str}` |
| `/runs/{id}` | GET | 获取 run 状态和元数据 |
| `/runs/{id}/stream` | GET | SSE 事件流（事件类型见 §八） |
| `/runs/{id}/report` | GET | 最终 JSON 报告（run 完成后） |
| `/evidence/{id}` | GET | 证据原文（搜索结果摘要 / 抓取内容） |
| `/health` | GET | 健康检查 |

---

## 八、事件总线（CrewAI → SSE）

CrewAI 内置 `step_callback` 机制，捕获以下事件发布到 SSE 事件流：

| 事件类型 | 载荷 |
|---------|------|
| `run.start` | `{run_id, startup_idea}` |
| `round.transition` | `{from_round, to_round}` |
| `agent.start` | `{agent, round}` |
| `agent.message` | `{agent, content_summary, is_thought: bool}` |
| `tool.start` | `{agent, tool, input_preview}` |
| `tool.end` | `{agent, tool, evidence_id, output_preview}` |
| `challenge.issued` | `{challenge_id, issuer, target, claim, reason}` |
| `challenge.responded` | `{challenge_id, target, response, verdict}` |
| `agent.end` | `{agent, round, output_json_summary}` |
| `run.complete` | `{run_id, report_url}` |
| `run.failed` | `{run_id, error, partial: bool}` |

SSE 消息格式：
```
id: <event_id>
event: <type>
data: <json>

```

断线重连：客户端用 `Last-Event-ID` header，服务端从该事件 replay。

---

## 九、数据流（端到端）

```
[用户]  POST /runs {startup_idea}
            │
            ▼
[FastAPI] 创建 run (status=queued) → SQLite → 返回 run_id
            │
            ▼
[Worker]  启动 CrewAI 编排
            │
            ├─ R1: 4 个 worker 并行跑（每个都注册工具回调）
            │     每次 tool.start / tool.end → 事件总线 → SSE
            │     每次 tool 产出 → evidence_capture 写 SQLite
            │
            ├─ R2: Manager 把 R1 JSON 注入每个 agent 的 context
            │     每个 agent 跑一次 LLM，可能发 challenge
            │     challenge.tool.start → 事件总线 → SSE
            │     目标 agent 收到后跑 LLM 回应 → 事件总线 → SSE
            │
            ├─ R3: strategy_advisor 跑一次 LLM → 最终 JSON
            │
            ▼
[Worker]  写 final report → SQLite (status=complete)
            │
            ▼
[SSE]     推送 run.complete 事件
            │
            ▼
[前端]    切到最终报告视图（带 evidence 链接）
```

---

## 十、错误处理

| 失败场景 | 处理策略 |
|---------|---------|
| 搜索 / 抓取工具超时 | 重试 3 次（指数退避 1s/3s/9s），仍失败 → Agent 看到 "tool failed" 提示，自主决定继续 / 标注证据缺失 |
| LLM 输出非法 JSON | 解析失败 → 重试 1 次（追加"请严格按 JSON 输出"提示），仍失败 → run 标 `partial`，前端显示"该 Agent 输出异常，已自动降级" |
| R2 挑战死循环 | 编排层硬性限制（3 次/agent、2 轮 sub-exchange）→ 超限冻结当前状态进入 R3 |
| 整个 run 超时 | 20 分钟硬性 kill，partial 结果落库，前端显示已完成的部分 |
| SSE 断线 | 客户端用 `Last-Event-ID` 重连，服务端从该事件 replay（事件持久化 1 小时） |
| 同一 URL 重复抓取 | evidence_capture 按 URL hash dedup，所有 run 引用同一 evidence_id |
| LLM API 限流 / 5xx | 重试 3 次（指数退避），仍失败 → run 标 `failed` 并落库，用户可重试 |

---

## 十一、测试策略

| 层级 | 内容 |
|------|------|
| **单测** | challenge 路由逻辑、evidence dedup、JSON 解析重试、3 轮编排状态机 |
| **集成测试** | 3 个黄金用例（AI Agent / 垂直 SaaS / 出海），用 mock LLM（record/replay）跑完整流程，断言：<br>(a) R2 至少产生 N 条 challenge<br>(b) 报告内每条数字至少带 1 个 evidence_id<br>(c) 最终 JSON schema 合规 |
| **人工冒烟** | 跑 2 次 `examples/analyze_ai_agent.py`，验证 CLI 流程不回归；前端手动跑 1 次完整流程 |
| **不做的** | 覆盖率指标、E2E 浏览器测试套件、性能压测 |

---

## 十二、依赖与外部资源

### Python 后端
- `crewai` (现有)
- `crewai-tools` (现有)
- `fastapi` + `uvicorn`
- `sse-starlette`
- `sqlalchemy` (SQLite)
- `pydantic` (现有，已在 schemas.py)

### 前端
- `vite` + `react` + `typescript`（SPA 模式，由 FastAPI 静态托管）
- `tailwindcss`
- 无重型 UI 库（手写组件为主）
- **不选 Next.js**：无 SEO 需求、无 SSR 需求；Vite 产物可由 FastAPI 直接托管，少一个进程

### 外部 API
- DeepSeek API（默认 LLM）
- Serper API（搜索）
- 阿里云服务器（部署）

---

## 十三、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 3 轮辩论导致单次运行时间翻倍 | 用户等待时间变长 | 进度条 + 实时活动反馈，预期管理 |
| LLM 拒绝挑战 / 不主动挑战 | 辩论环节形同虚设 | 通过 prompt 强制要求"每轮必须至少发 1 次 challenge 或明确接受" |
| Serper 中文搜索质量差 | 证据质量差 | 改用 Tavily 作为 fallback；前端标注证据置信度 |
| Next.js + FastAPI 部署复杂度 | 上线时间被拖长 | **MVP 阶段用 Vite + React SPA 而非 Next.js**：Vite 产物是纯静态文件，由 FastAPI 同进程托管，省去 Node 服务和 SSR 配置；功能差异对本项目无影响（无 SEO 需求、无服务端渲染需求） |
| evidence_id 引用错误（指向不存在 ID） | 报告坏链 | Manager R3 输出后，后端校验所有 evidence_id 都存在，缺失则补占位证据 |

---

## 十四、验收清单（v0.1 Release Gate）

- [ ] 任意用户访问 URL 输入想法，10-20 分钟内拿到最终报告
- [ ] 报告内 TAM/SAM/SOM、LTV、CAC 等关键数字每个都带可点击 evidence_id
- [ ] 点击 evidence_id 能看到对应搜索结果 / 抓取网页的原文
- [ ] 前端能看到 5 个 Agent 卡片实时更新（搜索中 / 读网页中 / 写结论中）
- [ ] 挑战日志可见，挑战次数符合"每 agent ≤3"
- [ ] 任意一次失败（工具超时 / LLM 异常 / 网络断）有友好降级，不白屏
- [ ] 阿里云单台服务器可部署，README 含部署步骤
- [ ] examples/analyze_ai_agent.py CLI 流程不回归

---

## 十五、未来扩展（v0.2+ 提案，不在本次范围）

- 用户账号 + 历史分析列表
- 行业垂直模板（医疗 / 金融 / AI Infra）
- 跨 run 记忆（RAG + 向量库）
- Eval 闭环（用户对结论反馈，飞轮优化 prompt）
- 字符级流式输出
- 多语言（英文）
- 移动端 PWA

---

## 十六、参考资料

- 现有 `docs/architecture.md` / `docs/design_decisions.md`
- 现有 `src/crew.py` / `src/schemas.py` / `src/config/*.yaml`
- CrewAI 官方文档（hierarchical process、step_callback、Memory）
