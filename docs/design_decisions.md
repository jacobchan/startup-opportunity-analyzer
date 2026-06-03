# 设计决策记录

本文档记录项目中的关键设计决策及其理由。面试时可基于此展开讨论。

---

## 1. 为什么选CrewAI而不是LangGraph？

**决策：使用CrewAI作为主框架**

**理由：**
- 本项目的核心场景是"多角色协作分析"，每个Agent有明确的角色定位和专业边界
- CrewAI的 role/goal/backstory 机制天然匹配"模拟团队协作"的需求
- LangGraph更适合需要精细控制状态流转的复杂工作流（如审批流、多轮对话系统）
- CrewAI的 hierarchical process 提供了开箱即用的Manager模式

**取舍：**
- 放弃了LangGraph的细粒度状态控制能力
- CrewAI的错误处理和重试机制不如LangGraph灵活
- 如果未来需要更复杂的工作流（条件分支、循环），可能需要迁移到LangGraph

---

## 2. 为什么选hierarchical而不是sequential？

**决策：使用Process.hierarchical（Manager模式）**

**理由：**
- 分析任务需要Manager汇总多方意见做综合判断，不只是简单串行
- Strategy Advisor作为Manager，能根据前序任务结果动态调整后续任务
- Sequential模式下，最后一个Agent只是被动接收前序输出

**取舍：**
- hierarchical模式LLM调用次数更多（Manager需要做调度决策）
- 降低了单次运行的可预测性（Manager可能跳过或重排任务）

---

## 3. 为什么不合并市场分析和竞品调研？

**决策：拆分为独立的Market Analyst和Competitor Researcher**

**理由：**
- 关注点不同：市场分析关注"蛋糕多大"，竞品调研关注"谁在抢蛋糕"
- 合并会导致单个Agent的prompt过长，影响输出质量
- 独立Agent可以并行搜索，提高信息收集效率

**取舍：**
- 增加了LLM调用成本（两次独立分析 vs 一次综合分析）
- 需要Manager做更好的信息汇总

---

## 4. LLM选择策略

**决策：全部使用Claude Sonnet**

**理由：**
- 简化维护，避免多模型适配的复杂性
- CrewAI的multi-LLM支持在实际使用中仍有稳定性问题
- Sonnet在中文理解和结构化输出方面表现稳定

**取舍：**
- 成本高于混合方案（Manager用Sonnet，Worker用Haiku）
- 未利用不同模型的不同优势（如GPT-4的长上下文）

---

## 5. 工具选择

**决策：Serper API + ScrapeWebsiteTool**

**理由：**
- Serper：成本低（$50/50000次），中文搜索质量好，注册简单
- ScrapeWebsiteTool：CrewAI内置，无需额外配置
- 未选择Tavily：免费额度更少，中文搜索质量不如Serper

**取舍：**
- Serper的搜索结果可能不够新（索引延迟）
- 网页抓取可能被反爬策略拦截

---

## 6. 输出格式控制

**决策：通过expected_output的描述控制输出格式，而非Pydantic模型**

**理由：**
- CrewAI的Pydantic输出支持在hierarchical模式下有兼容性问题
- 自然语言描述更灵活，LLM能更好地理解期望的输出结构
- 实际测试中，描述驱动的输出质量比强制schema更高

**取舍：**
- 输出格式不够严格，可能需要后处理
- 不利于程序化消费（如果有下游系统需要解析）

---

## 7. 风险与局限

- **搜索质量依赖Serper**：如果搜索结果质量差，分析结论会受影响
- **LLM幻觉风险**：市场规模等数据可能被LLM编造，需要人工交叉验证
- **成本控制**：一次完整分析约消耗50-80K tokens，成本约$0.5-1.0
- **运行时间**：完整分析约需5-10分钟，不适合实时场景

---

## 8. 未来改进方向

- [ ] 添加RAG模块，支持基于企业内部数据的分析
- [ ] 添加Milvus/PGVector向量检索，实现历史分析案例的相似度匹配
- [ ] 实现streaming输出，提升交互体验
- [ ] 添加评估框架，量化分析报告的质量
- [ ] 支持自定义Agent角色和工具（插件化架构）
