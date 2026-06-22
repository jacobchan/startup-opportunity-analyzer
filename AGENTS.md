# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

A multi-agent startup opportunity analysis system built on **CrewAI** with two execution surfaces:

1. **CLI / hierarchical mode** — `python -m src.crew "..."` runs a 5-agent hierarchical crew and emits a Go/No-Go/Conditional-Go report.
2. **Web / 3-round deliberation mode** — `POST /runs` spawns a stateful `DeliberationEngine` that runs Round 1 (independent analysis), Round 2 (cross-challenge), Round 3 (strategy synthesis), streaming events over SSE and checkpointing after every agent for crash-recovery via `POST /runs/{id}/resume`.

The project is Chinese-language focused — all prompts, agent roles, and output are in Chinese.

## Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# CLI - hierarchical mode
python -m examples.analyze_ai_agent
python -m examples.analyze_saas
python -m src.crew "你的创业方向描述" [output_path]

# Web - 3-round deliberation mode
uvicorn src.web.app:create_app --factory --host 0.0.0.0 --port 8000

# Frontend dev (optional)
cd frontend && npm install && npm run dev

# Run tests
pytest tests/

# Lint
ruff check src/ tests/
```

## Architecture

### Agents (5)

Defined in `src/config/agents.yaml` (role/goal/backstory):

- `market_analyst` — TAM/SAM/SOM, growth trends, user personas
- `competitor_researcher` — competitive landscape, differentiation opportunities
- `finance_analyst` — LTV/CAC model, pricing strategy, funding plan
- `risk_reviewer` — multi-dimensional risk assessment
- `strategy_advisor` — synthesises all inputs into Go/No-Go/Conditional-Go (CLI manager / R3 agent in web)

### Two execution surfaces

| Surface | Driver | Process | Resume |
| --- | --- | --- | --- |
| CLI | `src/crew.py` (`StartupAnalyzerCrew.crew()`) | `Process.hierarchical` (strategy_advisor as manager) | No |
| Web | `src/deliberation/engine.py` (`DeliberationEngine`) | 3 explicit rounds, checkpointed after every agent | Yes (`POST /runs/{id}/resume`) |

### Config-driven design

- `src/config/agents.yaml` — role, goal, backstory for each agent
- `src/config/tasks.yaml` — task descriptions with `{startup_idea}` placeholder; per-task `expected_output` JSON schemas
- `src/config/settings.py` — env vars (`LLM_MODEL`, API keys) and the shared `build_llm()` factory

### Tools

- `src/tools/search_tool.py` wraps `SerperDevTool`
- `src/tools/web_scraper.py` wraps `ScrapeWebsiteTool`
- `src/tools/challenge_tool.py` — R2 cross-challenge tool used only by the deliberation engine

### Web layer

- `src/web/app.py` — FastAPI factory; mounts the React `frontend/dist/` as static files
- `src/web/routes/runs.py` — `POST /runs`, `GET /runs`, `GET /runs/{id}`, `DELETE /runs/{id}`, `GET /runs/{id}/report`
- `src/web/routes/stream.py` — `GET /runs/{id}/stream` (SSE)
- `src/web/routes/evidence.py` — `GET /evidence/{id}` (lookup by evidence id)
- `src/web/routes/resume.py` — `POST /runs/{id}/resume`
- `src/web/runner.py` — background task drivers (`run_deliberation`, `resume_deliberation`)
- `src/web/run_registry.py` — in-process `EventBus` registry keyed by run_id

### Storage

- `src/storage/db.py` — SQLAlchemy engine, `init_db()` with lightweight migration for the `deliberation_state` column
- `src/storage/models.py` — `Run`, `Evidence`, `Challenge`
- `src/storage/repository.py` — data access helpers

### LLM switching

Controlled by the `LLM_MODEL` env var, dispatched by `build_llm()` in `src/config/settings.py`. When the model name contains `"deepseek"`, the factory uses `DEEPSEEK_API_KEY` + `DEEPSEEK_BASE_URL`. Otherwise it falls through to a plain `LLM(model=...)` (Anthropic Claude).

### Output

- CLI: `run_analysis(startup_idea, save_to)` returns raw markdown and optionally writes to a file
- Web: final report stored as JSON in `Run.final_report`; R1 outputs mirrored in `Run.round1_outputs` for frontend mid-run restoration

## When adding a new agent

1. Add its role/goal/backstory to `src/config/agents.yaml`
2. Add a task to `src/config/tasks.yaml` (with `{startup_idea}` placeholder and a JSON `expected_output`)
3. Wire it into `create_agents()` / `create_tasks()` in `src/crew.py`
4. If it should run in the web deliberation flow, also add it to the relevant `R*_AGENTS` tuple in `src/deliberation/engine.py` and update the `tools_map` in `src/web/runner.py`

## Key Design Decisions

- **CrewAI over LangGraph**: role-driven agents match the "simulate team collaboration" pattern better than state-graph control flow.
- **Hierarchical over sequential for CLI**: the Manager (strategy_advisor) dynamically synthesizes rather than passively receiving prior output.
- **Deliberation engine for web**: 3 explicit rounds with checkpointing + resume > relying on a single CrewAI kickoff.
- **YAML config over code**: agent roles and task prompts live in YAML for easy tuning without touching Python.
- **Description-driven output over Pydantic schema for LLM prompts**: CrewAI's Pydantic output has compatibility issues in hierarchical mode; natural language `expected_output` fields with embedded JSON templates work better in practice. Pydantic models in `src/schemas.py` are kept for downstream validation and for the web API contract.
- Each full web analysis costs ~$0.7–1.2 and takes 12–18 minutes (~60–100K tokens).

## Required Environment Variables

See `.env.example`. Minimum required: `DEEPSEEK_API_KEY` and `SERPER_API_KEY`.
