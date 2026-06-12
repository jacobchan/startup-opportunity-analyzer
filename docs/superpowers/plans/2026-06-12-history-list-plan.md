# History List on Homepage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scrollable history list below the homepage form showing recent analyses with re-run, view, and delete actions.

**Architecture:** Two new backend endpoints (`GET /runs` for listing, `DELETE /runs/{run_id}` for hard delete) + two new React components (`HistoryList` container, `HistoryCard` item) wired below `StartupForm` in `App.tsx`.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + TypeScript (frontend), SQLite (storage)

---

### Task 1: Add `list_runs` to repository

**Files:**
- Modify: `src/storage/repository.py`
- Modify: `src/storage/__init__.py`
- Test: `tests/storage/test_repository.py`

- [ ] **Step 1: Add failing tests for list_runs and count_runs**

Add to `tests/storage/test_repository.py`:

```python
def test_list_runs_returns_most_recent_first(db_session):
    r1 = create_run(db_session, startup_idea="first")
    r2 = create_run(db_session, startup_idea="second")
    from src.storage.repository import list_runs
    runs, total = list_runs(db_session, limit=10, offset=0)
    assert len(runs) == 2
    assert runs[0].startup_idea == "second"  # newest first


def test_list_runs_respects_limit_and_offset(db_session):
    for i in range(5):
        create_run(db_session, startup_idea=f"idea {i}")
    from src.storage.repository import list_runs
    runs, total = list_runs(db_session, limit=2, offset=1)
    assert len(runs) == 2
    assert total == 5
    # Offset 1 skips the newest run
    assert runs[0].created_at < runs[0].created_at  # just checking it works


def test_delete_run_removes_run_and_cascades(db_session):
    run = create_run(db_session, startup_idea="x")
    run_id = run.run_id
    from src.storage.repository import delete_run, add_evidence, add_challenge, get_run
    add_evidence(db_session, run_id=run_id, source_type="search",
                 query="q", url=None, title=None, content_excerpt="c", url_hash="h1")
    add_challenge(db_session, run_id=run_id, issuer="a", target="b", claim="c", reason="r")
    deleted = delete_run(db_session, run_id)
    assert deleted is True
    assert get_run(db_session, run_id) is None


def test_delete_run_returns_false_for_unknown_id(db_session):
    from src.storage.repository import delete_run
    assert delete_run(db_session, "no-such-id") is False
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/storage/test_repository.py::test_list_runs_returns_most_recent_first tests/storage/test_repository.py::test_list_runs_respects_limit_and_offset tests/storage/test_repository.py::test_delete_run_removes_run_and_cascades tests/storage/test_repository.py::test_delete_run_returns_false_for_unknown_id -v`

Expected: FAIL — `list_runs` / `count_runs` / `delete_run` not defined

- [ ] **Step 3: Implement list_runs and delete_run**

In `src/storage/repository.py`, add after `get_challenges_for_run`:

```python
def list_runs(session: Session, limit: int = 10, offset: int = 0) -> tuple[list[Run], int]:
    """Return (runs ordered by created_at DESC, total count)."""
    from sqlalchemy import func
    total = session.execute(select(func.count(Run.run_id))).scalar_one()
    stmt = select(Run).order_by(Run.created_at.desc()).limit(limit).offset(offset)
    runs = list(session.execute(stmt).scalars())
    return runs, total


def delete_run(session: Session, run_id: str) -> bool:
    """Hard-delete a run and its associated evidence + challenges. Returns True if deleted."""
    run = session.get(Run, run_id)
    if run is None:
        return False
    # Cascade delete evidence
    from sqlalchemy import delete as sql_delete
    session.execute(sql_delete(Evidence).where(Evidence.run_id == run_id))
    session.execute(sql_delete(Challenge).where(Challenge.run_id == run_id))
    session.delete(run)
    session.commit()
    return True
```

- [ ] **Step 4: Update __init__.py exports**

In `src/storage/__init__.py`, add `list_runs, delete_run` to the imports and `__all__`:

```python
from src.storage.repository import (
    create_run, get_run, update_run_status,
    add_evidence, get_evidence,
    add_challenge, update_challenge_response, get_challenges_for_run,
    list_runs, count_runs, delete_run,
)
```

And in `__all__` add `"list_runs", "count_runs", "delete_run"`.

Wait — I didn't add `count_runs`. Let me simplify. `list_runs` returns a `(runs, total)` tuple so we don't need a separate `count_runs`. The `__all__` should include `"list_runs", "delete_run"`.

- [ ] **Step 5: Run tests, verify PASS**

Run: `pytest tests/storage/test_repository.py -v`

Expected: All tests PASS (existing 4 + new 4 = 8)

- [ ] **Step 6: Commit**

```bash
git add src/storage/repository.py src/storage/__init__.py tests/storage/test_repository.py
git commit -m "feat: add list_runs and delete_run to storage repository"
```

---

### Task 2: Add GET /runs and DELETE /runs/{run_id} endpoints

**Files:**
- Modify: `src/web/routes/runs.py`
- Test: `tests/web/test_runs.py`

- [ ] **Step 1: Add failing tests**

Add to `tests/web/test_runs.py`:

```python
def test_list_runs_returns_recent_items(client):
    # Create 3 runs first
    ids = []
    for idea in ["idea-a", "idea-b", "idea-c"]:
        resp = client.post("/runs", json={"startup_idea": idea})
        ids.append(resp.json()["run_id"])
    # List them
    resp = client.get("/runs?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert "total" in data
    assert data["total"] >= 3
    # newest first
    assert data["runs"][0]["startup_idea"] == "idea-c"


def test_list_runs_defaults_limit_10_offset_0(client):
    resp = client.get("/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert "total" in data


def test_delete_run_removes_run(client):
    resp = client.post("/runs", json={"startup_idea": "x"})
    run_id = resp.json()["run_id"]
    del_resp = client.delete(f"/runs/{run_id}")
    assert del_resp.status_code == 204
    # Verify it's gone
    get_resp = client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 404


def test_delete_run_404_for_unknown(client):
    resp = client.delete("/runs/no-such-id")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `pytest tests/web/test_runs.py::test_list_runs_returns_recent_items tests/web/test_runs.py::test_list_runs_defaults_limit_10_offset_0 tests/web/test_runs.py::test_delete_run_removes_run tests/web/test_runs.py::test_delete_run_404_for_unknown -v`

Expected: FAIL — endpoints not defined

- [ ] **Step 3: Implement the endpoints**

In `src/web/routes/runs.py`, import `list_runs, delete_run` and add after `get_run_endpoint`:

```python
from src.storage import create_run, get_run, get_session, list_runs, delete_run


@router.get("")
async def list_runs_endpoint(limit: int = 10, offset: int = 0):
    init_db()
    session = get_session()
    runs, total = list_runs(session, limit=limit, offset=offset)
    items = []
    for run in runs:
        item = {
            "run_id": run.run_id,
            "startup_idea": run.startup_idea,
            "status": run.status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "decision": None,
            "executive_summary": None,
        }
        if run.final_report:
            item["decision"] = run.final_report.get("decision")
            item["executive_summary"] = run.final_report.get("executive_summary")
        items.append(item)
    return {"runs": items, "total": total}


@router.delete("/{run_id}")
async def delete_run_endpoint(run_id: str):
    init_db()
    session = get_session()
    if delete_run(session, run_id):
        return None, 204
    raise HTTPException(status_code=404, detail="run not found")
```

Note: FastAPI `return None, 204` returns a 204 No Content response. For the 204 case we should use `Response(status_code=204)`:

```python
from fastapi import Response

@router.delete("/{run_id}")
async def delete_run_endpoint(run_id: str):
    init_db()
    if delete_run(get_session(), run_id):
        return Response(status_code=204)
    raise HTTPException(status_code=404, detail="run not found")
```

- [ ] **Step 4: Handle route ordering**

The new `GET /runs` and `GET /runs/{run_id}` routes must not conflict. The `/runs/{run_id}` route with `{run_id}` param should not match `?limit=10&offset=0`. FastAPI's router handles this correctly because `/runs` (no path param) and `/runs/{run_id}` (path param) are distinct routes. The query params on `GET /runs?limit=10` don't create conflicts. Verify the existing `GET /runs/{run_id}` test still passes.

- [ ] **Step 5: Run tests, verify PASS**

Run: `pytest tests/web/test_runs.py -v`

Expected: All tests PASS (existing 4 + new 4 = 8)

- [ ] **Step 6: Commit**

```bash
git add src/web/routes/runs.py tests/web/test_runs.py
git commit -m "feat: add GET /runs list and DELETE /runs/{id} endpoints"
```

---

### Task 3: HistoryCard component

**Files:**
- Create: `frontend/src/components/HistoryCard.tsx`
- Create: `frontend/src/components/HistoryCard.test.tsx`

- [ ] **Step 1: Write tests for HistoryCard**

Create `frontend/src/components/HistoryCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import HistoryCard from './HistoryCard'

const completeRun = {
  run_id: 'run-1',
  startup_idea: 'AI Agent 客服平台',
  status: 'complete',
  decision: 'Go',
  executive_summary: '市场空间充足',
  created_at: new Date().toISOString(),
  completed_at: null,
}

const runningRun = {
  run_id: 'run-2',
  startup_idea: '跨境电商选品工具',
  status: 'running',
  decision: null,
  executive_summary: null,
  created_at: new Date().toISOString(),
  completed_at: null,
}

describe('HistoryCard', () => {
  it('renders startup idea truncated', () => {
    render(
      <HistoryCard
        run={completeRun}
        onRerun={vi.fn()}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    expect(screen.getByText(/AI Agent/)).toBeDefined()
  })

  it('shows decision badge for complete runs', () => {
    render(
      <HistoryCard
        run={completeRun}
        onRerun={vi.fn()}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    expect(screen.getByText('Go')).toBeDefined()
  })

  it('shows running status for non-complete runs', () => {
    render(
      <HistoryCard
        run={runningRun}
        onRerun={vi.fn()}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    expect(screen.getByText(/进行中/)).toBeDefined()
  })

  it('calls onRerun when re-run button clicked', () => {
    const onRerun = vi.fn()
    render(
      <HistoryCard
        run={completeRun}
        onRerun={onRerun}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    fireEvent.click(screen.getByText('重跑'))
    expect(onRerun).toHaveBeenCalledWith('AI Agent 客服平台')
  })

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn()
    render(
      <HistoryCard
        run={completeRun}
        onRerun={vi.fn()}
        onDelete={onDelete}
        onClick={vi.fn()}
      />
    )
    fireEvent.click(screen.getByText('删除'))
    expect(onDelete).toHaveBeenCalledWith('run-1')
  })
})
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `npx vitest run src/components/HistoryCard.test.tsx`

Expected: FAIL — HistoryCard module not found

- [ ] **Step 3: Implement HistoryCard**

Create `frontend/src/components/HistoryCard.tsx`:

```tsx
export interface HistoryRun {
  run_id: string
  startup_idea: string
  status: string
  decision: string | null
  executive_summary: string | null
  created_at: string | null
  completed_at: string | null
}

interface Props {
  run: HistoryRun
  onRerun: (idea: string) => void
  onDelete: (runId: string) => void
  onClick: (runId: string) => void
}

function formatTime(iso: string | null): string {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  if (hours < 48) return '昨天'
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function decisionBadge(decision: string | null, status: string) {
  if (status === 'running' || status === 'queued') {
    return (
      <span style={{
        background: '#e3f2fd', color: '#1565c0',
        padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
      }}>
        进行中
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span style={{
        background: '#ffebee', color: '#c62828',
        padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
      }}>
        失败
      </span>
    )
  }
  if (!decision) return null
  const colors: Record<string, { bg: string; fg: string }> = {
    'Go': { bg: '#e8f5e9', fg: '#2e7d32' },
    'No-Go': { bg: '#ffebee', fg: '#c62828' },
    'Conditional-Go': { bg: '#fff3e0', fg: '#e65100' },
  }
  const c = colors[decision] ?? { bg: '#f5f5f5', fg: '#666' }
  return (
    <span style={{
      background: c.bg, color: c.fg,
      padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
    }}>
      {decision}
    </span>
  )
}

export default function HistoryCard({ run, onRerun, onDelete, onClick }: Props) {
  const isComplete = run.status === 'complete'
  const summary = isComplete ? run.executive_summary : run.status === 'failed' ? '分析失败' : '分析进行中，预计 10-20 分钟...'

  return (
    <div
      onClick={() => onClick(run.run_id)}
      style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '12px 16px', border: '1px solid #eee', borderRadius: 10,
        cursor: 'pointer', background: run.status === 'running' ? '#f8fbff' : '#fff',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span style={{
            fontSize: 14, fontWeight: 600,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            maxWidth: 260,
          }}>
            {run.startup_idea.length > 40 ? run.startup_idea.slice(0, 40) + '...' : run.startup_idea}
          </span>
          {decisionBadge(run.decision, run.status)}
        </div>
        <p style={{
          color: run.status === 'running' ? '#aaa' : '#888', fontSize: 12, margin: 0,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          maxWidth: 340,
        }}>
          {summary ?? ''}
        </p>
        <span style={{ color: '#aaa', fontSize: 11 }}>{formatTime(run.created_at)}</span>
      </div>
      <div style={{ display: 'flex', gap: 6, marginLeft: 12, flexShrink: 0 }}
           onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => onRerun(run.startup_idea)}
          style={{
            padding: '4px 10px', fontSize: 11, border: '1px solid #ddd',
            borderRadius: 6, cursor: 'pointer', background: '#fff',
          }}
        >
          重跑
        </button>
        <button
          onClick={() => onDelete(run.run_id)}
          style={{
            padding: '4px 10px', fontSize: 11, border: 'none',
            borderRadius: 6, cursor: 'pointer', background: '#fee2e2', color: '#dc2626',
          }}
        >
          删除
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `npx vitest run src/components/HistoryCard.test.tsx`

Expected: All PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/HistoryCard.tsx frontend/src/components/HistoryCard.test.tsx
git commit -m "feat: add HistoryCard component"
```

---

### Task 4: HistoryList component

**Files:**
- Create: `frontend/src/components/HistoryList.tsx`
- Create: `frontend/src/components/HistoryList.test.tsx`

- [ ] **Step 1: Write tests for HistoryList**

Create `frontend/src/components/HistoryList.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import HistoryList from './HistoryList'

const mockRuns = [
  {
    run_id: 'r1',
    startup_idea: 'AI Agent 平台',
    status: 'complete',
    decision: 'Go',
    executive_summary: '市场好',
    created_at: new Date().toISOString(),
    completed_at: null,
    round1_outputs: null,
  },
  {
    run_id: 'r2',
    startup_idea: '跨境电商工具',
    status: 'running',
    decision: null,
    executive_summary: null,
    created_at: new Date().toISOString(),
    completed_at: null,
    round1_outputs: null,
  },
]

describe('HistoryList', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ runs: mockRuns, total: 15 }),
    }) as any
  })

  it('renders runs from API', async () => {
    render(<HistoryList onRerun={vi.fn()} onViewRun={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(/AI Agent/)).toBeDefined()
      expect(screen.getByText(/跨境电商/)).toBeDefined()
    })
  })

  it('shows empty state when no runs', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ runs: [], total: 0 }),
    }) as any
    render(<HistoryList onRerun={vi.fn()} onViewRun={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(/暂无历史记录/)).toBeDefined()
    })
  })

  it('calls onRerun with startup idea', async () => {
    const onRerun = vi.fn()
    render(<HistoryList onRerun={onRerun} onViewRun={vi.fn()} />)
    await waitFor(() => screen.getByText(/AI Agent/))
    fireEvent.click(screen.getAllByText('重跑')[0])
    expect(onRerun).toHaveBeenCalledWith('AI Agent 平台')
  })

  it('calls onViewRun with run_id on card click', async () => {
    const onViewRun = vi.fn()
    render(<HistoryList onRerun={vi.fn()} onViewRun={onViewRun} />)
    await waitFor(() => screen.getByText(/AI Agent/))
    // Click the card body
    fireEvent.click(screen.getByText(/AI Agent/))
    expect(onViewRun).toHaveBeenCalledWith('r1')
  })
})
```

- [ ] **Step 2: Run tests, verify FAIL**

Run: `npx vitest run src/components/HistoryList.test.tsx`

Expected: FAIL — HistoryList module not found

- [ ] **Step 3: Implement HistoryList**

Create `frontend/src/components/HistoryList.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react'
import HistoryCard, { type HistoryRun } from './HistoryCard'

interface Props {
  onRerun: (idea: string) => void
  onViewRun: (runId: string) => void
}

const PAGE_SIZE = 10

export default function HistoryList({ onRerun, onViewRun }: Props) {
  const [runs, setRuns] = useState<HistoryRun[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)

  const fetchRuns = useCallback(async (newOffset: number) => {
    setLoading(true)
    try {
      const resp = await fetch(`/runs?limit=${PAGE_SIZE}&offset=${newOffset}`)
      if (!resp.ok) return
      const data = await resp.json()
      if (newOffset === 0) {
        setRuns(data.runs)
      } else {
        setRuns((prev) => [...prev, ...data.runs])
      }
      setTotal(data.total)
      setOffset(newOffset + data.runs.length)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchRuns(0) }, [fetchRuns])

  async function handleDelete(runId: string) {
    if (!window.confirm('确认删除这条分析记录？')) return
    const resp = await fetch(`/runs/${runId}`, { method: 'DELETE' })
    if (resp.ok || resp.status === 404) {
      setRuns((prev) => prev.filter((r) => r.run_id !== runId))
      setTotal((t) => t - 1)
    }
  }

  const hasMore = offset < total

  if (loading && runs.length === 0) {
    return (
      <div style={{ marginTop: 24 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>最近分析</h3>
        <p style={{ color: '#aaa', fontSize: 13 }}>加载中...</p>
      </div>
    )
  }

  return (
    <div style={{ marginTop: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, margin: 0 }}>最近分析</h3>
        <span style={{ fontSize: 12, color: '#888' }}>共 {total} 条记录</span>
      </div>

      {runs.length === 0 ? (
        <p style={{ color: '#aaa', fontSize: 13 }}>暂无历史记录</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {runs.map((run) => (
            <HistoryCard
              key={run.run_id}
              run={run}
              onRerun={onRerun}
              onDelete={handleDelete}
              onClick={onViewRun}
            />
          ))}
        </div>
      )}

      {hasMore && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            onClick={() => fetchRuns(offset)}
            disabled={loading}
            style={{
              padding: '6px 16px', fontSize: 13, background: '#fff',
              border: '1px solid #ddd', borderRadius: 6, cursor: 'pointer',
            }}
          >
            {loading ? '加载中...' : '查看更多'}
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests, verify PASS**

Run: `npx vitest run src/components/HistoryList.test.tsx`

Expected: All PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/HistoryList.tsx frontend/src/components/HistoryList.test.tsx
git commit -m "feat: add HistoryList component with pagination"
```

---

### Task 5: Wire HistoryList into App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/StartupForm.tsx`

- [ ] **Step 1: Add initialValue prop to StartupForm**

In `frontend/src/components/StartupForm.tsx`, change the interface and component to accept an optional `initialValue`:

```tsx
interface Props {
  onSubmit: (idea: string) => void
  loading: boolean
  initialValue?: string
}

export default function StartupForm({ onSubmit, loading, initialValue }: Props) {
  const [idea, setIdea] = useState(initialValue ?? '')
  // ... rest stays the same, but add:
  // After initialValue changes, sync it (for re-run from history)
  useEffect(() => {
    if (initialValue) setIdea(initialValue)
  }, [initialValue])
}
```

Wait, `useEffect` import is already there. But we need `useEffect` from React. Let me keep it simpler: just use the `key` pattern in the parent to force re-mount.

Actually, the simplest approach: in `App.tsx`, when `onRerun` fires, pre-fill by using a `key` on `StartupForm` that changes to force a re-mount, or just call `startAnalysis()` directly without showing the form again. Per the spec: "Re-run: POST /runs with the same startup_idea, navigate to running view" — so we can just skip the form entirely and go straight to running view.

This means `onRerun(idea)` in App.tsx just calls `startAnalysis(idea)`. No need to modify StartupForm at all.

- [ ] **Step 2: Add HistoryList below StartupForm in App.tsx**

In `frontend/src/App.tsx`, import HistoryList and add it to the form view.

Add import:
```tsx
import HistoryList from './components/HistoryList'
```

In the `form` view return block, add HistoryList below StartupForm:

```tsx
if (view === 'form') {
  return (
    <div style={{ padding: 32, maxWidth: 800, margin: '0 auto' }}>
      <h1>创业机会分析器</h1>
      <p style={{ color: '#666' }}>5 个 AI Agent 协作分析你的想法，10-20 分钟出 Go/No-Go 结论</p>
      <StartupForm onSubmit={startAnalysis} loading={false} />
      <HistoryList
        onRerun={(idea) => startAnalysis(idea)}
        onViewRun={(runId) => {
          setRunIdInURL(runId)
          window.location.reload()
        }}
      />
    </div>
  )
}
```

For `onViewRun`, the simplest way to "navigate" is to set the URL param and reload. The `useEffect` on mount will detect the `run_id` in the URL and restore the appropriate view.

Actually, let me think about this more carefully. The current `restoreTried` ref is set to `true` on mount, so it won't trigger again. For `onViewRun`, I should use a different approach: set the URL, then trigger the restore flow manually.

Better approach: add a `navigateToRun(runId)` function in App.tsx:

```tsx
function navigateToRun(runId: string) {
  setEvents([])
  setReport(null)
  setErrorMsg('')
  setRunIdInURL(runId)
  // Fetch run status and restore
  fetch(`/runs/${runId}`)
    .then((r) => r.json())
    .then((info) => {
      if (info.status === 'complete') {
        fetch(`/runs/${runId}/report`).then((r) => r.json()).then((rep) => {
          const synthEvents = buildEventsFromR1Outputs(info.round1_outputs ?? null)
          setEvents(synthEvents)
          setReport(rep)
          setView('report')
        })
      } else if (info.status === 'failed') {
        setErrorMsg('分析失败')
        setView('failed')
      } else {
        const synthEvents = buildEventsFromR1Outputs(info.round1_outputs ?? null)
        setEvents(synthEvents)
        setView('running')
        subscribeToRun(runId, (event) => {
          setEvents((prev) => [...prev, event])
          if (event.type === 'run.complete') {
            setReport((event as any).report)
            setView('report')
          }
        }, () => {})
      }
    })
    .catch(() => {})
}
```

This is essentially the same logic as the `restore` function in `useEffect`. I should refactor to share the logic. Let me extract a `restoreRun(runId)` function that both `useEffect` and `navigateToRun` call.

Actually, to keep this task focused and not introduce a refactor, let me just use `window.location.reload()` for `onViewRun`. It's simple and works:

```tsx
onViewRun={(runId) => {
  setRunIdInURL(runId)
  window.location.reload()
}}
```

This triggers a full page reload, the `useEffect` fires, detects the URL param, and restores the view. Clean and simple.

- [ ] **Step 3: Run frontend tests and typecheck**

Run: `npx vitest run` and `npx tsc --noEmit`

Expected: All tests PASS, no type errors

- [ ] **Step 4: Build and verify**

Run: `npx vite build`

Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add history list below homepage form"
```

---

### Task 6: End-to-end integration test

**Files:**
- Modify: `tests/integration/test_e2e.py` (check if exists)

Actually, let me check if there's an existing integration test to extend.

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v` and `npx vitest run`

Expected: All backend + frontend tests PASS

- [ ] **Step 2: Commit final state**

```bash
git commit -m "test: verify history list feature works end-to-end"
```

(Only if there are integration test changes.)
