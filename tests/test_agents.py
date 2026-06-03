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


def test_agent_creation():
    """验证Agent对象能正确创建"""
    from src.crew import create_agents

    agents = create_agents()
    assert len(agents) == 4
    assert all(name in agents for name in [
        "market_analyst", "competitor_researcher", "risk_reviewer", "strategy_advisor"
    ])


def test_task_creation():
    """验证Task对象能正确创建"""
    from src.crew import create_tasks, create_agents

    agents = create_agents()
    tasks = create_tasks(agents, "测试创业方向")
    assert len(tasks) == 4
