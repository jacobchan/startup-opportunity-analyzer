"""
创业机会分析智能体 - Crew定义

基于CrewAI的hierarchical process，5个Agent协作完成创业机会评估：
1. 市场分析师 → TAM/SAM/SOM、增长趋势、用户画像 → JSON
2. 竞品调研员 → 竞品分析、差异化机会 → JSON
3. 财务分析师 → LTV/CAC模型、定价策略、资金需求 → JSON
4. 风险评审员 → 多维度风险评估 → JSON
5. 战略顾问（Manager） → 综合研判，输出最终报告 → JSON
"""

import json
from pathlib import Path
from typing import List

from crewai import Agent, Crew, Task, Process, LLM
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff

from src.tools.search_tool import search_tool
from src.tools.web_scraper import scrape_tool
from src.tools.challenge_tool import make_challenge_tool
from src.config.settings import LLM_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from src.storage import get_session, get_challenges_for_run


def _extract_json(text: str) -> str:
    """从LLM输出中提取JSON内容（处理markdown代码块包裹等情况）"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首尾的```行
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end])
    return text.strip()


def _parse_json(text: str) -> dict:
    """将LLM输出解析为JSON dict，解析失败则返回包含原始文本的dict"""
    cleaned = _extract_json(str(text))
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_output": str(text), "parse_error": True}


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
                f.write("# 创业机会分析报告\n\n")
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
    def finance_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["finance_analyst"],
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
    def finance_analysis(self) -> Task:
        return Task(config=self.tasks_config["finance_analysis"])

    @task
    def risk_review(self) -> Task:
        return Task(config=self.tasks_config["risk_review"])

    @task
    def strategy_report(self) -> Task:
        return Task(config=self.tasks_config["strategy_report"])

    @crew
    def crew(self) -> Crew:
        # self.tasks order: [market, competitor, finance, risk, strategy]
        market, competitor, finance, risk, strategy = self.tasks

        # risk depends on the 3 analysis tasks
        risk.context = [market, competitor, finance]
        # strategy synthesizes everything
        strategy.context = [market, competitor, finance, risk]

        # strategy_advisor as manager, others as workers
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

    # ── 3-round deliberation methods ──────────────────────────

    _ROUND1_AGENTS = [
        ("market_analyst", "market_analysis"),
        ("competitor_researcher", "competitor_analysis"),
        ("finance_analyst", "finance_analysis"),
    ]

    def run_round1(self, startup_idea: str, run_id: str, publisher) -> dict:
        """R1: 4 worker agents analyze independently. Returns {agent_name: output_dict}."""
        self._startup_idea = startup_idea
        results: dict = {}

        # Run market, competitor, finance (independent)
        for agent_key, task_key in self._ROUND1_AGENTS:
            publisher({"type": "agent.start", "agent": agent_key, "round": "round1"})
            agent = getattr(self, agent_key)()
            task = Task(config=self.tasks_config[task_key])
            crew = Crew(agents=[agent], tasks=[task], verbose=True)
            result = crew.kickoff(inputs={"startup_idea": startup_idea})
            results[agent_key] = _parse_json(str(result.raw))
            publisher({
                "type": "agent.end", "agent": agent_key, "round": "round1",
                "output_summary": results[agent_key],
            })

        # Risk depends on the first 3 — inject their outputs into the task
        publisher({"type": "agent.start", "agent": "risk_reviewer", "round": "round1"})
        risk_agent = self.risk_reviewer()
        risk_task = Task(
            description=(
                self.tasks_config["risk_review"]["description"]
                + "\n\n以下是前三项分析的结果，请基于这些数据完成风险评估：\n"
                + json.dumps(
                    {k: results[k] for k in ["market_analyst", "competitor_researcher", "finance_analyst"]},
                    ensure_ascii=False, indent=2,
                )
            ),
            expected_output=self.tasks_config["risk_review"]["expected_output"],
            agent=risk_agent,
        )
        risk_crew = Crew(agents=[risk_agent], tasks=[risk_task], verbose=True)
        risk_result = risk_crew.kickoff(inputs={"startup_idea": startup_idea})
        results["risk_reviewer"] = _parse_json(str(risk_result.raw))
        publisher({
            "type": "agent.end", "agent": "risk_reviewer", "round": "round1",
            "output_summary": results["risk_reviewer"],
        })

        return results

    def run_round2(self, r1_outputs: dict, run_id: str, publisher) -> list[dict]:
        """R2: cross-challenge — each agent reviews others' outputs and issues challenges."""
        r1_json = json.dumps(r1_outputs, ensure_ascii=False, indent=2)
        all_challenges: list[dict] = []
        seen_ids: set[str] = set()

        for agent_key, _task_key in self._ROUND1_AGENTS:
            publisher({"type": "agent.start", "agent": agent_key, "round": "round2"})

            agent = getattr(self, agent_key)()
            agent.tools = [make_challenge_tool(run_id=run_id, agent_name=agent_key)]

            task = Task(
                description=self.tasks_config["round2_challenge"]["description"],
                expected_output=self.tasks_config["round2_challenge"]["expected_output"],
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[task], verbose=True)
            crew.kickoff(inputs={
                "startup_idea": self._startup_idea,
                "round1_outputs": r1_json,
            })

            # Collect challenges issued by this agent in this round
            session = get_session()
            for ch in get_challenges_for_run(session, run_id):
                if ch.issuer == agent_key and ch.challenge_id not in seen_ids:
                    seen_ids.add(ch.challenge_id)
                    challenge_dict = {
                        "challenge_id": ch.challenge_id,
                        "issuer": ch.issuer,
                        "target": ch.target,
                        "claim": ch.claim,
                        "reason": ch.reason,
                    }
                    all_challenges.append(challenge_dict)
                    publisher({
                        "type": "challenge.issued",
                        **challenge_dict,
                    })

            publisher({"type": "agent.end", "agent": agent_key, "round": "round2"})

        return all_challenges

    def run_round3(
        self, r1_outputs: dict, challenges: list[dict], run_id: str, publisher,
    ) -> dict:
        """R3: strategy advisor synthesizes everything into the final Go/No-Go report."""
        publisher({"type": "agent.start", "agent": "strategy_advisor", "round": "round3"})

        r1_json = json.dumps(r1_outputs, ensure_ascii=False, indent=2)
        challenges_json = json.dumps(challenges, ensure_ascii=False, indent=2)

        strategy_agent = self.strategy_advisor()
        task = Task(
            description=(
                self.tasks_config["strategy_report"]["description"]
                + f"\n\n以下是四个分析 agent 的详细输出：\n{r1_json}"
                + f"\n\n以下是交叉挑战记录：\n{challenges_json}"
            ),
            expected_output=self.tasks_config["strategy_report"]["expected_output"],
            agent=strategy_agent,
        )
        crew = Crew(agents=[strategy_agent], tasks=[task], verbose=True)
        result = crew.kickoff(inputs={"startup_idea": self._startup_idea})

        output = _parse_json(str(result.raw))
        publisher({
            "type": "agent.end", "agent": "strategy_advisor", "round": "round3",
            "output_summary": output,
        })
        return output


def run_analysis(startup_idea: str, save_to: str | None = None) -> str:
    """
    执行创业机会分析

    Args:
        startup_idea: 创业方向描述，例如 "面向中小企业的AI Agent客服平台"
        save_to: 报告保存路径（可选）

    Returns:
        完整的分析报告（JSON格式）。如果LLM未严格返回JSON，则返回原始文本。
    """
    analyzer = StartupAnalyzerCrew()
    if save_to:
        analyzer._save_to = save_to

    result = analyzer.crew().kickoff(
        inputs={"startup_idea": startup_idea}
    )

    raw = str(result.raw)
    cleaned = _extract_json(raw)

    try:
        parsed = json.loads(cleaned)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return raw


if __name__ == "__main__":
    import sys

    idea = sys.argv[1] if len(sys.argv) > 1 else "面向中小企业的AI Agent客服平台"
    output = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"正在分析创业方向: {idea}")
    print(f"使用模型: {LLM_MODEL}\n")
    report = run_analysis(idea, save_to=output)
    print("\n" + "=" * 60)
    print(report)
