"""基础测试 - 验证Agent和Task配置加载"""

from pathlib import Path


def test_agents_config_loads():
    """验证agents.yaml配置正确加载"""
    import yaml

    config_path = Path(__file__).parent.parent / "src" / "config" / "agents.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    expected_agents = [
        "market_analyst",
        "competitor_researcher",
        "finance_analyst",
        "risk_reviewer",
        "strategy_advisor",
    ]
    for name in expected_agents:
        assert name in config, f"Missing agent: {name}"

    for name, agent in config.items():
        assert "role" in agent, f"{name} missing role"
        assert "goal" in agent, f"{name} missing goal"
        assert "backstory" in agent, f"{name} missing backstory"


def test_tasks_config_loads():
    """验证tasks.yaml配置正确加载"""
    import yaml

    config_path = Path(__file__).parent.parent / "src" / "config" / "tasks.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    expected_tasks = [
        "market_analysis",
        "competitor_analysis",
        "finance_analysis",
        "risk_review",
        "strategy_report",
    ]
    for name in expected_tasks:
        assert name in config, f"Missing task: {name}"

    for name, task in config.items():
        assert "description" in task, f"{name} missing description"
        assert "expected_output" in task, f"{name} missing expected_output"
        assert "agent" in task, f"{name} missing agent"
        assert "{startup_idea}" in task["description"], f"{name} missing startup_idea placeholder"


def test_crew_class_creation():
    """验证StartupAnalyzerCrew类能正确实例化，agents和tasks配置加载"""
    from src.crew import StartupAnalyzerCrew

    analyzer = StartupAnalyzerCrew()
    assert analyzer.agents_config is not None
    assert analyzer.tasks_config is not None

    expected_agents = ["market_analyst", "competitor_researcher", "finance_analyst", "risk_reviewer", "strategy_advisor"]
    for name in expected_agents:
        assert name in analyzer.agents_config, f"Missing agent config: {name}"

    expected_tasks = ["market_analysis", "competitor_analysis", "finance_analysis", "risk_review", "strategy_report"]
    for name in expected_tasks:
        assert name in analyzer.tasks_config, f"Missing task config: {name}"


def test_crew_builds():
    """验证crew()能正确构建Crew对象"""
    from src.crew import StartupAnalyzerCrew
    from crewai import Crew, Process

    analyzer = StartupAnalyzerCrew()
    crew = analyzer.crew()

    assert isinstance(crew, Crew)
    assert crew.process == Process.hierarchical
    assert len(crew.tasks) == 5
    assert crew.manager_agent is not None


def test_schemas_import():
    """验证所有Pydantic schema能正确导入"""
    from src.schemas import (
        MarketAnalysisOutput,
        CompetitorAnalysisOutput,
        FinanceAnalysisOutput,
        RiskReviewOutput,
        StrategyReportOutput,
    )

    # 验证Pydantic模型有字段定义
    assert len(MarketAnalysisOutput.model_fields) > 0
    assert len(CompetitorAnalysisOutput.model_fields) > 0
    assert len(FinanceAnalysisOutput.model_fields) > 0
    assert len(RiskReviewOutput.model_fields) > 0
    assert len(StrategyReportOutput.model_fields) > 0


def test_finance_schema_structure():
    """验证财务分析schema包含LTV/CAC关键字段"""
    from src.schemas import FinanceAnalysisOutput

    fields = FinanceAnalysisOutput.model_fields
    assert "ltv_analysis" in fields, "Missing ltv_analysis field"
    assert "cac_analysis" in fields, "Missing cac_analysis field"
    assert "unit_economics" in fields, "Missing unit_economics field"
    assert "pricing_strategy" in fields, "Missing pricing_strategy field"
    assert "funding_requirements" in fields, "Missing funding_requirements field"


def test_task_context_dependencies():
    """验证任务context依赖正确设置"""
    from src.crew import StartupAnalyzerCrew

    analyzer = StartupAnalyzerCrew()
    crew = analyzer.crew()

    # tasks order: [market, competitor, finance, risk, strategy]
    market, competitor, finance, risk, strategy = crew.tasks

    # risk depends on the 3 analysis tasks
    risk_ctx_ids = [t.id for t in risk.context]
    assert market.id in risk_ctx_ids, "risk should depend on market"
    assert competitor.id in risk_ctx_ids, "risk should depend on competitor"
    assert finance.id in risk_ctx_ids, "risk should depend on finance"

    # strategy depends on all 4
    strategy_ctx_ids = [t.id for t in strategy.context]
    assert market.id in strategy_ctx_ids, "strategy should depend on market"
    assert competitor.id in strategy_ctx_ids, "strategy should depend on competitor"
    assert finance.id in strategy_ctx_ids, "strategy should depend on finance"
    assert risk.id in strategy_ctx_ids, "strategy should depend on risk"
