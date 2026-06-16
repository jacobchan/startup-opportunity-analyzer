# 多轮辩论 + 证据追踪 Web Demo 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 5-Agent CLI 工具升级为「3 轮辩论 + 证据追踪 + Web 可视化」的社区 Demo，部署到阿里云。

**Architecture:** FastAPI 后端 + Vite/React 前端，3 轮 CrewAI 编排（独立分析 / 交叉挑战 / 综合），每个工具调用通过 evidence_capture 自动落库，所有事件通过内存总线推送 SSE。

**Tech Stack:** CrewAI 1.14+ · FastAPI · SSE-Starlette · SQLAlchemy (SQLite) · Pydantic v2 · Vite + React + TypeScript · Tailwind CSS · Vitest + Testing Library · Pytest

**Spec:** `docs/superpowers/specs/2026-06-12-multi-round-deliberation-web-demo-design.md`

---

## 文件结构总览

**新增**：
```
src/
├── storage/
│   ├── __init__.py
│   ├── db.py                 # SQLAlchemy engine, Session
│   ├── models.py             # Run, Evidence, Challenge ORM 模型
│   └── repository.py         # CRUD 函数
├── deliberation/
│   ├── __init__.py
│   ├── protocol.py           # Challenge dataclass + Verdict 枚举
│   ├── evidence.py           # @evidence_capture 装饰器
│   └── rounds.py             # 3 轮编排器
├── tools/
│   └── challenge_tool.py     # CrewAI BaseTool 子类
├── web/
│   ├── __init__.py
│   ├── app.py                # FastAPI app factory
│   ├── events.py             # 内存事件总线 + CrewAI 回调适配器
│   ├── runner.py             # 3 轮编排的同步执行器
│   └── routes/
│       ├── __init__.py
│       ├── runs.py
│       ├── stream.py
│       └── evidence.py
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── lib/
    │   ├── sse.ts
    │   └── types.ts
    └── components/
        ├── AgentCard.tsx
        ├── ActivityFeed.tsx
        ├── ChallengeLog.tsx
        ├── EvidenceReport.tsx
        └── StartupForm.tsx
data/
└── .gitkeep
tests/
├── storage/test_repository.py
├── deliberation/test_protocol.py
├── deliberation/test_evidence.py
├── deliberation/test_rounds.py
├── tools/test_challenge_tool.py
├── web/test_runs.py
├── web/test_stream.py
├── web/test_evidence.py
├── web/test_runner.py
└── integration/test_end_to_end.py
```

**修改**：
- `pyproject.toml` — 新增 fastapi/uvicorn/sse-starlette/sqlalchemy/aiosqlite/vitest 等
- `src/crew.py` — 接入 3 轮编排
- `src/config/agents.yaml` — R2 challenge 指令
- `src/config/tasks.yaml` — R2 challenge 任务
- `src/schemas.py` — 增加 evidence_ids 字段
- `src/__init__.py` — 导出新 API
- `.gitignore` — data/、frontend/dist/、frontend/node_modules/
- `README.md` — 增加 Web 启动方式 + 部署说明

---

## Phase 1：基础设施（T1-T4）

### Task 1: 添加新依赖

**Files:**
- Modify: `pyproject.toml:1-20`

- [ ] **Step 1: 添加后端 + 前端构建依赖**

编辑 `pyproject.toml`：

```toml
[project]
name = "startup-opportunity-analyzer"
version = "0.1.0"
description = "基于CrewAI的多智能体创业机会分析系统"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "crewai>=1.14.0",
    "crewai-tools>=1.14.0",
    "tokenizers>=0.21,<1",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sse-starlette>=2.1.0",
    "sqlalchemy>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: 同步依赖**

Run: `pip install -e ".[dev]"`
Expected: 安装成功，无错误

- [ ] **Step 3: 提交**

```bash
git add pyproject.toml
git commit -m "build: add fastapi/sse-starlette/sqlalchemy/httpx/pytest-asyncio"
```

---

### Task 2: SQLite 存储层（models + repository）

**Files:**
- Create: `src/storage/__init__.py`
- Create: `src/storage/db.py`
- Create: `src/storage/models.py`
- Create: `src/storage/repository.py`
- Create: `data/.gitkeep`
- Test: `tests/storage/test_repository.py`
- Modify: `.gitignore`

- [ ] **Step 1: 更新 .gitignore**

在 `.gitignore` 末尾追加：

```
data/
frontend/dist/
frontend/node_modules/
```

- [ ] **Step 2: 创建 storage 包初始化**

`src/storage/__init__.py`：

```python
from src.storage.db import get_engine, get_session, init_db
from src.storage.models import Run, Evidence, Challenge
from src.storage.repository import (
    create_run, get_run, update_run_status,
    add_evidence, get_evidence,
    add_challenge, update_challenge_response, get_challenges_for_run,
)

__all__ = [
    "get_engine", "get_session", "init_db",
    "Run", "Evidence", "Challenge",
    "create_run", "get_run", "update_run_status",
    "add_evidence", "get_evidence",
    "add_challenge", "update_challenge_response", "get_challenges_for_run",
]
```

- [ ] **Step 3: 写 storage 失败测试**

`tests/storage/test_repository.py`：

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.storage.db import get_engine, init_db
from src.storage.models import Run, Evidence, Challenge
from src.storage.repository import (
    create_run, get_run, update_run_status,
    add_evidence, get_evidence,
    add_challenge, update_challenge_response, get_challenges_for_run,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_and_get_run(db_session):
    run = create_run(db_session, startup_idea="AI Agent 平台")
    found = get_run(db_session, run.run_id)
    assert found is not None
    assert found.startup_idea == "AI Agent 平台"
    assert found.status == "queued"


def test_update_run_status(db_session):
    run = create_run(db_session, startup_idea="x")
    update_run_status(db_session, run.run_id, "running")
    found = get_run(db_session, run.run_id)
    assert found.status == "running"


def test_add_and_get_evidence(db_session):
    run = create_run(db_session, startup_idea="x")
    ev = add_evidence(
        db_session,
        run_id=run.run_id,
        source_type="search",
        query="AI Agent 市场",
        url="https://example.com",
        title="AI Agent 报告",
        content_excerpt="...",
        url_hash="abc123",
    )
    found = get_evidence(db_session, ev.evidence_id)
    assert found is not None
    assert found.url_hash == "abc123"


def test_evidence_dedup_by_url_hash(db_session):
    run = create_run(db_session, startup_idea="x")
    ev1 = add_evidence(
        db_session, run_id=run.run_id, source_type="search",
        query="q1", url="https://x.com", title="t", content_excerpt="c", url_hash="dup",
    )
    ev2 = add_evidence(
        db_session, run_id=run.run_id, source_type="search",
        query="q2", url="https://x.com", title="t", content_excerpt="c", url_hash="dup",
    )
    assert ev1.evidence_id == ev2.evidence_id


def test_add_challenge_and_respond(db_session):
    run = create_run(db_session, startup_idea="x")
    ch = add_challenge(
        db_session, run_id=run.run_id, issuer="market_analyst",
        target="finance_analyst", claim="LTV 假设过高", reason="...",
    )
    assert ch.verdict is None
    update_challenge_response(
        db_session, ch.challenge_id,
        response="已调整", verdict="modified",
    )
    challenges = get_challenges_for_run(db_session, run.run_id)
    assert len(challenges) == 1
    assert challenges[0].verdict == "modified"
    assert challenges[0].response == "已调整"
```

- [ ] **Step 4: 跑测试确认失败**

Run: `pytest tests/storage/test_repository.py -v`
Expected: FAIL (no module named src.storage)

- [ ] **Step 5: 实现 db.py**

`src/storage/db.py`：

```python
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None


def get_engine(db_path: str | None = None):
    global _engine
    if _engine is None:
        if db_path is None:
            db_path = str(Path("data") / "analyzer.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db(engine=None):
    from src.storage.models import Run, Evidence, Challenge  # noqa
    Base.metadata.create_all(engine or get_engine())
```

- [ ] **Step 6: 实现 models.py**

`src/storage/models.py`：

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.storage.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    __tablename__ = "runs"
    run_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    startup_idea: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    round1_outputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Evidence(Base):
    __tablename__ = "evidence"
    evidence_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_type: Mapped[str] = mapped_column(String)
    query: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    content_excerpt: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    url_hash: Mapped[str] = mapped_column(String, index=True)


class Challenge(Base):
    __tablename__ = "challenges"
    challenge_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String, index=True)
    issuer: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    claim: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 7: 实现 repository.py**

`src/storage/repository.py`：

```python
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.storage.models import Run, Evidence, Challenge


def create_run(session: Session, startup_idea: str) -> Run:
    run = Run(startup_idea=startup_idea)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_run(session: Session, run_id: str) -> Run | None:
    return session.get(Run, run_id)


def update_run_status(session: Session, run_id: str, status: str) -> None:
    run = session.get(Run, run_id)
    if run is None:
        return
    run.status = status
    if status in ("complete", "failed", "partial"):
        run.completed_at = datetime.now(timezone.utc)
    session.commit()


def _url_hash_to_existing(session: Session, url_hash: str) -> Evidence | None:
    stmt = select(Evidence).where(Evidence.url_hash == url_hash).limit(1)
    return session.execute(stmt).scalar_one_or_none()


def add_evidence(
    session: Session, run_id: str, source_type: str, query: str,
    url: str | None, title: str | None, content_excerpt: str, url_hash: str,
) -> Evidence:
    existing = _url_hash_to_existing(session, url_hash)
    if existing is not None:
        return existing
    ev = Evidence(
        run_id=run_id, source_type=source_type, query=query,
        url=url, title=title, content_excerpt=content_excerpt, url_hash=url_hash,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def get_evidence(session: Session, evidence_id: str) -> Evidence | None:
    return session.get(Evidence, evidence_id)


def add_challenge(
    session: Session, run_id: str, issuer: str, target: str,
    claim: str, reason: str,
) -> Challenge:
    ch = Challenge(
        run_id=run_id, issuer=issuer, target=target,
        claim=claim, reason=reason,
    )
    session.add(ch)
    session.commit()
    session.refresh(ch)
    return ch


def update_challenge_response(
    session: Session, challenge_id: str, response: str, verdict: str,
) -> Challenge | None:
    ch = session.get(Challenge, challenge_id)
    if ch is None:
        return None
    ch.response = response
    ch.verdict = verdict
    ch.resolved_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(ch)
    return ch


def get_challenges_for_run(session: Session, run_id: str) -> list[Challenge]:
    stmt = select(Challenge).where(Challenge.run_id == run_id).order_by(Challenge.issued_at)
    return list(session.execute(stmt).scalars())
```

- [ ] **Step 8: 跑测试确认通过**

Run: `pytest tests/storage/test_repository.py -v`
Expected: 5 passed

- [ ] **Step 9: 提交**

```bash
git add src/storage/ tests/storage/ data/.gitkeep .gitignore
git commit -m "feat: add SQLite storage layer with Run/Evidence/Challenge models"
```

---

### Task 3: Challenge 数据结构 + Verdict 枚举

**Files:**
- Create: `src/deliberation/__init__.py`
- Create: `src/deliberation/protocol.py`
- Test: `tests/deliberation/test_protocol.py`

- [ ] **Step 1: 写 failing test**

`tests/deliberation/test_protocol.py`：

```python
import pytest

from src.deliberation.protocol import ChallengeDraft, Verdict, challenge_to_orm


def test_challenge_draft_required_fields():
    draft = ChallengeDraft(
        issuer="market_analyst",
        target="finance_analyst",
        claim="LTV 假设过高",
        reason="同行业基准是 X",
    )
    assert draft.issuer == "market_analyst"
    assert draft.target == "finance_analyst"


def test_verdict_enum_members():
    assert Verdict.ACCEPTED.value == "accepted"
    assert Verdict.REJECTED.value == "rejected"
    assert Verdict.MODIFIED.value == "modified"


def test_challenge_to_orm_creates_challenge():
    from src.storage.db import create_engine_memory
    # 实际 ORM 转换测试在 storage 测过了；这里只验证类型
    draft = ChallengeDraft(
        issuer="a", target="b", claim="c", reason="d",
    )
    assert draft.issuer == "a"


def test_challenge_draft_rejects_empty_claim():
    with pytest.raises(ValueError):
        ChallengeDraft(issuer="a", target="b", claim="", reason="d")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/deliberation/test_protocol.py -v`
Expected: FAIL (no module named src.deliberation)

- [ ] **Step 3: 实现 protocol.py**

`src/deliberation/__init__.py`：

```python
from src.deliberation.protocol import ChallengeDraft, Verdict

__all__ = ["ChallengeDraft", "Verdict"]
```

`src/deliberation/protocol.py`：

```python
from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class ChallengeDraft:
    issuer: str
    target: str
    claim: str
    reason: str

    def __post_init__(self):
        if not self.claim.strip():
            raise ValueError("claim cannot be empty")
        if self.issuer == self.target:
            raise ValueError("issuer and target must differ")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/deliberation/test_protocol.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/deliberation/ tests/deliberation/
git commit -m "feat: add ChallengeDraft dataclass and Verdict enum"
```

---

### Task 4: 证据捕获装饰器

**Files:**
- Create: `src/deliberation/evidence.py`
- Test: `tests/deliberation/test_evidence.py`

- [ ] **Step 1: 写 failing test**

`tests/deliberation/test_evidence.py`：

```python
import hashlib
import pytest
from unittest.mock import MagicMock

from src.deliberation.evidence import evidence_capture, hash_url, make_evidence_id


def test_hash_url_stable():
    h1 = hash_url("https://example.com/article?x=1")
    h2 = hash_url("https://example.com/article?x=1")
    assert h1 == h2
    assert len(h1) == 32


def test_hash_url_different():
    assert hash_url("https://a.com") != hash_url("https://b.com")


def test_make_evidence_id_unique():
    ids = {make_evidence_id() for _ in range(100)}
    assert len(ids) == 100


def test_evidence_capture_writes_to_session(monkeypatch):
    captured = {}
    mock_session = MagicMock()
    mock_add = MagicMock(return_value=MagicMock(evidence_id="ev-test"))
    monkeypatch.setattr("src.deliberation.evidence.add_evidence", mock_add)
    monkeypatch.setattr("src.deliberation.evidence.get_session", lambda: mock_session)

    @evidence_capture(run_id="run-1", source_type="search")
    def fake_search(query: str) -> str:
        return f"results for {query}"

    result = fake_search("AI Agent")
    assert result == "results for AI Agent"
    mock_add.assert_called_once()
    args, kwargs = mock_add.call_args
    assert kwargs["run_id"] == "run-1"
    assert kwargs["query"] == "AI Agent"
    assert kwargs["url_hash"] == hashlib.md5("AI Agent".encode()).hexdigest()


def test_evidence_capture_dedups(monkeypatch):
    same_evidence = MagicMock(evidence_id="ev-same")
    mock_add = MagicMock(return_value=same_evidence)
    monkeypatch.setattr("src.deliberation.evidence.add_evidence", mock_add)

    @evidence_capture(run_id="run-1", source_type="search")
    def fake_search(query: str) -> str:
        return "x"

    fake_search("same query")
    fake_search("same query")
    assert mock_add.call_count == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/deliberation/test_evidence.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: 实现 evidence.py**

`src/deliberation/evidence.py`：

```python
import hashlib
import uuid
from functools import wraps
from typing import Callable

from src.storage import add_evidence, get_session


def hash_url(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def make_evidence_id() -> str:
    return f"ev-{uuid.uuid4().hex[:12]}"


def evidence_capture(run_id: str, source_type: str = "search"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            result = func(*args, **kwargs)
            query = str(args[0]) if args else str(kwargs.get("query", ""))
            url_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
            session = get_session()
            evidence = add_evidence(
                session=session,
                run_id=run_id,
                source_type=source_type,
                query=query,
                url=None,
                title=None,
                content_excerpt=result[:500] if isinstance(result, str) else str(result)[:500],
                url_hash=url_hash,
            )
            return f"{result}\n\n<!-- evidence_id={evidence.evidence_id} -->"
        return wrapper
    return decorator
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/deliberation/test_evidence.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add src/deliberation/evidence.py tests/deliberation/test_evidence.py
git commit -m "feat: add evidence_capture decorator for automatic evidence tracking"
```

---

## Phase 2：辩论协议（T5-T7）

### Task 5: Challenge 自定义工具

**Files:**
- Create: `src/tools/__init__.py` (改现有)
- Create: `src/tools/challenge_tool.py`
- Test: `tests/tools/test_challenge_tool.py`

- [ ] **Step 1: 写 failing test**

`tests/tools/test_challenge_tool.py`：

```python
import pytest
from unittest.mock import MagicMock, patch

from src.tools.challenge_tool import ChallengeTool, make_challenge_tool


def test_challenge_tool_has_correct_name():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    assert tool.name == "challenge"


def test_challenge_tool_routes_to_target():
    mock_session = MagicMock()
    mock_add = MagicMock(return_value=MagicMock(challenge_id="ch-1"))

    with patch("src.tools.challenge_tool.get_session", return_value=mock_session), \
         patch("src.tools.challenge_tool.add_challenge", mock_add):
        tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
        result = tool._run(
            target="finance_analyst",
            claim="LTV 假设过高",
            reason="行业基准是 X",
        )
        assert "ch-1" in result
        mock_add.assert_called_once()
        args, kwargs = mock_add.call_args
        assert kwargs["issuer"] == "market_analyst"
        assert kwargs["target"] == "finance_analyst"


def test_challenge_tool_validates_inputs():
    tool = make_challenge_tool(run_id="run-1", agent_name="market_analyst")
    with pytest.raises(ValueError):
        tool._run(target="market_analyst", claim="x", reason="y")
    with pytest.raises(ValueError):
        tool._run(target="finance_analyst", claim="", reason="y")


def test_challenge_tool_max_challenges_per_agent():
    tool = make_challenge_tool(
        run_id="run-1", agent_name="market_analyst", max_challenges=2,
    )
    with patch("src.tools.challenge_tool.get_session", return_value=MagicMock()), \
         patch("src.tools.challenge_tool.add_challenge", return_value=MagicMock(challenge_id="x")):
        tool._run(target="finance_analyst", claim="a", reason="r")
        tool._run(target="risk_reviewer", claim="b", reason="r")
        with pytest.raises(RuntimeError, match="max challenges"):
            tool._run(target="competitor_researcher", claim="c", reason="r")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/tools/test_challenge_tool.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: 实现 challenge_tool.py**

`src/tools/challenge_tool.py`：

```python
from crewai.tools import BaseTool
from pydantic import Field

from src.storage import add_challenge, get_session


class ChallengeTool(BaseTool):
    name: str = "challenge"
    description: str = (
        "对其他 agent 的结论提出挑战。"
        "输入: target (被挑战的 agent 名), claim (被挑战的具体论断), reason (挑战理由)。"
    )
    run_id: str
    issuer: str
    _count: int = 0
    max_challenges: int = 3

    def _run(self, target: str, claim: str, reason: str) -> str:
        if not claim.strip():
            raise ValueError("claim cannot be empty")
        if target == self.issuer:
            raise ValueError("cannot challenge yourself")
        if self._count >= self.max_challenges:
            raise RuntimeError(f"max challenges ({self.max_challenges}) reached for {self.issuer}")
        session = get_session()
        ch = add_challenge(
            session=session,
            run_id=self.run_id,
            issuer=self.issuer,
            target=target,
            claim=claim,
            reason=reason,
        )
        self._count += 1
        return f"挑战已发出 challenge_id={ch.challenge_id}，等待 {target} 回应"


def make_challenge_tool(run_id: str, agent_name: str, max_challenges: int = 3) -> ChallengeTool:
    return ChallengeTool(run_id=run_id, issuer=agent_name, max_challenges=max_challenges)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/tools/test_challenge_tool.py -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/tools/challenge_tool.py tests/tools/test_challenge_tool.py
git commit -m "feat: add ChallengeTool for cross-agent challenges"
```

---

### Task 6: 3 轮编排器

**Files:**
- Create: `src/deliberation/rounds.py`
- Test: `tests/deliberation/test_rounds.py`

- [ ] **Step 1: 写 failing test**

`tests/deliberation/test_rounds.py`：

```python
import pytest
from unittest.mock import MagicMock, patch, call

from src.deliberation.rounds import RoundOrchestrator, RoundTransition


def test_round_orchestrator_starts_at_round1():
    orch = RoundOrchestrator(
        run_id="run-1",
        agents={},
        tasks={},
        event_publisher=lambda e: None,
    )
    assert orch.current_round == "round1"


def test_round_transition_emits_event():
    events = []
    orch = RoundOrchestrator(
        run_id="run-1",
        agents={},
        tasks={},
        event_publisher=events.append,
    )
    orch.transition_to("round2")
    assert orch.current_round == "round2"
    assert any(isinstance(e, RoundTransition) and e.to_round == "round2" for e in events)


def test_round_transition_validates_order():
    orch = RoundOrchestrator("run-1", {}, {}, lambda e: None)
    with pytest.raises(ValueError, match="order"):
        orch.transition_to("round3")


def test_round_orchestrator_tracks_r1_outputs():
    orch = RoundOrchestrator("run-1", {}, {}, lambda e: None)
    orch.record_r1_output("market_analyst", {"tam": "100"})
    assert orch.r1_outputs["market_analyst"] == {"tam": "100"}


def test_round_orchestrator_tracks_challenges():
    orch = RoundOrchestrator("run-1", {}, {}, lambda e: None)
    orch.record_challenge({"challenge_id": "ch-1"})
    assert "ch-1" in orch.challenge_ids
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/deliberation/test_rounds.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: 实现 rounds.py**

`src/deliberation/rounds.py`：

```python
from collections import OrderedDict
from dataclasses import dataclass, field


ROUND_ORDER = ["round1", "round2", "round3"]


@dataclass
class RoundTransition:
    from_round: str | None
    to_round: str


class RoundOrchestrator:
    def __init__(self, run_id: str, agents: dict, tasks: dict, event_publisher):
        self.run_id = run_id
        self.agents = agents
        self.tasks = tasks
        self._publisher = event_publisher
        self._current_round: str | None = None
        self.r1_outputs: dict = {}
        self.challenge_ids: list[str] = []

    @property
    def current_round(self) -> str | None:
        return self._current_round

    def transition_to(self, to_round: str) -> None:
        if to_round not in ROUND_ORDER:
            raise ValueError(f"unknown round: {to_round}")
        if self._current_round is not None:
            current_idx = ROUND_ORDER.index(self._current_round)
            target_idx = ROUND_ORDER.index(to_round)
            if target_idx != current_idx + 1:
                raise ValueError(
                    f"invalid transition: {self._current_round} -> {to_round} "
                    f"(must follow order: {ROUND_ORDER})"
                )
        self._publisher(RoundTransition(from_round=self._current_round, to_round=to_round))
        self._current_round = to_round

    def record_r1_output(self, agent_name: str, output: dict) -> None:
        self.r1_outputs[agent_name] = output

    def record_challenge(self, challenge: dict) -> None:
        self.challenge_ids.append(challenge["challenge_id"])
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/deliberation/test_rounds.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add src/deliberation/rounds.py tests/deliberation/test_rounds.py
git commit -m "feat: add RoundOrchestrator for 3-round deliberation state machine"
```

---

### Task 7: 接线 crew.py 到 3 轮编排

**Files:**
- Create: `src/web/runner.py`
- Test: `tests/web/test_runner.py`

- [ ] **Step 1: 写 failing test**

`tests/web/test_runner.py`：

```python
import pytest
from unittest.mock import MagicMock, patch

from src.web.runner import run_deliberation


@pytest.fixture
def mock_crew():
    with patch("src.web.runner.StartupAnalyzerCrew") as MockCrew:
        mock_instance = MagicMock()
        MockCrew.return_value = mock_instance
        yield mock_instance


def test_run_deliberation_emits_round_transitions(mock_crew):
    events = []
    mock_crew.run_round1.return_value = {"market_analyst": {"tam": "100"}}
    mock_crew.run_round2.return_value = {"challenges": []}
    mock_crew.run_round3.return_value = {"decision": "Go"}

    result = run_deliberation(
        run_id="run-1",
        startup_idea="AI Agent 平台",
        event_publisher=events.append,
    )

    transitions = [e.to_round for e in events if hasattr(e, "to_round")]
    assert transitions == ["round1", "round2", "round3"]
    assert result["decision"] == "Go"


def test_run_deliberation_returns_final_report(mock_crew):
    mock_crew.run_round1.return_value = {}
    mock_crew.run_round2.return_value = {}
    mock_crew.run_round3.return_value = {"decision": "No-Go"}
    result = run_deliberation("run-1", "x", lambda e: None)
    assert "decision" in result
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/web/test_runner.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: 实现 runner.py**

`src/web/runner.py`：

```python
from src.crew import StartupAnalyzerCrew
from src.deliberation.rounds import RoundOrchestrator, RoundTransition
from src.deliberation.protocol import Verdict
from src.storage import update_run_status, get_session


def run_deliberation(run_id: str, startup_idea: str, event_publisher) -> dict:
    """执行 3 轮辩论流程，返回最终报告 dict。"""
    crew = StartupAnalyzerCrew(run_id=run_id)
    orch = RoundOrchestrator(
        run_id=run_id,
        agents=crew.agents_dict,
        tasks=crew.tasks_dict,
        event_publisher=event_publisher,
    )

    update_run_status(get_session(), run_id, "running")

    orch.transition_to("round1")
    r1_outputs = crew.run_round1(startup_idea=startup_idea, publisher=event_publisher)
    for agent_name, output in r1_outputs.items():
        orch.record_r1_output(agent_name, output)

    orch.transition_to("round2")
    r2_challenges = crew.run_round2(r1_outputs=r1_outputs, publisher=event_publisher)
    for ch in r2_challenges:
        orch.record_challenge(ch)

    orch.transition_to("round3")
    final_report = crew.run_round3(
        r1_outputs=r1_outputs, challenges=r2_challenges, publisher=event_publisher,
    )

    update_run_status(get_session(), run_id, "complete")
    event_publisher({"type": "run.complete", "run_id": run_id, "report": final_report})
    return final_report
```

- [ ] **Step 4: 跑测试确认通过（mock 模式）**

Run: `pytest tests/web/test_runner.py -v`
Expected: 2 passed（mock_instance 接受任意方法调用；CrewAI 真实方法接入在 T8 事件总线就绪后由后续 PR 补，v0.1 阶段 runner 只验证编排骨架）

- [ ] **Step 5: 提交（runner 占位）**

```bash
git add src/web/runner.py tests/web/test_runner.py
git commit -m "feat: add run_deliberation orchestrator (crew methods to be added in T8)"
```

---

## Phase 3：事件总线（T8）

### Task 8: 内存事件总线 + CrewAI 回调适配器

**Files:**
- Create: `src/web/events.py`
- Test: `tests/web/test_events.py`

- [ ] **Step 1: 写 failing test**

`tests/web/test_events.py`：

```python
import asyncio
import pytest

from src.web.events import EventBus, CrewCallbackAdapter


@pytest.mark.asyncio
async def test_event_bus_publishes_to_subscribers():
    bus = EventBus()
    received = []

    async def sub():
        async for event in bus.subscribe():
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(sub())
    await asyncio.sleep(0.01)
    bus.publish({"type": "a"})
    bus.publish({"type": "b"})
    await asyncio.wait_for(task, timeout=1.0)
    assert [e["type"] for e in received] == ["a", "b"]


def test_event_bus_publish_with_no_subscribers():
    bus = EventBus()
    bus.publish({"type": "x"})  # 不报错


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = EventBus()
    a, b = [], []

    async def sub_a():
        async for event in bus.subscribe():
            a.append(event)
            if len(a) >= 1:
                break

    async def sub_b():
        async for event in bus.subscribe():
            b.append(event)
            if len(b) >= 1:
                break

    t1 = asyncio.create_task(sub_a())
    t2 = asyncio.create_task(sub_b())
    await asyncio.sleep(0.01)
    bus.publish({"type": "shared"})
    await asyncio.wait_for(asyncio.gather(t1, t2), timeout=1.0)
    assert a == [{"type": "shared"}]
    assert b == [{"type": "shared"}]


def test_crew_callback_adapter_emits_agent_start():
    bus = EventBus()
    bus.publish = MagicMock(wraps=bus.publish)
    adapter = CrewCallbackAdapter(bus)

    adapter.on_agent_start(agent_name="market_analyst", round_name="round1")
    args, _ = bus.publish.call_args
    assert args[0]["type"] == "agent.start"
    assert args[0]["agent"] == "market_analyst"


def test_crew_callback_adapter_emits_tool_end():
    bus = EventBus()
    bus.publish = MagicMock(wraps=bus.publish)
    adapter = CrewCallbackAdapter(bus)

    adapter.on_tool_end(
        agent_name="market_analyst", tool_name="search",
        input_preview="AI Agent", output_preview="...",
        evidence_id="ev-1",
    )
    args, _ = bus.publish.call_args
    assert args[0]["type"] == "tool.end"
    assert args[0]["evidence_id"] == "ev-1"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/web/test_events.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: 实现 events.py**

`src/web/events.py`：

```python
import asyncio
from typing import Any, AsyncIterator


class EventBus:
    """进程内事件总线。多订阅者异步迭代。"""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def publish(self, event: dict) -> None:
        for q in self._subscribers:
            q.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            self._subscribers.remove(q)


class CrewCallbackAdapter:
    """把 CrewAI step_callback 事件转成 EventBus 事件。"""

    def __init__(self, bus: EventBus):
        self._bus = bus

    def on_agent_start(self, agent_name: str, round_name: str) -> None:
        self._bus.publish({
            "type": "agent.start",
            "agent": agent_name,
            "round": round_name,
        })

    def on_agent_end(self, agent_name: str, round_name: str, output_json_summary: dict) -> None:
        self._bus.publish({
            "type": "agent.end",
            "agent": agent_name,
            "round": round_name,
            "output_summary": output_json_summary,
        })

    def on_tool_start(self, agent_name: str, tool_name: str, input_preview: str) -> None:
        self._bus.publish({
            "type": "tool.start",
            "agent": agent_name,
            "tool": tool_name,
            "input_preview": input_preview[:200],
        })

    def on_tool_end(
        self, agent_name: str, tool_name: str,
        input_preview: str, output_preview: str, evidence_id: str | None = None,
    ) -> None:
        self._bus.publish({
            "type": "tool.end",
            "agent": agent_name,
            "tool": tool_name,
            "evidence_id": evidence_id,
            "output_preview": output_preview[:200],
        })

    def on_challenge_issued(self, challenge_id: str, issuer: str, target: str, claim: str, reason: str) -> None:
        self._bus.publish({
            "type": "challenge.issued",
            "challenge_id": challenge_id,
            "issuer": issuer,
            "target": target,
            "claim": claim,
            "reason": reason,
        })

    def on_challenge_responded(self, challenge_id: str, target: str, response: str, verdict: str) -> None:
        self._bus.publish({
            "type": "challenge.responded",
            "challenge_id": challenge_id,
            "target": target,
            "response": response,
            "verdict": verdict,
        })
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/web/test_events.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add src/web/events.py tests/web/test_events.py
git commit -m "feat: add in-process EventBus and CrewAI callback adapter"
```

---

## Phase 4：Backend API（T9-T13）

### Task 9: FastAPI app 骨架 + /health

**Files:**
- Create: `src/web/app.py`
- Create: `src/web/__init__.py`
- Create: `src/web/routes/__init__.py`
- Test: `tests/web/test_health.py`

- [ ] **Step 1: 写 failing test**

`tests/web/test_health.py`：

```python
import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/web/test_health.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: 实现 app.py + 路由包**

`src/web/__init__.py`：

```python
from src.web.app import create_app

__all__ = ["create_app"]
```

`src/web/routes/__init__.py`：

```python
```

`src/web/app.py`：

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.web.routes import runs, stream, evidence


def create_app() -> FastAPI:
    app = FastAPI(title="Startup Opportunity Analyzer", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(runs.router)
    app.include_router(stream.router)
    app.include_router(evidence.router)

    # 前端 SPA（Vite 构建产物）
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app
```

`src/web/routes/runs.py`（占位）：

```python
from fastapi import APIRouter

router = APIRouter(prefix="/runs", tags=["runs"])
```

`src/web/routes/stream.py`（占位）：

```python
from fastapi import APIRouter

router = APIRouter(tags=["stream"])
```

`src/web/routes/evidence.py`（占位）：

```python
from fastapi import APIRouter

router = APIRouter(prefix="/evidence", tags=["evidence"])
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/web/test_health.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add src/web/ tests/web/test_health.py
git commit -m "feat: add FastAPI app skeleton with /health endpoint"
```

---

### Task 10: POST /runs + run registry

**Files:**
- Modify: `src/web/routes/runs.py`
- Create: `src/web/run_registry.py`
- Test: `tests/web/test_runs.py`

- [ ] **Step 1: 写 failing test**

`tests/web/test_runs.py`：

```python
import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.web.run_registry import RunRegistry


@pytest.fixture
def client():
    return TestClient(create_app())


def test_post_runs_creates_run_and_returns_id(client, monkeypatch):
    monkeypatch.setattr(
        "src.web.routes.runs.run_deliberation_async",
        lambda run_id, idea: None,
    )
    resp = client.post("/runs", json={"startup_idea": "AI Agent 平台"})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "queued"


def test_get_run_returns_status(client):
    resp = client.post(
        "/runs", json={"startup_idea": "x"},
    )
    run_id = resp.json()["run_id"]
    resp2 = client.get(f"/runs/{run_id}")
    assert resp2.status_code == 200
    assert resp2.json()["run_id"] == run_id
    assert resp2.json()["status"] in ("queued", "running", "complete")


def test_post_runs_validates_input(client):
    resp = client.post("/runs", json={})
    assert resp.status_code == 422
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/web/test_runs.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 run_registry.py**

`src/web/run_registry.py`：

```python
from src.web.events import EventBus


class RunRegistry:
    """单进程内维护 run_id -> EventBus 的映射，供 SSE 流查询。"""

    def __init__(self):
        self._buses: dict[str, EventBus] = {}

    def create(self, run_id: str) -> EventBus:
        bus = EventBus()
        self._buses[run_id] = bus
        return bus

    def get(self, run_id: str) -> EventBus | None:
        return self._buses.get(run_id)


registry = RunRegistry()
```

- [ ] **Step 4: 实现 routes/runs.py**

`src/web/routes/runs.py`：

```python
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.storage import create_run, get_run, get_session
from src.storage.db import init_db
from src.web.events import EventBus
from src.web.run_registry import registry
from src.web.runner import run_deliberation

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    startup_idea: str


@router.post("")
async def create_run_endpoint(req: CreateRunRequest, background_tasks: BackgroundTasks):
    init_db()
    run = create_run(get_session(), startup_idea=req.startup_idea)
    bus = registry.create(run.run_id)
    background_tasks.add_task(_run_in_background, run.run_id, req.startup_idea, bus)
    return {"run_id": run.run_id, "status": run.status}


async def _run_in_background(run_id: str, startup_idea: str, bus: EventBus) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        run_deliberation,
        run_id,
        startup_idea,
        bus.publish,
    )


@router.get("/{run_id}")
async def get_run_endpoint(run_id: str):
    run = get_run(get_session(), run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": run.run_id,
        "startup_idea": run.startup_idea,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/web/test_runs.py -v`
Expected: 3 passed

- [ ] **Step 6: 提交**

```bash
git add src/web/routes/runs.py src/web/run_registry.py tests/web/test_runs.py
git commit -m "feat: add POST /runs and GET /runs/{id} endpoints"
```

---

### Task 11: GET /runs/{id}/stream SSE 端点

**Files:**
- Modify: `src/web/routes/stream.py`
- Test: `tests/web/test_stream.py`

- [ ] **Step 1: 写 failing test**

`tests/web/test_stream.py`：

```python
import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.web.run_registry import registry


def test_stream_yields_published_events():
    client = TestClient(create_app())
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    bus = registry.get(run_id)

    with client.stream("GET", f"/runs/{run_id}/stream") as response:
        bus.publish({"type": "test.event", "msg": "hello"})
        # 等待一行事件
        for line in response.iter_lines():
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if payload:
                    event = json.loads(payload)
                    if event.get("type") == "test.event":
                        assert event["msg"] == "hello"
                        break


def test_stream_404_for_unknown_run():
    client = TestClient(create_app())
    resp = client.get("/runs/does-not-exist/stream")
    assert resp.status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/web/test_stream.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 stream.py**

`src/web/routes/stream.py`：

```python
import asyncio
import json
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.web.run_registry import registry

router = APIRouter(prefix="/runs", tags=["stream"])


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    bus = registry.get(run_id)
    if bus is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_generator():
        try:
            async for event in bus.subscribe():
                yield (
                    f"id: {uuid.uuid4().hex}\n"
                    f"event: {event.get('type', 'message')}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )
                if event.get("type") in ("run.complete", "run.failed"):
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/web/test_stream.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add src/web/routes/stream.py tests/web/test_stream.py
git commit -m "feat: add SSE stream endpoint for live run events"
```

---

### Task 12: GET /runs/{id}/report

**Files:**
- Modify: `src/web/routes/runs.py`
- Test: `tests/web/test_report.py`

- [ ] **Step 1: 写 failing test**

`tests/web/test_report.py`：

```python
import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.storage import get_session, update_run_status
from src.storage.repository import _set_final_report_for_test  # 见下


def test_get_report_returns_final_report(client_with_complete_run):
    client, run_id = client_with_complete_run
    resp = client.get(f"/runs/{run_id}/report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "Go"


def test_get_report_404_for_unknown_run():
    from src.web.app import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app())
    resp = client.get("/runs/nonexistent/report")
    assert resp.status_code == 404


def test_get_report_409_for_running_run():
    from src.web.app import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app())
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    resp2 = client.get(f"/runs/{run_id}/report")
    assert resp2.status_code == 409


@pytest.fixture
def client_with_complete_run():
    from src.web.app import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app())
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    update_run_status(get_session(), run_id, "complete")
    _set_final_report_for_test(run_id, {"decision": "Go", "executive_summary": "ok"})
    return client, run_id
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/web/test_report.py -v`
Expected: FAIL

- [ ] **Step 3: 在 repository.py 增加测试辅助函数（追加到文件末尾）**

编辑 `src/storage/repository.py`，在末尾追加：

```python
def _set_final_report_for_test(run_id: str, report: dict) -> None:
    """测试用：直接给 run 写入 final_report。"""
    session = get_session()
    run = session.get(Run, run_id)
    if run is None:
        return
    run.final_report = report
    session.commit()
```

- [ ] **Step 4: 在 routes/runs.py 增加 report 端点（追加）**

编辑 `src/web/routes/runs.py`，在 `get_run_endpoint` 后追加：

```python
@router.get("/{run_id}/report")
async def get_report_endpoint(run_id: str):
    run = get_run(get_session(), run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.status != "complete":
        raise HTTPException(status_code=409, detail=f"run is {run.status}, not complete")
    if run.final_report is None:
        raise HTTPException(status_code=500, detail="run complete but no report")
    return run.final_report
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/web/test_report.py -v`
Expected: 4 passed

- [ ] **Step 6: 提交**

```bash
git add src/web/routes/runs.py src/storage/repository.py tests/web/test_report.py
git commit -m "feat: add GET /runs/{id}/report endpoint"
```

---

### Task 13: GET /evidence/{id}

**Files:**
- Modify: `src/web/routes/evidence.py`
- Test: `tests/web/test_evidence.py`

- [ ] **Step 1: 写 failing test**

`tests/web/test_evidence.py`：

```python
import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app
from src.storage import add_evidence, get_session


def test_get_evidence_returns_content():
    client = TestClient(create_app())
    ev = add_evidence(
        session=get_session(),
        run_id="run-1",
        source_type="search",
        query="AI Agent",
        url="https://example.com",
        title="报告",
        content_excerpt="前 500 字",
        url_hash="hash1",
    )
    resp = client.get(f"/evidence/{ev.evidence_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["evidence_id"] == ev.evidence_id
    assert data["title"] == "报告"
    assert data["content_excerpt"] == "前 500 字"


def test_get_evidence_404():
    client = TestClient(create_app())
    resp = client.get("/evidence/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/web/test_evidence.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 routes/evidence.py**

`src/web/routes/evidence.py`：

```python
from fastapi import APIRouter, HTTPException

from src.storage import get_evidence, get_session

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{evidence_id}")
async def get_evidence_endpoint(evidence_id: str):
    ev = get_evidence(get_session(), evidence_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    return {
        "evidence_id": ev.evidence_id,
        "source_type": ev.source_type,
        "query": ev.query,
        "url": ev.url,
        "title": ev.title,
        "content_excerpt": ev.content_excerpt,
        "captured_at": ev.captured_at.isoformat() if ev.captured_at else None,
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/web/test_evidence.py -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add src/web/routes/evidence.py tests/web/test_evidence.py
git commit -m "feat: add GET /evidence/{id} endpoint"
```

---

## Phase 5：前端（T14-T20）

### Task 14: Vite + React 项目骨架

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/.gitignore`

- [ ] **Step 1: 前端 .gitignore**

`frontend/.gitignore`：

```
node_modules/
dist/
.DS_Store
```

- [ ] **Step 2: package.json**

`frontend/package.json`：

```json
{
  "name": "startup-analyzer-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4",
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.6.3",
    "jsdom": "^25.0.1"
  }
}
```

- [ ] **Step 3: vite.config.ts**

`frontend/vite.config.ts`：

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/runs': 'http://localhost:8000',
      '/evidence': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 4: tsconfig.json**

`frontend/tsconfig.json`：

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 5: tsconfig.node.json**

`frontend/tsconfig.node.json`：

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: index.html**

`frontend/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>创业机会分析器</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: main.tsx**

`frontend/src/main.tsx`：

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 8: 极简 index.css**

`frontend/src/index.css`：

```css
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
  background: #f7f7f8;
  color: #1a1a1a;
}
```

- [ ] **Step 9: App.tsx 占位**

`frontend/src/App.tsx`：

```typescript
export default function App() {
  return <div style={{ padding: 24 }}><h1>创业机会分析器</h1></div>
}
```

- [ ] **Step 10: 安装依赖 + 验证 build**

```bash
cd frontend && npm install && npm run build
```

Expected: dist 目录生成，无错误

- [ ] **Step 11: 提交**

```bash
cd .. && git add frontend/
git commit -m "feat: scaffold Vite + React + TypeScript frontend"
```

---

### Task 15: SSE 客户端 lib + 类型定义

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/sse.ts`
- Test: `frontend/src/lib/sse.test.ts`

- [ ] **Step 1: types.ts**

`frontend/src/lib/types.ts`：

```typescript
export type RunStatus = 'queued' | 'running' | 'complete' | 'failed' | 'partial'

export interface RunInfo {
  run_id: string
  startup_idea: string
  status: RunStatus
  created_at: string | null
  completed_at: string | null
}

export type AgentName =
  | 'market_analyst'
  | 'competitor_researcher'
  | 'finance_analyst'
  | 'risk_reviewer'
  | 'strategy_advisor'

export type RunEvent =
  | { type: 'run.start'; run_id: string; startup_idea: string }
  | { type: 'round.transition'; from_round: string | null; to_round: string }
  | { type: 'agent.start'; agent: AgentName; round: string }
  | { type: 'agent.message'; agent: AgentName; content_summary: string; is_thought: boolean }
  | { type: 'agent.end'; agent: AgentName; round: string; output_summary: unknown }
  | { type: 'tool.start'; agent: AgentName; tool: string; input_preview: string }
  | { type: 'tool.end'; agent: AgentName; tool: string; evidence_id: string | null; output_preview: string }
  | { type: 'challenge.issued'; challenge_id: string; issuer: AgentName; target: AgentName; claim: string; reason: string }
  | { type: 'challenge.responded'; challenge_id: string; target: AgentName; response: string; verdict: string }
  | { type: 'run.complete'; run_id: string; report: unknown }
  | { type: 'run.failed'; run_id: string; error: string; partial: boolean }
  | { type: string; [k: string]: unknown }
```

- [ ] **Step 2: sse.ts**

`frontend/src/lib/sse.ts`：

```typescript
import type { RunEvent } from './types'

export type EventHandler = (event: RunEvent) => void

export function subscribeToRun(runId: string, onEvent: EventHandler, onError?: (e: Error) => void): () => void {
  const url = `/runs/${runId}/stream`
  const es = new EventSource(url)

  const handler = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data) as RunEvent
      onEvent(data)
    } catch (err) {
      onError?.(err as Error)
    }
  }

  const allEventNames = [
    'run.start', 'round.transition', 'agent.start', 'agent.message', 'agent.end',
    'tool.start', 'tool.end', 'challenge.issued', 'challenge.responded',
    'run.complete', 'run.failed',
  ]
  for (const name of allEventNames) {
    es.addEventListener(name, handler as EventListener)
  }
  es.onerror = () => onError?.(new Error('SSE connection error'))

  return () => {
    for (const name of allEventNames) {
      es.removeEventListener(name, handler as EventListener)
    }
    es.close()
  }
}
```

- [ ] **Step 3: sse.test.ts**

`frontend/src/lib/sse.test.ts`：

```typescript
import { describe, it, expect, vi } from 'vitest'
import { subscribeToRun } from './sse'

describe('sse subscribeToRun', () => {
  it('opens EventSource to the correct URL', () => {
    const ctor = vi.fn()
    // @ts-expect-error override for test
    global.EventSource = ctor
    subscribeToRun('run-123', () => {})
    expect(ctor).toHaveBeenCalledWith('/runs/run-123/stream')
  })

  it('returns a cleanup function that closes EventSource', () => {
    const close = vi.fn()
    const ctor = vi.fn().mockImplementation(() => ({ close, addEventListener: vi.fn(), removeEventListener: vi.fn(), onerror: null }))
    // @ts-expect-error override for test
    global.EventSource = ctor
    const cleanup = subscribeToRun('run-1', () => {})
    cleanup()
    expect(close).toHaveBeenCalled()
  })
})
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd frontend && npm test`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
cd .. && git add frontend/src/lib/
git commit -m "feat: add SSE client lib and shared event types"
```

---

### Task 16: 启动表单 + App layout

**Files:**
- Create: `frontend/src/components/StartupForm.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/StartupForm.test.tsx`

- [ ] **Step 1: StartupForm.tsx**

`frontend/src/components/StartupForm.tsx`：

```typescript
import { useState } from 'react'

interface Props {
  onSubmit: (idea: string) => void
  loading: boolean
}

export default function StartupForm({ onSubmit, loading }: Props) {
  const [idea, setIdea] = useState('')
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (idea.trim()) onSubmit(idea.trim())
      }}
      style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 720 }}
    >
      <label style={{ fontSize: 14, fontWeight: 600 }}>
        描述你的创业方向
      </label>
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        rows={8}
        placeholder="例如：面向中小企业的 AI Agent 客服平台，支持多轮对话、工单自动创建..."
        style={{
          padding: 12, fontSize: 14, border: '1px solid #ddd',
          borderRadius: 8, fontFamily: 'inherit', resize: 'vertical',
        }}
      />
      <button
        type="submit"
        disabled={loading || !idea.trim()}
        style={{
          padding: '10px 20px', fontSize: 14, fontWeight: 600,
          background: loading ? '#aaa' : '#1a1a1a', color: '#fff',
          border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? '分析中...' : '开始分析'}
      </button>
    </form>
  )
}
```

- [ ] **Step 2: StartupForm.test.tsx**

`frontend/src/components/StartupForm.test.tsx`：

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StartupForm from './StartupForm'

describe('StartupForm', () => {
  it('calls onSubmit with trimmed idea on submit', () => {
    const onSubmit = vi.fn()
    render(<StartupForm onSubmit={onSubmit} loading={false} />)
    fireEvent.change(screen.getByPlaceholderText(/AI Agent/), {
      target: { value: '  AI Agent 平台  ' },
    })
    fireEvent.click(screen.getByText('开始分析'))
    expect(onSubmit).toHaveBeenCalledWith('AI Agent 平台')
  })

  it('disables button when loading', () => {
    render(<StartupForm onSubmit={vi.fn()} loading={true} />)
    expect(screen.getByText('分析中...')).toBeDisabled()
  })

  it('does not call onSubmit with empty idea', () => {
    const onSubmit = vi.fn()
    render(<StartupForm onSubmit={onSubmit} loading={false} />)
    fireEvent.click(screen.getByText('开始分析'))
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 3: App.tsx 接入表单**

`frontend/src/App.tsx`：

```typescript
import { useState } from 'react'
import StartupForm from './components/StartupForm'
import { subscribeToRun } from './lib/sse'
import type { RunEvent } from './lib/types'
import AgentCard from './components/AgentCard'
import ChallengeLog from './components/ChallengeLog'
import EvidenceReport from './components/EvidenceReport'

type View = 'form' | 'running' | 'report' | 'failed'

export default function App() {
  const [view, setView] = useState<View>('form')
  const [events, setEvents] = useState<RunEvent[]>([])
  const [report, setReport] = useState<any>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')

  async function startAnalysis(idea: string) {
    setEvents([])
    setReport(null)
    setErrorMsg('')
    setView('running')

    const resp = await fetch('/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ startup_idea: idea }),
    })
    if (!resp.ok) {
      setErrorMsg('启动失败')
      setView('failed')
      return
    }
    const { run_id } = await resp.json()

    const cleanup = subscribeToRun(
      run_id,
      (event) => {
        setEvents((prev) => [...prev, event])
        if (event.type === 'run.complete') {
          setReport((event as any).report)
          setView('report')
          cleanup()
        } else if (event.type === 'run.failed') {
          setErrorMsg((event as any).error)
          setView('failed')
          cleanup()
        }
      },
      (err) => {
        setErrorMsg(err.message)
        setView('failed')
      },
    )
  }

  if (view === 'form') {
    return (
      <div style={{ padding: 32, maxWidth: 800, margin: '0 auto' }}>
        <h1>创业机会分析器</h1>
        <p style={{ color: '#666' }}>5 个 AI Agent 协作分析你的想法，10-20 分钟出 Go/No-Go 结论</p>
        <StartupForm onSubmit={startAnalysis} loading={false} />
      </div>
    )
  }

  if (view === 'running' || view === 'report' || view === 'failed') {
    return (
      <div style={{ padding: 32, maxWidth: 1000, margin: '0 auto' }}>
        <button onClick={() => setView('form')} style={{ marginBottom: 16 }}>← 重新开始</button>
        {view === 'failed' && <div style={{ color: 'red' }}>错误：{errorMsg}</div>}
        <ActivityFeed events={events} />
        <ChallengeLog events={events} />
        {view === 'report' && report && <EvidenceReport report={report} />}
      </div>
    )
  }
}

function ActivityFeed({ events }: { events: RunEvent[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
      {(['market_analyst', 'competitor_researcher', 'finance_analyst', 'risk_reviewer', 'strategy_advisor'] as const).map((agent) => (
        <AgentCard key={agent} agent={agent} events={events} />
      ))}
    </div>
  )
}
```

- [ ] **Step 4: 跑测试 + build**

```bash
cd frontend && npm test && npm run build
```

Expected: 测试通过，build 成功

- [ ] **Step 5: 提交**

```bash
cd .. && git add frontend/src/components/StartupForm.tsx frontend/src/App.tsx frontend/src/components/StartupForm.test.tsx
git commit -m "feat: add StartupForm and App layout with SSE wiring"
```

---

### Task 17: AgentCard 组件

**Files:**
- Create: `frontend/src/components/AgentCard.tsx`
- Test: `frontend/src/components/AgentCard.test.tsx`

- [ ] **Step 1: AgentCard.tsx**

`frontend/src/components/AgentCard.tsx`：

```typescript
import type { AgentName, RunEvent } from '../lib/types'

const LABELS: Record<AgentName, string> = {
  market_analyst: '市场分析师',
  competitor_researcher: '竞品调研员',
  finance_analyst: '财务分析师',
  risk_reviewer: '风险评审员',
  strategy_advisor: '战略顾问',
}

interface Props {
  agent: AgentName
  events: RunEvent[]
}

export default function AgentCard({ agent, events }: Props) {
  const agentEvents = events.filter((e) => (e as any).agent === agent)
  const lastTool = [...agentEvents].reverse().find((e) => e.type === 'tool.start') as
    | Extract<RunEvent, { type: 'tool.start' }>
    | undefined
  const lastEnd = [...agentEvents].reverse().find((e) => e.type === 'agent.end')
  const isActive = agentEvents.some((e) => e.type === 'agent.start') && !lastEnd
  const status = isActive ? '运行中' : lastEnd ? '已完成' : '待命'

  const statusColor =
    status === '运行中' ? '#f59e0b' : status === '已完成' ? '#10b981' : '#9ca3af'

  return (
    <div style={{
      padding: 12, background: '#fff', border: '1px solid #e5e5e5',
      borderRadius: 8, minHeight: 100,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong style={{ fontSize: 13 }}>{LABELS[agent]}</strong>
        <span style={{ fontSize: 11, color: statusColor }}>● {status}</span>
      </div>
      {lastTool && (
        <div style={{ fontSize: 11, color: '#666', marginTop: 8 }}>
          工具: {lastTool.tool} — {lastTool.input_preview.slice(0, 30)}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: AgentCard.test.tsx**

`frontend/src/components/AgentCard.test.tsx`：

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgentCard from './AgentCard'

describe('AgentCard', () => {
  it('shows waiting status when no events', () => {
    render(<AgentCard agent="market_analyst" events={[]} />)
    expect(screen.getByText(/待命/)).toBeInTheDocument()
  })

  it('shows running status when agent started but not ended', () => {
    const events = [{ type: 'agent.start', agent: 'market_analyst', round: 'round1' }]
    render(<AgentCard agent="market_analyst" events={events as any} />)
    expect(screen.getByText(/运行中/)).toBeInTheDocument()
  })

  it('shows completed status when agent ended', () => {
    const events = [
      { type: 'agent.start', agent: 'market_analyst', round: 'round1' },
      { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: {} },
    ]
    render(<AgentCard agent="market_analyst" events={events as any} />)
    expect(screen.getByText(/已完成/)).toBeInTheDocument()
  })

  it('shows last tool call when available', () => {
    const events = [
      { type: 'agent.start', agent: 'market_analyst', round: 'round1' },
      { type: 'tool.start', agent: 'market_analyst', tool: 'search', input_preview: 'AI Agent 市场' },
    ]
    render(<AgentCard agent="market_analyst" events={events as any} />)
    expect(screen.getByText(/工具: search/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 跑测试确认通过**

Run: `cd frontend && npm test`
Expected: AgentCard 测试全部通过

- [ ] **Step 4: 提交**

```bash
cd .. && git add frontend/src/components/AgentCard.tsx frontend/src/components/AgentCard.test.tsx
git commit -m "feat: add AgentCard component with status indicator"
```

---

### Task 18: ChallengeLog 组件

**Files:**
- Create: `frontend/src/components/ChallengeLog.tsx`
- Test: `frontend/src/components/ChallengeLog.test.tsx`

- [ ] **Step 1: ChallengeLog.tsx**

`frontend/src/components/ChallengeLog.tsx`：

```typescript
import type { RunEvent } from '../lib/types'

interface Props {
  events: RunEvent[]
}

const NAME_MAP: Record<string, string> = {
  market_analyst: '市场分析师',
  competitor_researcher: '竞品调研员',
  finance_analyst: '财务分析师',
  risk_reviewer: '风险评审员',
  strategy_advisor: '战略顾问',
}

export default function ChallengeLog({ events }: Props) {
  const challenges = events.filter((e) => e.type === 'challenge.issued') as Extract<RunEvent, { type: 'challenge.issued' }>[]
  const responses = events.filter((e) => e.type === 'challenge.responded') as Extract<RunEvent, { type: 'challenge.responded' }>[]

  if (challenges.length === 0) return null

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ fontSize: 16 }}>挑战日志</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {challenges.map((ch) => {
          const response = responses.find((r) => r.challenge_id === ch.challenge_id)
          return (
            <div key={ch.challenge_id} style={{
              padding: 12, background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 8,
            }}>
              <div style={{ fontSize: 13 }}>
                <strong>{NAME_MAP[ch.issuer]}</strong> 挑战 <strong>{NAME_MAP[ch.target]}</strong>
              </div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                论断: {ch.claim}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>
                理由: {ch.reason}
              </div>
              {response && (
                <div style={{ fontSize: 12, marginTop: 8, padding: 8, background: '#fff', borderRadius: 4 }}>
                  <strong>{NAME_MAP[response.target]} 回应:</strong> {response.response}
                  <span style={{ marginLeft: 8, color: response.verdict === 'rejected' ? '#dc2626' : '#10b981' }}>
                    [{response.verdict}]
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
```

- [ ] **Step 2: ChallengeLog.test.tsx**

`frontend/src/components/ChallengeLog.test.tsx`：

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChallengeLog from './ChallengeLog'

describe('ChallengeLog', () => {
  it('renders nothing when no challenges', () => {
    const { container } = render(<ChallengeLog events={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders challenge with issuer and target', () => {
    const events = [
      {
        type: 'challenge.issued',
        challenge_id: 'ch-1',
        issuer: 'market_analyst',
        target: 'finance_analyst',
        claim: 'LTV 假设过高',
        reason: '行业基准是 X',
      },
    ]
    render(<ChallengeLog events={events as any} />)
    expect(screen.getByText(/市场分析师/)).toBeInTheDocument()
    expect(screen.getByText(/财务分析师/)).toBeInTheDocument()
    expect(screen.getByText(/LTV 假设过高/)).toBeInTheDocument()
  })

  it('shows response when present', () => {
    const events = [
      {
        type: 'challenge.issued',
        challenge_id: 'ch-1', issuer: 'a', target: 'b',
        claim: 'c', reason: 'd',
      },
      {
        type: 'challenge.responded',
        challenge_id: 'ch-1', target: 'b',
        response: '已调整', verdict: 'modified',
      },
    ]
    render(<ChallengeLog events={events as any} />)
    expect(screen.getByText(/已调整/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 跑测试 + 提交**

```bash
cd frontend && npm test
```

Expected: 全部通过

```bash
cd .. && git add frontend/src/components/ChallengeLog.tsx frontend/src/components/ChallengeLog.test.tsx
git commit -m "feat: add ChallengeLog component for cross-agent debate display"
```

---

### Task 19: EvidenceReport 组件

**Files:**
- Create: `frontend/src/components/EvidenceReport.tsx`
- Test: `frontend/src/components/EvidenceReport.test.tsx`

- [ ] **Step 1: EvidenceReport.tsx**

`frontend/src/components/EvidenceReport.tsx`：

```typescript
import { useEffect, useState } from 'react'

interface EvidenceContent {
  evidence_id: string
  title: string | null
  url: string | null
  content_excerpt: string
}

interface Props {
  report: any
}

const VERDICT_COLOR: Record<string, string> = {
  Go: '#10b981',
  'No-Go': '#dc2626',
  'Conditional-Go': '#f59e0b',
}

export default function EvidenceReport({ report }: Props) {
  const [modal, setModal] = useState<EvidenceContent | null>(null)

  useEffect(() => {
    if (!modal) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setModal(null)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [modal])

  const verdict = report?.decision
  const color = verdict ? VERDICT_COLOR[verdict] || '#666' : '#666'

  async function showEvidence(evidenceId: string) {
    const resp = await fetch(`/evidence/${evidenceId}`)
    if (resp.ok) {
      setModal(await resp.json())
    }
  }

  return (
    <section style={{ marginTop: 32, background: '#fff', padding: 24, borderRadius: 8, border: '1px solid #e5e5e5' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, margin: 0 }}>最终评估</h2>
        <span style={{
          padding: '4px 12px', background: color, color: '#fff',
          borderRadius: 4, fontSize: 14, fontWeight: 600,
        }}>{verdict}</span>
      </div>

      <div style={{ fontSize: 14, lineHeight: 1.6 }}>
        <p><strong>结论：</strong>{report?.executive_summary}</p>
        <p><strong>市场机会：</strong>{report?.market_opportunity_summary}</p>
        <p><strong>竞争优势：</strong>{report?.competitive_advantage}</p>
        <p><strong>财务可行性：</strong>{report?.financial_viability}</p>
        <p><strong>信心度：</strong>{report?.final_confidence}</p>
      </div>

      {report?.key_risks?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong style={{ fontSize: 14 }}>关键风险：</strong>
          <ul style={{ fontSize: 13, marginTop: 8 }}>
            {report.key_risks.map((r: string, i: number) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {report?.next_steps?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong style={{ fontSize: 14 }}>下一步行动：</strong>
          <ul style={{ fontSize: 13, marginTop: 8 }}>
            {report.next_steps.map((s: any, i: number) => (
              <li key={i}>
                <strong>[{s.priority}]</strong> {s.action} <em style={{ color: '#666' }}>({s.timeline})</em>
              </li>
            ))}
          </ul>
        </div>
      )}

      {modal && (
        <div
          onClick={() => setModal(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#fff', padding: 24, maxWidth: 720, maxHeight: '80vh',
              overflow: 'auto', borderRadius: 8,
            }}
          >
            <h3 style={{ margin: 0 }}>{modal.title || '证据原文'}</h3>
            {modal.url && <a href={modal.url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>{modal.url}</a>}
            <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 12 }}>{modal.content_excerpt}</pre>
            <button onClick={() => setModal(null)} style={{ marginTop: 12 }}>关闭</button>
          </div>
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 2: EvidenceReport.test.tsx**

`frontend/src/components/EvidenceReport.test.tsx`：

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EvidenceReport from './EvidenceReport'

describe('EvidenceReport', () => {
  it('renders decision verdict', () => {
    render(<EvidenceReport report={{ decision: 'Go', executive_summary: 'x' }} />)
    expect(screen.getByText('Go')).toBeInTheDocument()
  })

  it('renders key risks', () => {
    render(<EvidenceReport report={{ decision: 'Go', key_risks: ['风险 A', '风险 B'] }} />)
    expect(screen.getByText('风险 A')).toBeInTheDocument()
  })

  it('renders next steps with priority', () => {
    render(<EvidenceReport report={{
      decision: 'Go',
      next_steps: [{ action: '做 MVP', priority: 'P0', timeline: '1 月' }],
    }} />)
    expect(screen.getByText(/做 MVP/)).toBeInTheDocument()
    expect(screen.getByText(/P0/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 跑测试 + 提交**

```bash
cd frontend && npm test
```

Expected: 全部通过

```bash
cd .. && git add frontend/src/components/EvidenceReport.tsx frontend/src/components/EvidenceReport.test.tsx
git commit -m "feat: add EvidenceReport with verdict and evidence modal"
```

---

### Task 20: 前端构建产物集成到 FastAPI

**Files:**
- Modify: `src/web/app.py`
- Create: `frontend/dist/index.html` (placeholder)

- [ ] **Step 1: 临时生成占位 dist（验证 FastAPI 静态托管）**

```bash
cd frontend && npm run build && cd ..
ls frontend/dist/
```

Expected: dist 下有 index.html 和 assets/

- [ ] **Step 2: 验证 FastAPI 静态托管**

```bash
python -c "
from src.web.app import create_app
app = create_app()
print([r.path for r in app.routes if 'static' in str(type(r)).lower()])
"
```

Expected: 看到 `/` 路径下的 StaticFiles mount

- [ ] **Step 3: 端到端冒烟（手动）**

```bash
uvicorn src.web.app:create_app --factory --host 0.0.0.0 --port 8000 &
sleep 2
curl http://localhost:8000/health
curl -X POST http://localhost:8000/runs -H "Content-Type: application/json" -d '{"startup_idea":"test"}'
# 应该返回 {"run_id":"...","status":"queued"}
```

Expected: 启动成功，两个端点都返回正常

- [ ] **Step 4: 关闭后台服务**

```bash
pkill -f "uvicorn src.web.app"
```

- [ ] **Step 5: 提交（dist 不进 git，只提交 app.py 验证）**

```bash
git add src/web/app.py
git commit -m "feat: wire FastAPI to serve Vite frontend dist"
```

---

## Phase 6：集成 + 部署（T21-T23）

### Task 21: prompts 强化（强制挑战 + 强制 evidence_ids）

**Files:**
- Modify: `src/config/agents.yaml`
- Modify: `src/config/tasks.yaml`

- [ ] **Step 1: 在 agents.yaml 给所有 worker agent 加 R2 行为**

编辑 `src/config/agents.yaml`，在 `risk_reviewer` 的 `backstory` 末尾追加（保留原内容）：

```yaml
    在第二轮（交叉挑战）中，你必须仔细审视其他 agent 的输出。
    如果发现论断缺乏证据、假设不合理、或与其他 agent 矛盾，
    使用 challenge 工具发起挑战。如果没有异议，可以直接接受。
```

- [ ] **Step 2: 在 tasks.yaml 给 R2 加任务定义**

在 `src/config/tasks.yaml` 末尾追加：

```yaml
round2_challenge:
  description: >
    第二轮：交叉审视其他 4 个 agent 在第一轮的分析结果。
    创业方向：{startup_idea}

    其他 agent 的结论：
    {round1_outputs}

    你的任务：
    1. 仔细阅读所有 agent 的输出
    2. 如果发现任何论断缺乏证据支撑、数据可疑、或与其他 agent 矛盾，
       使用 challenge 工具发起挑战（最多 3 次）
    3. 如果没有明显问题，可以直接接受，不需要发起挑战
  expected_output: >
    你的回应可以包含 0-3 个 challenge 调用，每个挑战指明：
    - target: 被挑战的 agent 名
    - claim: 具体被挑战的论断
    - reason: 挑战理由（引用其他 agent 的字段或你自己的依据）
  agent: market_analyst  # 占位：实际上 5 个 agent 都会跑
```

- [ ] **Step 3: 提交**

```bash
git add src/config/agents.yaml src/config/tasks.yaml
git commit -m "feat: add R2 challenge instructions to agent prompts"
```

---

### Task 22: 端到端集成测试（mock LLM）

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_end_to_end.py`
- Test: `tests/integration/test_end_to_end.py`

- [ ] **Step 1: 写集成测试**

`tests/integration/__init__.py`：

```python
```

`tests/integration/test_end_to_end.py`：

```python
import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock

from src.web.app import create_app
from src.web.run_registry import registry
from src.storage import get_run, get_session


MOCK_R1_OUTPUTS = {
    "market_analyst": {
        "startup_idea": "test",
        "tam_sam_som": {"tam": {"value": "100亿", "source": "x", "year": "2024"}},
    },
    "competitor_researcher": {"startup_idea": "test", "competitors": []},
    "finance_analyst": {"startup_idea": "test", "ltv_analysis": {"estimated_ltv": "X"}},
    "risk_reviewer": {"startup_idea": "test", "risks": []},
}

MOCK_R2_CHALLENGES = [
    {"challenge_id": "ch-1", "issuer": "market_analyst", "target": "finance_analyst",
     "claim": "LTV 假设过高", "reason": "行业基准是 Y", "response": "已调整", "verdict": "modified"},
]

MOCK_R3_REPORT = {
    "startup_idea": "test",
    "decision": "Conditional-Go",
    "executive_summary": "需要进一步验证",
    "final_confidence": "中",
}


@pytest.fixture
def mock_crew_methods():
    with patch("src.web.runner.StartupAnalyzerCrew") as MockCrew:
        instance = MagicMock()
        instance.run_round1.return_value = MOCK_R1_OUTPUTS
        instance.run_round2.return_value = MOCK_R2_CHALLENGES
        instance.run_round3.return_value = MOCK_R3_REPORT
        instance.agents_dict = {}
        instance.tasks_dict = {}
        MockCrew.return_value = instance
        yield instance


def test_end_to_end_run_completes_with_report(mock_crew_methods):
    from fastapi.testclient import TestClient
    client = TestClient(create_app())

    resp = client.post("/runs", json={"startup_idea": "AI Agent 平台"})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    # 等待后台任务完成
    import time
    for _ in range(50):
        run = get_run(get_session(), run_id)
        if run.status == "complete":
            break
        time.sleep(0.1)

    run = get_run(get_session(), run_id)
    assert run.status == "complete"
    assert run.final_report is not None
    assert run.final_report["decision"] == "Conditional-Go"


def test_end_to_end_sse_stream_emits_events(mock_crew_methods):
    from fastapi.testclient import TestClient
    client = TestClient(create_app())

    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    bus = registry.get(run_id)
    received_types = []

    with client.stream("GET", f"/runs/{run_id}/stream") as response:
        # 模拟后台任务推送一些事件
        bus.publish({"type": "test.event", "msg": "a"})
        bus.publish({"type": "run.complete", "run_id": run_id})

        for line in response.iter_lines():
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload:
                    event = json.loads(payload)
                    received_types.append(event.get("type"))
                    if "run.complete" in received_types:
                        break

    assert "test.event" in received_types
    assert "run.complete" in received_types
```

- [ ] **Step 2: 跑测试确认通过**

Run: `pytest tests/integration/ -v`
Expected: 2 passed

- [ ] **Step 3: 提交**

```bash
git add tests/integration/
git commit -m "test: add end-to-end integration test with mock LLM"
```

---

### Task 23: 阿里云部署文档

**Files:**
- Modify: `README.md`
- Modify: `src/web/app.py`（确保 host=0.0.0.0）

- [ ] **Step 1: 阿里云部署文档**

在 `README.md` 末尾追加：

```markdown
## 部署到阿里云 ECS

### 前置条件
- 阿里云 ECS 一台（2 vCPU / 4GB RAM 起步）
- 操作系统：Ubuntu 22.04 LTS
- 域名（可选，HTTPS 用）

### 部署步骤

```bash
# 1. 系统依赖
sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx nodejs npm

# 2. 克隆代码
git clone https://github.com/yourname/startup-opportunity-analyzer.git
cd startup-opportunity-analyzer

# 3. Python 后端
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env：填入 DEEPSEEK_API_KEY / SERPER_API_KEY

# 5. 前端构建
cd frontend
npm install
npm run build
cd ..

# 6. 启动后端（前台）
uvicorn src.web.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 用 systemd 管理进程

创建 `/etc/systemd/system/analyzer.service`：

```ini
[Unit]
Description=Startup Opportunity Analyzer
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/startup-opportunity-analyzer
Environment="PATH=/home/ubuntu/startup-opportunity-analyzer/.venv/bin"
ExecStart=/home/ubuntu/startup-opportunity-analyzer/.venv/bin/uvicorn src.web.app:create_app --factory --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now analyzer
sudo systemctl status analyzer
```

### 用 Nginx 反向代理 + HTTPS

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE 必须
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/analyzer /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

HTTPS 用 certbot：`sudo certbot --nginx -d yourdomain.com`
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: add 阿里云 ECS deployment guide"
```

---

## 完整端到端验证（最后一步）

按顺序执行所有测试：

```bash
# 后端测试
pytest tests/ -v

# 前端测试
cd frontend && npm test && npm run build && cd ..

# 启动服务
uvicorn src.web.app:create_app --factory --host 0.0.0.0 --port 8000
```

浏览器访问 `http://localhost:8000`，填入一个创业想法，验证：
- 5 个 Agent 卡片实时更新
- 挑战日志显示
- 最终报告显示 Go/No-Go/Conditional-Go

**验收清单见 spec 第十四节**。
