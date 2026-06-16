# 项目经验 — 简历素材

> 本文档提供两个版本（中文/英文），供简历直接使用。
> 每个版本后附面试谈资要点，帮助你在面试中自然展开。

---

## 中文版

### 项目名称

**多智能体创业机会分析系统（Startup Opportunity Analyzer）**

### 项目描述（简历用，3-4行）

基于 CrewAI 框架设计并实现了多 Agent 协作的创业机会评估系统。系统采用 Hierarchical Process 架构，4 个角色化 Agent（市场分析师、竞品调研员、风险评审员、战略顾问）分工协作，通过联网搜索和网页抓取获取实时数据，自动生成包含市场规模估算（TAM/SAM/SOM）、竞品格局分析、六维风险评估的 Go/No-Go/Conditional-Go 结构化评估报告。采用配置驱动设计，Agent 角色与任务模板通过 YAML 定义，支持 DeepSeek / Claude 双 LLM 切换。

### 技术栈

CrewAI · crewai-tools · Python · DeepSeek API · Anthropic API · Serper API · YAML · Pytest

### 核心工作（简历用，bullet points）

- **多 Agent 协作架构设计**：基于 CrewAI 的 `@CrewBase` 装饰器模式，定义 4 个 Agent 和 4 个 Task，通过 `Process.hierarchical` 实现 Manager Agent 动态调度，完成市场分析 → 竞品调研 → 风险评审 → 战略汇总的依赖链编排
- **Agent 间上下文传递机制**：通过 Task 的 `context` 依赖声明实现信息流控制——风险评审 Agent 综合市场和竞品分析结论进行评估，战略顾问基于全部三份报告做出最终判断
- **工具分层分配策略**：根据 Agent 角色定位差异化分配工具能力——市场分析师和竞品调研员配备搜索+网页抓取双工具主动收集信息，风险评审员仅配备搜索做补充验证，战略顾问不配备工具专注综合推理
- **配置驱动的 Prompt 工程**：将 Agent 的 role/goal/backstory 和 Task 的 description/expected_output 抽离为独立 YAML 配置，实现 Prompt 调优与代码逻辑解耦，支持快速迭代优化输出质量
- **LLM 成本控制**：通过环境变量实现 DeepSeek（低成本中文场景）与 Claude（高精度推理场景）的无缝切换，单次完整分析成本控制在 $0.5-1.0

---

## 英文版

### Project Name

**Multi-Agent Startup Opportunity Analyzer**

### Project Description

Designed and built a multi-agent system that automates startup opportunity assessment. Four role-based AI agents (Market Analyst, Competitor Researcher, Risk Reviewer, Strategy Advisor) collaborate under a hierarchical process to produce structured Go/No-Go evaluation reports. The system performs real-time web research, market sizing (TAM/SAM/SOM), competitive landscape analysis, and multi-dimensional risk assessment. Built with a config-driven architecture where agent personas and task templates are defined in YAML, decoupled from execution logic.

### Tech Stack

CrewAI · crewai-tools · Python · DeepSeek API · Anthropic API · Serper API · YAML · Pytest

### Key Contributions

- **Multi-Agent Orchestration**: Designed a hierarchical agent architecture using CrewAI's `@CrewBase` decorator pattern. Four agents with distinct roles collaborate through a task dependency chain (market analysis → competitor research → risk review → strategic synthesis), orchestrated by a Manager Agent
- **Context-Aware Task Dependencies**: Implemented inter-agent information flow through Task context declarations — the Risk Reviewer synthesizes market and competitor findings, while the Strategy Advisor integrates all three analyses into a final Go/No-Go verdict
- **Tool Allocation Strategy**: Differentiated tool access based on agent role — researchers get search + web scraping for active data collection, the reviewer gets search-only for supplemental verification, and the advisor operates without tools for pure reasoning
- **Config-Driven Prompt Engineering**: Externalized agent personas (role/goal/backstory) and task templates (description/expected_output) into YAML configs, enabling prompt iteration without code changes
- **LLM Cost Optimization**: Implemented dual-LLM switching (DeepSeek for cost-effective Chinese analysis, Claude for high-precision reasoning) with per-analysis cost controlled at $0.5-1.0 (50-80K tokens)

---

## 面试谈资要点

> 以下内容不写在简历上，但在面试中可以自然展开。

### 谈资1：为什么选 CrewAI 而不是 LangGraph

**触发时机**：面试官问"技术选型"或"为什么用这个框架"

> "我评估了 LangChain、LangGraph、CrewAI 三个方案。这个项目的核心场景是'多角色协作分析'——每个 Agent 有明确的专业边界，任务之间有固定依赖关系。CrewAI 的 role/goal/backstory 机制天然匹配这个需求，而且 Hierarchical Process 提供了开箱即用的 Manager 模式。
>
> LangGraph 的状态机模型控制力更强，能做条件分支、循环、人工审批，但我的场景不需要这些。用 LangGraph 意味着手写 100 多行状态定义，开发周期翻倍。在 MVP 阶段我选择了开发速度优先。
>
> 如果未来需要'分析结果不好自动重做'或'用户中途选择方向'这种动态流程，我会考虑迁移到 LangGraph。"

### 谈资2：Agent 间信息流怎么设计的

**触发时机**：面试官问"架构设计"或"Agent之间怎么协作"

> "四个 Agent 不是简单串行，而是有信息依赖的设计：
> - 市场分析和竞品分析可以并行（互不依赖）
> - 风险评审依赖前两者的结论——它需要知道'市场多大'和'谁在做'才能评估风险
> - 战略汇总依赖全部三份报告
>
> 这个依赖关系通过 Task 的 `context` 字段声明。在 `@crew` 方法中，我把前序 Task 实例注入到后序 Task 的 context 列表里，CrewAI 会自动把前序 Task 的输出作为后序 Agent 的上下文传入。
>
> 这比纯 Sequential 模式好——Sequential 是每个 Agent 只看前一个的输出，我的设计让风险评审和战略顾问能看到多个前序结果的完整视图。"

### 谈资3：Prompt 工程的经验

**触发时机**：面试官问"怎么保证输出质量"或"遇到什么挑战"

> "最大的经验是：框架选对只解决 30% 的问题，剩下 70% 是 Prompt 工程。
>
> 举两个具体例子：
> - 一开始市场分析师输出的市场规模只是一个模糊数字。我在 backstory 里加入了 TAM/SAM/SOM 方法论，expected_output 里明确要求'每个论点都要有数据来源'，输出结构化程度立刻提升
> - 竞品调研员一开始只会列出竞品名字。调整 goal 为'找到至少5个直接竞品和3个间接竞品，分析商业模式和融资阶段'后，输出质量和深度显著改善
>
> 这让我意识到 Agent 的 backstory 不只是'角色描述'，实际上是控制输出质量的杠杆。我把这些全部抽到 YAML 里，调 Prompt 不用改代码，迭代效率很高。"

### 谈资4：成本控制和工程权衡

**触发时机**：面试官问"生产化"或"有什么不足"

> "一次完整分析消耗 50-80K tokens，成本 $0.5-1.0，耗时 10-15 分钟。主要成本来自两个方面：
> - 四个 Agent 各自调用 LLM 做分析和推理
> - Manager Agent 做调度决策的额外开销（Hierarchical 模式特有）
>
> 三个主要的技术不足：
> 1. 输出格式不可控——hierarchical 模式下 Pydantic Schema 有兼容性问题，只能用自然语言描述期望输出，导致报告格式每次有波动
> 2. Agent 间状态传递是纯文本——传的是 Markdown 字符串而非结构化对象，后续 Agent 要从文本中'理解'前序结论，有信息丢失风险
> 3. Manager 调度是黑盒——无法知道它为什么选择某个执行顺序，调试困难
>
> 我的后续规划是用 CrewAI Flow 在外层加流程编排，支持'快筛→确认→深度分析'的分阶段模式，减少不必要的 token 消耗。"

### 谈资5：这个项目体现了什么工程能力

**触发时机**：面试官问"你觉得自己最强的能力是什么"或综合评估题

> "这个项目体现了三个我认为重要的工程能力：
> 1. **技术选型决策**——我不是选最流行的框架，而是根据场景特征（多角色协作、固定依赖、MVP 阶段）选择最合适的工具，并且能说清楚权衡取舍
> 2. **配置驱动设计**——把容易变化的部分（Prompt）和稳定的部分（执行逻辑）分离，这在 AI 应用里特别重要，因为 Prompt 的迭代频率远高于代码
> 3. **端到端交付**——从框架选型、架构设计、Prompt 工程到测试验证，一个人完成了整个系统的搭建，并且有真实可运行的输出"
