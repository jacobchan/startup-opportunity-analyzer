# Startup Opportunity Analyzer

> 基于 **CrewAI** 的多智能体创业机会分析系统。5 个 Agent 协作完成市场分析、竞品调研、财务建模、风险评估，输出 Go/No-Go/Conditional-Go 的结构化评估报告。
>
> 完整 web 端产品，支持 SSE 实时推送、历史分析、断点续跑。中文场景，DeepSeek V4 Pro + Serper 搜索。

## 核心特性

- **3 轮 deliberation 机制**：第 1 轮 4 个 worker 独立分析 → 第 2 轮交叉挑战 → 第 3 轮战略汇总。避免单 Agent 视角偏差
- **状态化引擎**：每完成一个 agent 即 checkpoint 写入 SQLite，崩溃后能从断点继续而非从头重跑
- **Web 端产品**：FastAPI + React + SSE 实时推送 + 历史列表 + URL 持久化
- **证据可追溯**：搜索/抓取结果落库到 `Evidence` 表，报告里 `ev-xxx` 引用一键查原文
- **跨平台部署**：包含阿里云 ECS 部署文档和 systemd / Nginx 配置

## 快速开始

```bash
# 1. 克隆 & 安装
git clone https://github.com/jacobchan/startup-opportunity-analyzer.git
cd startup-opportunity-analyzer
pip install -e ".[dev]"

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY 和 SERPER_API_KEY

# 3. CLI 跑一次分析
python -m examples.analyze_ai_agent

# 4. 启动 web 端
cd frontend && npm install && npm run build && cd ..
uvicorn src.web.app:create_app --factory --host 0.0.0.0 --port 8000
# 访问 http://localhost:8000
```

## 三种使用方式

### 1. CLI 模式（hierarchical 模式）

```bash
# 跑预设示例
python -m examples.analyze_ai_agent
python -m examples.analyze_saas

# 自定义方向
python -m src.crew "面向物业管理的 AI Agent 平台"
python -m src.crew "你的创业方向" examples/output/my_report.md
```

CLI 走 `StartupAnalyzerCrew.crew()` 的 hierarchical 模式，5 个 Agent 一次性串起来。

### 2. Web 端（3 轮 deliberation）

启动后访问 `http://localhost:8000`：
- 输入创业方向 → 提交 → SSE 实时看到 5 个 Agent 轮流工作
- 第 2 轮会看到 3 个 Agent 互相挑战的日志
- 完成后跳转到最终评估页（Go/No-Go/Conditional-Go）
- 历史列表可查看/重跑/删除过往分析

### 3. 程序化调用

```python
from src.web.runner import run_deliberation
from src.storage import create_run, get_session

session = get_session()
run = create_run(session, startup_idea="AI Agent 平台")
session.close()

report = run_deliberation(
    run_id=run.run_id,
    startup_idea="AI Agent 平台",
    event_publisher=lambda e: print(e),
)
print(report["decision"])
```

## 架构

```
                            ┌─────────────────────────────┐
                            │      DeliberationEngine     │
                            │   (stateful, checkpointed)  │
                            └──────────────┬──────────────┘
                                           │
        ┌──────────── R1 ─────────────┐    ┌┴──────── R2 ─────────┐
        │  4 agents analyze           │    │  3 agents cross-     │
        │  independently              │    │  challenge via tool  │
        │                             │    │                       │
        │  market_analyst ─┐          │    │  market_analyst       │
        │  competitor ─────┼─→ checkpoint per agent →  competitor     │
        │  finance ────────┤          │    │  finance              │
        │  risk_reviewer ──┘ (depends on first 3)                       │
        └─────────────────────────────┘    └───────────────────────┘
                                           │
                                           ▼
                                ┌──────────────────────┐
                                │  R3: strategy_advisor │
                                │  synthesize to        │
                                │  Go/No-Go report      │
                                └──────────────────────┘
```

### 5 个 Agent 角色

| Agent | 角色 | 输出 | 工具 |
|-------|------|------|------|
| `market_analyst` | 资深市场分析师 | TAM/SAM/SOM、增长趋势、用户画像 | search + scrape |
| `competitor_researcher` | 竞品与行业调研专家 | 竞品列表、竞争格局、差异化机会 | search + scrape |
| `finance_analyst` | 创业财务分析专家 | LTV/CAC 模型、定价策略、资金需求 | search + scrape |
| `risk_reviewer` | 创业风险评审专家 | 多维度风险列表、整体风险评级 | search |
| `strategy_advisor` | 创业战略顾问 | Go/No-Go 决策、下一步行动计划、信心度 | — |

所有 Worker Agent 输出都是结构化 JSON。`strategy_advisor` 在 hierarchical 模式下做 Manager，在 web 端 R3 单独汇总。

### 状态化引擎

`src/deliberation/engine.py` 是 3 轮编排的核心：

- **Agent 缓存**：每个角色 Agent 构造一次复用（除非 R2 需要换 `challenge_tool`）
- **Checkpoint 粒度**：每完成一个 agent 写入一次 `Run.deliberation_state`
- **崩溃恢复**：进程崩了后调 `POST /runs/{id}/resume`，从下一个未完成 agent 继续
- **可单测**：`tests/deliberation/test_engine.py` 用 mock agent factory 跑 10 个控制流测试

详见 [docs/deliberation_engine.md](docs/deliberation_engine.md)。

## 技术栈

| 组件 | 选择 | 说明 |
|------|------|------|
| Agent 框架 | **CrewAI** (hierarchical) | 角色驱动多 Agent 协作 |
| LLM | DeepSeek V4 Pro | 中文理解 + 结构化输出稳定、成本低 |
| 输出约束 | JSON Schema（自然语言描述） | DeepSeek 不支持 `response_format: json_schema`，通过 `expected_output` 描述 Schema 手动解析 |
| 搜索 | Serper API | 中文搜索质量好、$50/50000 次 |
| 网页抓取 | ScrapeWebsiteTool | CrewAI 内置 |
| Web 框架 | FastAPI | SSE 流式响应 + async |
| 存储 | SQLite + SQLAlchemy | 单文件、零运维 |
| 前端 | React + Vite + TypeScript | SSE 订阅 + 历史列表 |
| 语言 | Python 3.11+ / TypeScript 5 | |

## 目录结构

```
startup-opportunity-analyzer/
├── src/
│   ├── crew.py                       # StartupAnalyzerCrew (hierarchical 模式入口)
│   ├── schemas.py                    # 6 套 Pydantic 输出模型
│   ├── config/
│   │   ├── agents.yaml               # 5 个 Agent 的 role/goal/backstory
│   │   ├── tasks.yaml                # 5+1 个 Task 定义
│   │   └── settings.py               # 环境变量
│   ├── deliberation/                 # 3 轮 deliberation 引擎
│   │   ├── engine.py                 # DeliberationEngine（核心）
│   │   ├── state.py                  # EngineState（Pydantic）
│   │   ├── checkpoint.py             # CheckpointStore（SQLite 持久化）
│   │   ├── rounds.py                 # RoundOrchestrator（兼容旧测试）
│   │   ├── evidence.py               # 证据捕获装饰器
│   │   └── protocol.py               # ChallengeDraft / Verdict
│   ├── tools/                        # search / scrape / challenge
│   ├── storage/                      # SQLAlchemy models + repository
│   └── web/                          # FastAPI 应用
│       ├── app.py                    # create_app 工厂
│       ├── runner.py                 # run_deliberation / resume_deliberation
│       ├── events.py                 # EventBus（SSE）
│       ├── run_registry.py           # run_id -> EventBus 映射
│       └── routes/
│           ├── runs.py               # POST /runs, GET /runs/{id}, DELETE
│           ├── stream.py             # GET /runs/{id}/stream (SSE)
│           ├── evidence.py           # GET /evidence/{id}
│           └── resume.py             # POST /runs/{id}/resume
├── frontend/                         # React + Vite + TypeScript
│   └── src/
│       ├── App.tsx                   # 视图路由 + 状态恢复
│       ├── components/               # StartupForm, HistoryList, AgentCard, ...
│       └── lib/                      # sse.ts, types.ts
├── examples/                         # CLI 入口示例
│   ├── analyze_ai_agent.py
│   └── analyze_saas.py
├── tests/                            # 90 个测试，全套 < 3 秒
│   ├── deliberation/                 # 状态机 + 引擎控制流（17 个）
│   ├── web/                          # API 层（19 个）
│   ├── storage/                      # 仓储层
│   ├── tools/                        # 工具层
│   ├── integration/                  # 端到端（2 个）
│   └── test_agents.py                # 配置加载
├── docs/
│   ├── architecture.md               # 旧版架构说明（CLI 模式为主）
│   ├── design_decisions.md           # 设计决策记录
│   ├── deliberation_engine.md        # 新版：引擎架构 + 故障恢复手册
│   └── superpowers/                  # 历史设计文档
├── data/
│   └── analyzer.db                   # SQLite 数据库
├── pyproject.toml
├── AGENTS.md                         # 给 AI 助手的项目说明
└── README.md                         # 本文件
```

## HTTP API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/runs` | 创建一次新分析（body: `{"startup_idea": "..."}`） |
| GET | `/runs` | 列出历史分析（分页） |
| GET | `/runs/{id}` | 查询单次分析状态 + R1 outputs |
| GET | `/runs/{id}/report` | 拉取最终评估报告 |
| GET | `/runs/{id}/stream` | SSE 流，订阅实时事件 |
| POST | `/runs/{id}/resume` | 从断点恢复（failed / paused 状态） |
| DELETE | `/runs/{id}` | 删除分析记录 |
| GET | `/evidence/{id}` | 查询证据原文（搜索/抓取内容） |

完整事件协议见 `frontend/src/lib/types.ts`。

## 添加新 Agent

1. 在 `src/schemas.py` 中加 Pydantic 输出模型
2. 在 `src/config/agents.yaml` 中定义 role/goal/backstory
3. 在 `src/config/tasks.yaml` 中加 Task 和 `expected_output`
4. 在 `src/crew.py` 的 `@agent` 和 `@task` 装饰器中注册
5. 在 `src/web/runner.py` 的 `_build_engine` 中加到 `tools_map`

## 运行测试

```bash
pytest tests/                       # 全套（90 个，约 3 秒）
pytest tests/deliberation/          # 引擎相关
pytest tests/web/                   # API 层
pytest tests/integration/           # 端到端

ruff check src/ tests/              # Lint
```

## 部署到阿里云 ECS

### 前置条件

- 阿里云 ECS 一台（2 vCPU / 4GB RAM 起步）
- Ubuntu 22.04 LTS
- 域名（可选，HTTPS 用）

### 部署步骤

```bash
# 1. 系统依赖
sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx nodejs npm

# 2. 克隆 & Python 后端
git clone https://github.com/jacobchan/startup-opportunity-analyzer.git
cd startup-opportunity-analyzer
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. 环境变量
cp .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY / SERPER_API_KEY

# 4. 前端构建
cd frontend && npm install && npm run build && cd ..

# 5. 启动后端
uvicorn src.web.app:create_app --factory --host 0.0.0.0 --port 8000
```

### systemd 管理

创建 `/etc/systemd/system/analyzer.service`：

```ini
[Unit]
Description=Startup Opportunity Analyzer
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/startup-opportunity-analyzer
Environment="PATH=/home/ubuntu/startup-opportunity-analyzer/.venv/bin"
ExecStart=/home/ubuntu/startup-opportunity-analyzer/.venv/bin/uvicorn src.web.app:create_app --factory --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now analyzer
sudo systemctl status analyzer
```

### Nginx 反代 + HTTPS

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 必须
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/analyzer /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

HTTPS 用 certbot：

```bash
sudo certbot --nginx -d yourdomain.com
```

## 关键设计决策

详见 [docs/design_decisions.md](docs/design_decisions.md)。核心要点：

- **CrewAI over LangGraph**：role-driven 更契合"模拟团队协作"场景
- **Hierarchical over sequential**：Manager 模式能根据前序结果动态决策
- **3 轮 deliberation**：单轮分析 + 交叉挑战 + 战略汇总，避免单视角偏差
- **状态化引擎 + checkpoint**：8 次冷启动 → 1 个有状态单元，可恢复、可单测
- **YAML config over code**：agent 角色和 prompt 改 YAML 不动 Python
- **自然语言 expected_output 驱动**：Pydantic schema 校验在 hierarchical 模式下兼容性差，描述驱动实际效果更好

## 已知限制

- **搜索质量依赖 Serper**：搜索结果质量差时，分析结论会受影响
- **LLM 幻觉风险**：市场规模等数据可能被 LLM 编造，需人工交叉验证（证据可追溯功能是缓解手段）
- **运行时间**：完整分析 10-15 分钟（5 个 Agent × 工具调用 + 思考），实时场景不合适
- **成本**：每次完整分析 $0.7-1.2（60-100K tokens）

## License & 联系方式

「架构师创业笔记」（Personal, xiaohongshu 同名）。有兴趣一起开发智能体的同伴可 email 联系我：`jacobchan5519@gmail.com`
