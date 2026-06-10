# 系统架构说明

> 本文档深入讲解创业机会分析系统的设计思路、实现细节与演进方向。
> 供项目参与者理解"为什么这样设计"以及"每个部分做了什么"。

---

## 一、系统全貌

一句话概括：**用户输入一个创业方向描述，系统派 4 个 AI 角色各司其职去调研，最后由一位"战略顾问"汇总出一份 Go/No-Go/Conditional-Go 评估报告。**

```
用户输入                    4个Agent协作                     最终输出
"AI客服平台"  ─────►  [市场分析] [竞品调研] [风险评估] [战略汇总]  ─────►  分析报告.md
                        ──►──►──►  (context依赖链)
```

运行一次完整分析约消耗 50-80K tokens，成本 $0.5-1.0，耗时 10-15 分钟。

---

## 二、目录结构与每个文件的作用

```
startup-opportunity-analyzer/
├── src/                          # 核心代码
│   ├── crew.py                   # 主入口：Crew定义（4个Agent + 4个Task + 协作流程）
│   ├── __init__.py               # 导出 StartupAnalyzerCrew 和 run_analysis
│   ├── config/
│   │   ├── agents.yaml           # 4个Agent的角色定义（role/goal/backstory）
│   │   ├── tasks.yaml            # 4个Task的任务描述和期望输出
│   │   └── settings.py           # 环境变量（LLM模型、API Key）
│   ├── tools/
│   │   ├── search_tool.py        # Serper搜索工具（网络检索）
│   │   └── web_scraper.py        # 网页抓取工具（读取网页内容）
│   ├── agents/                   # 空目录（预留扩展）
│   └── tasks/                    # 空目录（预留扩展）
├── examples/                     # 示例入口
│   ├── analyze_ai_agent.py       # 分析"AI Agent客服平台"
│   ├── analyze_saas.py           # 分析"产业园区SaaS"
│   └── output/                   # 生成的报告样例
├── tests/                        # 测试
│   └── test_agents.py            # 验证配置加载和Crew构建
├── docs/                         # 文档
│   ├── architecture.md           # 本文件：架构说明
│   └── design_decisions.md       # 设计决策记录
└── pyproject.toml                # 项目依赖声明
```

---

## 三、核心执行流程（从入口到报告）

以 `python -m examples.analyze_ai_agent` 为例，完整执行路径如下：

### 第1步：入口调用

`examples/analyze_ai_agent.py` 做了一件事：

```python
from src.crew import run_analysis
report = run_analysis(
    startup_idea="面向中小企业的AI Agent客服平台...",
    save_to="examples/output/ai_agent_analysis.md",
)
```

### 第2步：`run_analysis()` 构建并启动 Crew

```python
def run_analysis(startup_idea, save_to=None):
    analyzer = StartupAnalyzerCrew()   # 实例化Crew类
    analyzer._save_to = save_to        # 配置保存路径
    result = analyzer.crew().kickoff(  # 构建Crew并启动
        inputs={"startup_idea": startup_idea}
    )
    return result.raw
```

关键点：`inputs={"startup_idea": "..."}` 会被 CrewAI 自动注入到所有 Task 的 description 中，替换 `{startup_idea}` 占位符。

### 第3步：`StartupAnalyzerCrew` 的组装过程

`@CrewBase` 装饰器做了两件关键的事：
1. 自动加载 `agents.yaml` 到 `self.agents_config`
2. 自动加载 `tasks.yaml` 到 `self.tasks_config`

然后 4 个 `@agent` 方法被收集为 Agent 列表，4 个 `@task` 方法被收集为 Task 列表。

### 第4步：`@crew` 方法组装最终执行单元

```python
@crew
def crew(self) -> Crew:
    # 1. 设置任务间的context依赖
    market, competitor, risk, strategy = self.tasks
    risk.context = [market, competitor]           # 风险评审依赖市场+竞品
    strategy.context = [market, competitor, risk]  # 战略报告依赖全部三个

    # 2. strategy_advisor 做Manager，其余3个做Worker
    manager = self.strategy_advisor()
    workers = [self.market_analyst(), self.competitor_researcher(), self.risk_reviewer()]

    return Crew(
        agents=workers,
        tasks=self.tasks,
        process=Process.hierarchical,
        manager_agent=manager,
    )
```

### 第5步：生命周期钩子

- `@before_kickoff` — 在 kickoff 之前执行，保存 `startup_idea` 供后续使用
- `@after_kickoff` — 在 kickoff 完成后执行，如果设置了 `save_to` 就把报告写入文件

---

## 四、4 个 Agent 的分工与工具分配

```
┌─────────────────┐     ┌─────────────────┐
│  market_analyst  │     │ competitor_     │
│  资深市场分析师   │     │ researcher      │
│                 │     │ 竞品调研专家     │
│  工具: 搜索+抓取 │     │  工具: 搜索+抓取 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │  context 依赖          │
         ▼                       ▼
┌─────────────────────────────────┐
│        risk_reviewer            │
│        创业风险评审专家          │
│        工具: 仅搜索             │
└───────────────┬─────────────────┘
                │  context 依赖
                ▼
┌─────────────────────────────────┐
│     strategy_advisor (Manager)  │
│     创业战略顾问                 │
│     工具: 无（纯综合分析）       │
└─────────────────────────────────┘
```

| Agent | 做什么 | 有什么工具 | 输出什么 |
|---|---|---|---|
| **market_analyst** | TAM/SAM/SOM估算、增长趋势、用户画像、时机判断 | 搜索+网页抓取 | 市场分析报告 |
| **competitor_researcher** | 找5+直接竞品、3+间接竞品，分析商业模式和短板 | 搜索+网页抓取 | 竞品分析报告 |
| **risk_reviewer** | 技术/市场/团队/资金/政策/时机六维风险评估 | 仅搜索（综合前序结论） | 风险评估报告 |
| **strategy_advisor** | 汇总三方结论，输出 Go/No-Go/Conditional-Go 判断 | 无（纯推理） | 最终评估报告 |

**为什么 strategy_advisor 没有工具？** 因为它的角色是"综合研判"，不需要自己去搜索，只需要读取前三个 Agent 的分析结果做出判断。

---

## 五、配置驱动设计（YAML 分离）

### `agents.yaml` — 定义角色人格

每个 Agent 的 `role`、`goal`、`backstory` 都在 YAML 中定义，不在 Python 代码中。这让你可以随时调整 Agent 的"性格"和行为导向，而不用改代码。

```yaml
market_analyst:
  role: "资深市场分析师"
  goal: "分析市场规模、增长趋势、用户画像..."
  backstory: "你是一位有10年经验的市场分析师..."
```

`@CrewBase` 类通过 `config=self.agents_config["market_analyst"]` 引用这些配置，CrewAI 会自动将 YAML 中的字段映射到 Agent 构造参数。

### `tasks.yaml` — 定义任务模板

每个 Task 的 `description` 包含 `{startup_idea}` 占位符，运行时由 CrewAI 通过 `kickoff(inputs=...)` 自动替换为实际输入。`expected_output` 用自然语言描述期望的输出格式。

```yaml
market_analysis:
  description: >
    对以下创业方向进行深入的市场分析：{startup_idea}
    请完成：1. 市场规模估算  2. 增长趋势 ...
  expected_output: >
    一份结构化的市场分析报告...
  agent: market_analyst
```

**为什么用自然语言描述而非 Pydantic Schema？** 因为 CrewAI 的 Pydantic 输出在 hierarchical 模式下有兼容性问题，自然语言描述反而质量更高。

---

## 六、LLM 配置机制

`settings.py` 通过环境变量控制使用哪个 LLM：

| 环境变量值 | 走哪个 API | 特点 |
|---|---|---|
| `deepseek-v4-pro`（默认） | DeepSeek API | 便宜、中文好、推理稳定 |
| `anthropic/claude-sonnet-4-6` | Anthropic API | 推理强、长上下文 |

`_get_llm()` 函数根据模型名称自动选择 API 配置：

```python
if "deepseek" in LLM_MODEL:
    return LLM(model=LLM_MODEL, api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
return LLM(model=LLM_MODEL)  # 默认走 Anthropic
```

---

## 七、工具层

| 工具 | 实现方式 | 用途 |
|---|---|---|
| **search_tool** | `crewai_tools.SerperDevTool` | 通过 Serper API 执行网络搜索，获取行业报告、新闻、竞品信息 |
| **scrape_tool** | `crewai_tools.ScrapeWebsiteTool` | 抓取指定 URL 的网页文本内容，用于深入阅读搜索到的页面 |

工具分配策略：
- **market_analyst + competitor_researcher** 拥有搜索+抓取两个工具，因为它们需要主动收集外部信息
- **risk_reviewer** 仅有搜索工具，主要依赖前序分析结论，偶尔补充搜索
- **strategy_advisor** 无工具，纯粹综合推理

---

## 八、CrewAI `@CrewBase` 装饰器模式

项目使用 CrewAI 推荐的类装饰器模式（而非旧版函数式写法），核心结构如下：

```python
@CrewBase
class StartupAnalyzerCrew:
    agents: List[BaseAgent]          # 类型声明，CrewAI自动收集@agent方法
    tasks: List[Task]                # 类型声明，CrewAI自动收集@task方法

    agents_config = "config/agents.yaml"   # 相对于类文件的路径
    tasks_config = "config/tasks.yaml"

    @agent
    def market_analyst(self) -> Agent:
        return Agent(config=self.agents_config["market_analyst"], ...)

    @task
    def market_analysis(self) -> Task:
        return Task(config=self.tasks_config["market_analysis"])

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks, ...)
```

关键机制：
- `@agent` 装饰的方法返回值会被自动收集到 `self.agents`
- `@task` 装饰的方法返回值会被自动收集到 `self.tasks`，收集顺序与定义顺序一致
- `@crew` 方法定义最终的 Crew 组装逻辑
- `@before_kickoff` / `@after_kickoff` 提供生命周期钩子

---

## 九、Hierarchical Process 的工作方式

项目使用 `Process.hierarchical` 而非 `Process.sequential`：

- **Sequential**：Task 按顺序执行，每个 Agent 被动接收前一个 Task 的输出
- **Hierarchical**：Manager Agent（strategy_advisor）动态决定任务执行顺序、可以重新分配任务、最终汇总所有结果

在这个项目中，Manager 的作用是：
1. 接收所有 Worker Agent 的分析结果
2. 综合研判，而非简单拼接
3. 输出结构化的 Go/No-Go/Conditional-Go 结论

代价是 Manager 会额外消耗 LLM 调用来做调度决策。

---

## 十、后续演进方向

### 短期优化（不改架构）

1. **报告质量提升** — 在 `agents.yaml` 的 backstory 中加入更具体的分析框架（如 Porter's Five Forces、STP 模型），让 Agent 输出更结构化
2. **增加数据源工具** — 添加天眼查/企查查 API 工具，让竞品调研拿到融资数据；添加财报/行业报告数据库接口
3. **输出格式化** — 在 `@after_kickoff` 中添加 Markdown → PDF 的转换，或者用正则/Jinja2 模板对报告做后处理

### 中期扩展（增加 Agent/Task）

4. **新增"技术可行性分析师"Agent** — 专门评估技术栈选型、开源组件可用性、开发周期估算，当前4个Agent都未深入覆盖这一维度
5. **新增"财务建模Agent"** — 自动生成收入预测模型、现金流分析、估值模型，让"资金需求估算"从定性变定量
6. **增加多轮对话能力** — 用户看完报告后可以追问"帮我深入分析竞品X"或"换一个方向：教育行业"，在当前分析上下文中继续探索

### 架构级演进

7. **引入 CrewAI Flow** — 用 `Flow` 编排多个 Crew 的执行，比如：
   - Flow 1：快速筛选（只跑 market_analyst，5分钟出初筛结论）
   - Flow 2：深度分析（当前完整流程）
   - Flow 3：专题深挖（用户选某个维度后只跑对应Agent）

   这样用户可以先用"快筛"判断值不值得深入，避免每次都等 15 分钟。

8. **RAG + 向量数据库** — 引入 Milvus/PGVector，存储历史分析报告和行业数据，让 Agent 能参考"上一次分析类似方向时的结论"，形成知识积累。其实不仅仅的vetorDB，更需要一套4层的memory体系构建，确保助手具备多层记忆。（这里我会考虑是不是对于这个创业机会分析Agent过度设计记忆了，其实作为一个用完即走的工具时，其实它就没有必要有那么多层的记忆，只需要保留部分数据即可。）

9. **评估框架** — 自动对比分析报告中的预测与实际情况（如果用户半年后回来填反馈），量化 Agent 分析的准确度。 需要建立一套Eval体系，通过数据化、可视化的方式对模型进行评估，确保Harness系统的可靠。

10. **插件化架构** — 让用户自定义 Agent 角色、工具和分析维度，支持不同行业模板（医疗、教育、金融各有不同的风险关注点）
