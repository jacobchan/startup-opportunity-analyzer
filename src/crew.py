"""
创业机会分析智能体 - Crew定义

基于CrewAI的hierarchical process，4个Agent协作完成创业机会评估：
1. 市场分析师 → 市场规模、增长趋势、用户画像
2. 竞品调研员 → 竞品分析、差异化机会
3. 风险评审员 → 多维度风险评估
4. 战略顾问（Manager） → 综合研判，输出最终报告
"""

from pathlib import Path
from typing import List

from crewai import Agent, Crew, Task, Process, LLM
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff

from src.tools.search_tool import search_tool
from src.tools.web_scraper import scrape_tool
from src.config.settings import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


def _get_llm() -> LLM:
    """根据配置创建LLM实例，支持DeepSeek和Claude"""
    if "deepseek" in LLM_MODEL:
        return LLM(
            model=LLM_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    return LLM(model=LLM_MODEL)


@CrewBase
class StartupAnalyzerCrew:
    """创业机会分析 Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self):
        super().__init__()
        self._llm = _get_llm()
        self._startup_idea = None
        self._save_to = None

    @before_kickoff
    def inject_startup_idea(self, inputs: dict) -> dict:
        """在kickoff前注入startup_idea到inputs"""
        if "startup_idea" in inputs:
            self._startup_idea = inputs["startup_idea"]
        return inputs

    @after_kickoff
    def save_report(self, output):
        """kickoff后保存报告（如果配置了save_to）"""
        if self._save_to:
            Path(self._save_to).parent.mkdir(parents=True, exist_ok=True)
            with open(self._save_to, "w", encoding="utf-8") as f:
                f.write(f"# 创业机会分析报告\n\n")
                f.write(f"## 分析方向：{self._startup_idea}\n\n")
                f.write(str(output.raw))
            print(f"\n报告已保存至: {self._save_to}")
        return output

    @agent
    def market_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["market_analyst"],
            tools=[search_tool, scrape_tool],
            llm=self._llm,
            verbose=True,
        )

    @agent
    def competitor_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["competitor_researcher"],
            tools=[search_tool, scrape_tool],
            llm=self._llm,
            verbose=True,
        )

    @agent
    def risk_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["risk_reviewer"],
            tools=[search_tool],
            llm=self._llm,
            verbose=True,
        )

    @agent
    def strategy_advisor(self) -> Agent:
        return Agent(
            config=self.agents_config["strategy_advisor"],
            llm=self._llm,
            verbose=True,
        )

    @task
    def market_analysis(self) -> Task:
        return Task(config=self.tasks_config["market_analysis"])

    @task
    def competitor_analysis(self) -> Task:
        return Task(config=self.tasks_config["competitor_analysis"])

    @task
    def risk_review(self) -> Task:
        return Task(config=self.tasks_config["risk_review"])

    @task
    def strategy_report(self) -> Task:
        return Task(config=self.tasks_config["strategy_report"])

    @crew
    def crew(self) -> Crew:
        # 设置任务间的context依赖
        # Wire task context dependencies after all tasks are created
        # self.tasks is populated by @task decorators in definition order:
        # [market_analysis, competitor_analysis, risk_review, strategy_report]
        market, competitor, risk, strategy = self.tasks
        risk.context = [market, competitor]
        strategy.context = [market, competitor, risk]

        # strategy_advisor as manager, others as workers
        manager = self.strategy_advisor()
        worker_agents = [
            self.market_analyst(),
            self.competitor_researcher(),
            self.risk_reviewer(),
        ]

        return Crew(
            agents=worker_agents,
            tasks=self.tasks,
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True,
        )


def run_analysis(startup_idea: str, save_to: str | None = None) -> str:
    """
    执行创业机会分析

    Args:
        startup_idea: 创业方向描述，例如 "面向中小企业的AI Agent客服平台"
        save_to: 报告保存路径（可选）

    Returns:
        完整的分析报告（Markdown格式）
    """
    analyzer = StartupAnalyzerCrew()
    if save_to:
        analyzer._save_to = save_to

    result = analyzer.crew().kickoff(
        inputs={"startup_idea": startup_idea}
    )

    return result.raw


if __name__ == "__main__":
    import sys

    idea = sys.argv[1] if len(sys.argv) > 1 else "面向中小企业的AI Agent客服平台"
    output = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"正在分析创业方向: {idea}")
    print(f"使用模型: {LLM_MODEL}\n")
    report = run_analysis(idea, save_to=output)
    print("\n" + "=" * 60)
    print(report)
