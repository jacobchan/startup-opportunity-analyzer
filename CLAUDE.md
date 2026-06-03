# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-agent startup opportunity analysis system built on **CrewAI**. Four collaborative agents (market analyst, competitor researcher, risk reviewer, strategy advisor) produce a structured Go/No-Go assessment report for a given startup idea. The project is Chinese-language focused — all prompts, agent roles, and output are in Chinese.

## Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run analysis (two example entry points)
python -m examples.analyze_ai_agent
python -m examples.analyze_saas

# Run with custom idea from CLI
python src/crew.py "你的创业方向描述"

# Run tests
pytest tests/

# Lint
ruff check src/ tests/
```

## Architecture

**Core flow**: `run_analysis()` in `src/crew.py` is the main entry point. It creates 4 agents, 4 tasks, assembles a `Crew` with `Process.hierarchical`, and calls `crew.kickoff()`.

**Agent hierarchy** (hierarchical process — strategy_advisor acts as Manager):
- `market_analyst` — TAM/SAM/SOM, growth trends, user personas
- `competitor_researcher` — competitive landscape, differentiation opportunities
- `risk_reviewer` — multi-dimensional risk assessment (tech, market, team, funding, policy)
- `strategy_advisor` — synthesizes all inputs into a Go/No-Go/Conditional-Go report (Manager role)

**Config-driven design**:
- `src/config/agents.yaml` — role, goal, backstory for each agent
- `src/config/tasks.yaml` — task descriptions with `{startup_idea}` placeholder injection
- `src/config/settings.py` — env vars (LLM_MODEL, API keys, output dir)

When adding a new agent: add its definition to `agents.yaml`, add its task to `tasks.yaml` (with `{startup_idea}` placeholder), then wire it into `create_agents()` and `create_tasks()` in `src/crew.py`.

**Tools**: `src/tools/search_tool.py` wraps `SerperDevTool`, `src/tools/web_scraper.py` wraps `ScrapeWebsiteTool`. Market analyst and competitor researcher get both tools; risk reviewer gets search only; strategy advisor gets none (it synthesizes).

**LLM switching**: Controlled by `LLM_MODEL` env var. Defaults to `deepseek-v4-pro`. When the model name contains "deepseek", it uses `DEEPSEEK_API_KEY` + `DEEPSEEK_BASE_URL`. Otherwise it falls through to Anthropic. See `get_llm()` in `src/crew.py`.

**Output**: `run_analysis(startup_idea, save_to)` returns raw markdown and optionally writes to a file. Example outputs go to `examples/output/`.

## Key Design Decisions

- **CrewAI over LangGraph**: role-driven agents match the "simulate team collaboration" pattern better than state-graph control flow.
- **Hierarchical over sequential**: the Manager (strategy_advisor) dynamically synthesizes rather than passively receiving prior output.
- **YAML config over code**: agent roles and task prompts live in YAML for easy tuning without touching Python.
- **Description-driven output over Pydantic schema**: CrewAI's Pydantic output has compatibility issues in hierarchical mode; natural language `expected_output` fields work better in practice.
- Each full analysis run costs ~$0.5-1.0 and takes 10-15 minutes (~50-80K tokens).

## Required Environment Variables

See `.env.example`. Minimum required: `DEEPSEEK_API_KEY` and `SERPER_API_KEY`.
