"""
创业机会分析智能体 - Crew定义

基于CrewAI的hierarchical process，4个Agent协作完成创业机会评估：
1. 市场分析师 → 市场规模、增长趋势、用户画像
2. 竞品调研员 → 竞品分析、差异化机会
3. 风险评审员 → 多维度风险评估
4. 战略顾问（Manager） → 综合研判，输出最终报告
"""

import os
import yaml
from pathlib import Path
from crewai import Agent, Task, Crew, Process, LLM

from src.tools.search_tool import search_tool
from src.tools.web_scraper import scrape_tool
from src.config.settings import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

CONFIG_DIR = Path(__file__).parent / "config"


def load_yaml(filename: str) -> dict:
    with open(CONFIG_DIR / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_llm() -> LLM:
    """根据配置创建LLM实例，支持DeepSeek和Claude"""
    if "deepseek" in LLM_MODEL:
        return LLM(
            model="deepseek-v4-pro",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    return LLM(model=LLM_MODEL)


def create_agents() -> dict[str, Agent]:
    """创建4个Agent"""
    agents_config = load_yaml("agents.yaml")
    llm = get_llm()

    return {
        "market_analyst": Agent(
            role=agents_config["market_analyst"]["role"],
            goal=agents_config["market_analyst"]["goal"],
            backstory=agents_config["market_analyst"]["backstory"],
            tools=[search_tool, scrape_tool],
            llm=llm,
            verbose=True,
        ),
        "competitor_researcher": Agent(
            role=agents_config["competitor_researcher"]["role"],
            goal=agents_config["competitor_researcher"]["goal"],
            backstory=agents_config["competitor_researcher"]["backstory"],
            tools=[search_tool, scrape_tool],
            llm=llm,
            verbose=True,
        ),
        "risk_reviewer": Agent(
            role=agents_config["risk_reviewer"]["role"],
            goal=agents_config["risk_reviewer"]["goal"],
            backstory=agents_config["risk_reviewer"]["backstory"],
            tools=[search_tool],
            llm=llm,
            verbose=True,
        ),
        "strategy_advisor": Agent(
            role=agents_config["strategy_advisor"]["role"],
            goal=agents_config["strategy_advisor"]["goal"],
            backstory=agents_config["strategy_advisor"]["backstory"],
            llm=llm,
            verbose=True,
        ),
    }


def create_tasks(agents: dict[str, Agent], startup_idea: str) -> list[Task]:
    """创建4个Task，注入创业方向参数"""
    tasks_config = load_yaml("tasks.yaml")

    return [
        Task(
            description=tasks_config["market_analysis"]["description"].format(
                startup_idea=startup_idea
            ),
            expected_output=tasks_config["market_analysis"]["expected_output"],
            agent=agents["market_analyst"],
        ),
        Task(
            description=tasks_config["competitor_analysis"]["description"].format(
                startup_idea=startup_idea
            ),
            expected_output=tasks_config["competitor_analysis"]["expected_output"],
            agent=agents["competitor_researcher"],
        ),
        Task(
            description=tasks_config["risk_review"]["description"].format(
                startup_idea=startup_idea
            ),
            expected_output=tasks_config["risk_review"]["expected_output"],
            agent=agents["risk_reviewer"],
        ),
        Task(
            description=tasks_config["strategy_report"]["description"].format(
                startup_idea=startup_idea
            ),
            expected_output=tasks_config["strategy_report"]["expected_output"],
            agent=agents["strategy_advisor"],
        ),
    ]


def run_analysis(startup_idea: str, save_to: str | None = None) -> str:
    """
    执行创业机会分析

    Args:
        startup_idea: 创业方向描述，例如 "面向中小企业的AI Agent客服平台"
        save_to: 报告保存路径（可选）

    Returns:
        完整的分析报告（Markdown格式）
    """
    agents = create_agents()
    tasks = create_tasks(agents, startup_idea)
    llm = get_llm()

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.hierarchical,
        manager_llm=llm,
        verbose=True,
    )

    result = crew.kickoff()

    if save_to:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        with open(save_to, "w", encoding="utf-8") as f:
            f.write(f"# 创业机会分析报告\n\n")
            f.write(f"## 分析方向：{startup_idea}\n\n")
            f.write(str(result.raw))
        print(f"\n报告已保存至: {save_to}")

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
