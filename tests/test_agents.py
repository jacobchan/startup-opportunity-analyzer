"""基础测试 - 验证Agent和Task配置加载"""

import pytest
from pathlib import Path


def test_agents_config_loads():
    """验证agents.yaml配置正确加载"""
    import yaml

    config_path = Path(__file__).parent.parent / "src" / "config" / "agents.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "market_analyst" in config
    assert "competitor_researcher" in config
    assert "risk_reviewer" in config
    assert "strategy_advisor" in config

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

    assert "market_analysis" in config
    assert "competitor_analysis" in config
    assert "risk_review" in config
    assert "strategy_report" in config

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
    assert "market_analyst" in analyzer.agents_config
    assert "strategy_advisor" in analyzer.agents_config
    assert "market_analysis" in analyzer.tasks_config
    assert "strategy_report" in analyzer.tasks_config


def test_crew_builds():
    """验证crew()能正确构建Crew对象"""
    from src.crew import StartupAnalyzerCrew
    from crewai import Crew, Process

    analyzer = StartupAnalyzerCrew()
    crew = analyzer.crew()

    assert isinstance(crew, Crew)
    assert crew.process == Process.hierarchical
    assert len(crew.tasks) == 4
    assert crew.manager_agent is not None
