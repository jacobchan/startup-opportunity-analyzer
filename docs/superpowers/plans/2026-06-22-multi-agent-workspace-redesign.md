# 多 Agent 协作控制台重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 5-card `AgentCard` grid in `frontend/src/App.tsx` with a 3-column collaboration console (team sidebar / timeline / detail inspector) driven by a derived event-tree model.

**Architecture:** A pure `buildWorkspace(events, runInfo, report)` function compiles the flat SSE event stream into `Round[] → AgentTask[] → AgentTaskEvent[]`. `useRunWorkspace` wraps it with React state and selection. Four pure presentational components (`WorkspaceTopbar`, `AgentTeamSidebar`, `CollaborationTimeline`, `DetailInspector`) consume the derived state. `App.tsx` mounts the new `<Workspace>` and stops rendering the old grid.

**Tech Stack:** React 18, TypeScript, Vite, vitest, @testing-library/react, jsdom. No new dependencies.

## Global Constraints

- **No new npm dependencies.** Use only what's already in `frontend/package.json` (React 18, vitest, @testing-library/react, jsdom).
- **No backend changes.** Pause / terminate / retry / send-instruction are frontend-only placeholders, rendered as `disabled` buttons with tooltip text "暂停功能即将支持" / "重试任务将在下一版支持" / "运行中追加指令将在下一版支持".
- **Desktop-only.** `min-width: 1280px` on the workspace root; narrower viewports may scroll horizontally.
- **Chinese-first UI.** All visible copy is Simplified Chinese. Code identifiers stay English.
- **CSS strategy is mixed (relaxed from BEM-only):** Color tokens, spacing tokens, status colors, and shared utility classes (`.ws-dot`, `.ws-pill`, `.ws-clr-*`, etc.) live in `workspace.css` as CSS variables / BEM-style classes. Component layout (padding, flex, grid-template) MAY use inline `style={{...}}` — this matches the existing `App.tsx` / `AgentCard.tsx` / `ChallengeLog.tsx` pattern in the codebase. Status-color and animation hooks MUST go through className, never inline, so the palette stays centralized.
- **Status colors**: running `#2563eb`, done `#08783e`, waiting `#86868b`, needs_input `#b45309`, failed `#c22f2f`.
- **No animations** except the existing `history-pulse` keyframe (already defined in `HistoryCard.css`), reused only on (a) the left-sidebar status dot when `running` and (b) the current running task's left bar.
- **Tests are co-located** with source (e.g., `AgentTeamSidebar.tsx` ↔ `AgentTeamSidebar.test.tsx`). Pure-function tests follow the same rule.
- **All tests must pass** after each task. Run `cd frontend && npm run test` before committing.
- **Commit message style**: `feat(workspace): …`, `refactor(workspace): …`, `test(workspace): …`, `docs(workspace): …`, `chore(workspace): …`.

## File Structure

```
frontend/src/
├── App.tsx                                  # Modify (Task 11)
├── App.test.tsx                             # Modify (Task 11)
├── lib/
│   ├── types.ts                             # Unchanged
│   ├── sse.ts                               # Unchanged
│   ├── workspace-types.ts                   # Create (Task 1)
│   ├── workspace-constants.ts               # Create (Task 1)
│   ├── buildWorkspace.ts                    # Create (Task 2)
│   ├── buildWorkspace.test.ts               # Create (Task 2)
│   ├── useRunWorkspace.ts                   # Create (Task 3)
│   └── useRunWorkspace.test.ts              # Create (Task 3)
└── components/
    ├── AgentCard.tsx                        # Keep (do not delete, no longer imported)
    ├── AgentCard.test.tsx                   # Keep
    ├── ChallengeLog.tsx                     # Keep
    ├── ChallengeLog.test.tsx                # Keep
    ├── EvidenceReport.tsx                   # Unchanged (referenced by DetailInspector)
    ├── EvidenceReport.test.tsx              # Unchanged
    ├── HistoryCard.tsx / *.css / *.test.tsx # Unchanged
    ├── HistoryList.tsx / *.test.tsx         # Unchanged
    ├── StartupForm.tsx / *.test.tsx         # Unchanged
    └── workspace/                           # Create dir (Task 4)
        ├── workspace.css                    # Create (Task 4, no test)
        ├── Workspace.tsx                    # Create (Task 11)
        ├── WorkspaceTopbar.tsx              # Create (Task 6)
        ├── WorkspaceTopbar.test.tsx         # Create (Task 6)
        ├── AgentAvatar.tsx                  # Create (Task 5)
        ├── AgentAvatar.test.tsx             # Create (Task 5)
        ├── AgentTeamSidebar.tsx             # Create (Task 7)
        ├── AgentTeamSidebar.test.tsx        # Create (Task 7)
        ├── CollaborationTimeline.tsx        # Create (Task 9)
        ├── CollaborationTimeline.test.tsx   # Create (Task 9)
        ├── TimelineTaskItem.tsx             # Create (Task 8)
        ├── TimelineTaskItem.test.tsx        # Create (Task 8)
        ├── DetailInspector.tsx              # Create (Task 10)
        ├── DetailInspector.test.tsx         # Create (Task 10)
        ├── workspace-flow.test.tsx          # Create (Task 12)
        └── artifact-renderers.tsx           # Create (Task 10)
```

**Responsibilities:**

- `workspace-types.ts` — All shared TS types (`RoundId`, `AgentStatus`, `AgentTaskEvent`, `AgentTask`, `Round`, `AgentSummary`, `WorkspaceState`, `SelectedTarget`).
- `workspace-constants.ts` — Static config (`ROUND_META`, `EXPECTED_TASKS_PER_AGENT`, `AGENT_LABELS`, `AGENT_ORDER`, `STATUS_LABEL`).
- `buildWorkspace.ts` — Pure function: `(events, runInfo, report) => WorkspaceState`. Single pass, no React.
- `useRunWorkspace.ts` — React hook wrapping `buildWorkspace` + selection state + restore-event synthesis + dedupe.
- `AgentAvatar.tsx` — Shared "status dot + label" block used by sidebar and inspector.
- `WorkspaceTopbar.tsx` — Back button / task name / progress / status badge / action buttons.
- `AgentTeamSidebar.tsx` — Orchestrator card + agent list.
- `CollaborationTimeline.tsx` — Three rounds, expand/collapse, renders `TimelineTaskItem` list.
- `TimelineTaskItem.tsx` — Single task node with expandable artifact section.
- `DetailInspector.tsx` — Right pane, switches between Agent / Event / Artifact panels.
- `artifact-renderers.tsx` — Per-agent-type artifact renderers + JSON fallback.
- `Workspace.tsx` — Container that owns the hook and wires the four children.

---

## Task 1: Type definitions and constants

**Files:**
- Create: `frontend/src/lib/workspace-types.ts`
- Create: `frontend/src/lib/workspace-constants.ts`

**Interfaces:**
- Consumes: `AgentName` from `frontend/src/lib/types.ts`
- Produces: `RoundId`, `AgentStatus`, `AgentTaskEvent`, `AgentTask`, `Round`, `AgentSummary`, `WorkspaceState`, `SelectedTarget`, `ROUND_META`, `EXPECTED_TASKS_PER_AGENT`, `AGENT_LABELS`, `AGENT_ORDER`, `STATUS_LABEL`

- [ ] **Step 1: Create `workspace-types.ts`**

```ts
// frontend/src/lib/workspace-types.ts
import type { AgentName } from './types'

export type RoundId = 'r1' | 'r2' | 'r3'

export type AgentStatus =
  | 'pending'
  | 'running'
  | 'waiting'
  | 'needs_input'
  | 'done'
  | 'failed'

export type TaskEventKind =
  | 'start'
  | 'tool'
  | 'message'
  | 'challenge_issued'
  | 'challenge_responded'
  | 'end'

export interface AgentTaskEvent {
  id: string
  kind: TaskEventKind
  timestamp: number
  agent: AgentName
  round: RoundId
  payload: Record<string, unknown>
}

export interface AgentTask {
  id: string                  // `${round}:${agent}:${subRound ?? ''}`
  agent: AgentName
  round: RoundId
  subRound?: 'A' | 'B'
  status: AgentStatus
  startedAt: number | null
  endedAt: number | null
  events: AgentTaskEvent[]
  output_summary?: unknown
  error?: string
}

export interface Round {
  id: RoundId
  title: string
  subtitle: string
  status: 'pending' | 'running' | 'done' | 'failed'
  tasks: AgentTask[]
  transitionedAt: number | null
}

export interface AgentSummary {
  name: AgentName
  label: string
  role: 'orchestrator' | 'analyst'
  status: AgentStatus
  currentAction: string
  progress: { done: number; total: number }
}

export interface WorkspaceState {
  rounds: Round[]
  agents: AgentSummary[]
  progress: { done: number; total: 11; percent: number }
  status: 'pending' | 'running' | 'done' | 'failed'
}

export type SelectedTarget =
  | { kind: 'agent'; agent: AgentName }
  | { kind: 'event'; taskId: string; eventId: string }
  | { kind: 'artifact'; taskId: string }
  | null
```

- [ ] **Step 2: Create `workspace-constants.ts`**

```ts
// frontend/src/lib/workspace-constants.ts
import type { AgentName } from './types'
import type { RoundId } from './workspace-types'

export const ROUND_META: Record<RoundId, { title: string; subtitle: string }> = {
  r1: {
    title: '第一轮 · 独立分析',
    subtitle: '4 个 Agent 并行展开市场、竞品、财务、风险',
  },
  r2: {
    title: '第二轮 · 交叉挑战',
    subtitle: '市场/竞品/财务 Agent 互相质询并回应',
  },
  r3: {
    title: '第三轮 · 战略综合',
    subtitle: '战略顾问综合所有输入，给出 Go/No-Go 结论',
  },
}

export const EXPECTED_TASKS_PER_AGENT: Record<AgentName, number> = {
  market_analyst: 3,        // R1 + R2-A + R2-B
  competitor_researcher: 3,
  finance_analyst: 3,
  risk_reviewer: 1,
  strategy_advisor: 1,
}

export const PROGRESS_TOTAL = 11

export const AGENT_LABELS: Record<AgentName, string> = {
  market_analyst: '市场分析师',
  competitor_researcher: '竞品调研员',
  finance_analyst: '财务分析师',
  risk_reviewer: '风险评审员',
  strategy_advisor: '战略顾问',
}

// Display order in the left sidebar (Orchestrator handled separately).
export const AGENT_ORDER: AgentName[] = [
  'market_analyst',
  'competitor_researcher',
  'finance_analyst',
  'risk_reviewer',
]

export const STATUS_LABEL: Record<AgentStatus, string> = {
  pending: '待启动',
  running: '执行中',
  waiting: '等待依赖',
  needs_input: '需要确认',
  done: '已完成',
  failed: '失败',
}

// Re-export for convenience
import type { AgentStatus } from './workspace-types'
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/workspace-types.ts frontend/src/lib/workspace-constants.ts
git commit -m "feat(workspace): add derived-data types and constants"
```

---

## Task 2: Pure `buildWorkspace` function

The hardest algorithm. Pure function, no React. Tested exhaustively before any UI exists.

**Files:**
- Create: `frontend/src/lib/buildWorkspace.ts`
- Create: `frontend/src/lib/buildWorkspace.test.ts`

**Interfaces:**
- Consumes: `RunEvent` from `./types`, all types/constants from Task 1.
- Produces: `buildWorkspace(events, runInfo, report): WorkspaceState`

- [ ] **Step 1: Write the first failing test (empty events)**

```ts
// frontend/src/lib/buildWorkspace.test.ts
import { describe, it, expect } from 'vitest'
import { buildWorkspace } from './buildWorkspace'
import type { RunEvent } from './types'

describe('buildWorkspace', () => {
  it('returns all-pending state for empty events', () => {
    const state = buildWorkspace([], { run_id: 'r1', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }, null)
    expect(state.status).toBe('pending')
    expect(state.progress).toEqual({ done: 0, total: 11, percent: 0 })
    expect(state.rounds).toHaveLength(3)
    expect(state.rounds[0].status).toBe('pending')
    expect(state.agents.every((a) => a.status === 'pending')).toBe(true)
    expect(state.agents.find((a) => a.name === 'strategy_advisor')?.role).toBe('orchestrator')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/buildWorkspace.test.ts`
Expected: FAIL with "Function buildWorkspace is not defined" or import error.

- [ ] **Step 3: Write minimal `buildWorkspace.ts` to make the empty test pass**

```ts
// frontend/src/lib/buildWorkspace.ts
import type { RunEvent, AgentName, RunInfo } from './types'
import {
  ROUND_META,
  AGENT_LABELS,
  AGENT_ORDER,
  EXPECTED_TASKS_PER_AGENT,
  PROGRESS_TOTAL,
} from './workspace-constants'
import type {
  RoundId,
  AgentStatus,
  AgentTask,
  AgentTaskEvent,
  Round,
  AgentSummary,
  WorkspaceState,
  TaskEventKind,
} from './workspace-types'

const ALL_AGENTS: AgentName[] = [
  'market_analyst',
  'competitor_researcher',
  'finance_analyst',
  'risk_reviewer',
  'strategy_advisor',
]

const ORCHESTRATOR: AgentName = 'strategy_advisor'

function emptyRounds(): Round[] {
  return (['r1', 'r2', 'r3'] as RoundId[]).map((id) => ({
    id,
    title: ROUND_META[id].title,
    subtitle: ROUND_META[id].subtitle,
    status: 'pending' as const,
    tasks: [],
    transitionedAt: null,
  }))
}

function emptyAgentSummaries(): AgentSummary[] {
  const summaries: AgentSummary[] = []
  for (const name of [ORCHESTRATOR, ...AGENT_ORDER]) {
    summaries.push({
      name,
      label: AGENT_LABELS[name],
      role: name === ORCHESTRATOR ? 'orchestrator' : 'analyst',
      status: 'pending',
      currentAction: '等待启动',
      progress: { done: 0, total: EXPECTED_TASKS_PER_AGENT[name] },
    })
  }
  return summaries
}

export function buildWorkspace(
  events: RunEvent[],
  runInfo: RunInfo | null,
  report: unknown,
): WorkspaceState {
  const rounds = emptyRounds()
  const agents = emptyAgentSummaries()
  const done = 0
  const isComplete = runInfo?.status === 'complete'
  return {
    rounds,
    agents,
    progress: { done, total: PROGRESS_TOTAL, percent: isComplete ? 100 : 0 },
    status: 'pending',
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/buildWorkspace.test.ts`
Expected: PASS.

- [ ] **Step 5: Add test for `run.start` event**

Append to `buildWorkspace.test.ts`:

```ts
it('marks r1 as running when run.start fires', () => {
  const events: RunEvent[] = [
    { type: 'run.start', run_id: 'r1', startup_idea: 'x' },
  ]
  const state = buildWorkspace(events, null, null)
  expect(state.rounds[0].status).toBe('running')
  expect(state.status).toBe('running')
})
```

- [ ] **Step 6: Run test — expect FAIL**

Run: `cd frontend && npx vitest run src/lib/buildWorkspace.test.ts`
Expected: FAIL on the new test (we still return status `'pending'`).

- [ ] **Step 7: Implement event-loop skeleton**

Replace the body of `buildWorkspace` in `buildWorkspace.ts`:

```ts
export function buildWorkspace(
  events: RunEvent[],
  runInfo: RunInfo | null,
  report: unknown,
): WorkspaceState {
  const rounds = emptyRounds()
  const agents = emptyAgentSummaries()
  // taskId → AgentTask
  const taskMap = new Map<string, AgentTask>()
  // (round, agent) → currently-open task (for event routing)
  const openTaskByAgent = new Map<string, AgentTask>()
  // round of the currently-routing events
  let currentRoundId: RoundId = 'r1'

  let ts = 0
  const nextTs = () => ++ts

  const getOrCreateRound = (id: RoundId) => rounds.find((r) => r.id === id)!

  const markRoundStatus = (id: RoundId) => {
    const r = getOrCreateRound(id)
    if (r.tasks.some((t) => t.status === 'failed')) r.status = 'failed'
    else if (r.tasks.some((t) => t.status === 'running')) r.status = 'running'
    else if (r.tasks.length > 0 && r.tasks.every((t) => t.status === 'done')) r.status = 'done'
    else r.status = 'pending'
  }

  const inferWaitingStates = () => {
    // R1 risk_reviewer: waiting until other 3 R1 tasks done
    const r1 = getOrCreateRound('r1')
    const r1TasksByAgent = new Map<AgentName, AgentTask>()
    for (const t of r1.tasks) r1TasksByAgent.set(t.agent, t)
    const firstThreeDone =
      r1TasksByAgent.get('market_analyst')?.status === 'done' &&
      r1TasksByAgent.get('competitor_researcher')?.status === 'done' &&
      r1TasksByAgent.get('finance_analyst')?.status === 'done'
    const riskTask = r1TasksByAgent.get('risk_reviewer')
    if (firstThreeDone && riskTask && riskTask.status === 'pending') {
      riskTask.status = 'waiting'
      riskTask.events.push({
        id: `r1:risk_reviewer:inferred-waiting`,
        kind: 'message',
        timestamp: nextTs(),
        agent: 'risk_reviewer',
        round: 'r1',
        payload: { note: 'inferred waiting on first three R1 tasks' },
      })
    }
  }

  const findAgentTaskInRound = (round: RoundId, agent: AgentName): AgentTask | undefined => {
    return getOrCreateRound(round).tasks.find((t) => t.agent === agent)
  }

  // Find or create the currently-running task for (round, agent).
  // For R2: if one task already exists and is done (issue phase complete),
  // create a new R2-B task on the next agent.start.
  const routeAgentStart = (round: RoundId, agent: AgentName): AgentTask => {
    const existing = findAgentTaskInRound(round, agent)
    if (round === 'r2' && existing && existing.status === 'done') {
      // Start R2-B
      const task: AgentTask = {
        id: `r2:${agent}:B`,
        agent,
        round: 'r2',
        subRound: 'B',
        status: 'running',
        startedAt: nextTs(),
        endedAt: null,
        events: [],
      }
      getOrCreateRound('r2').tasks.push(task)
      openTaskByAgent.set(`r2:${agent}`, task)
      return task
    }
    if (existing && existing.status === 'pending') {
      existing.status = 'running'
      existing.startedAt = nextTs()
      openTaskByAgent.set(`${round}:${agent}`, existing)
      return existing
    }
    if (existing && existing.status === 'waiting') {
      existing.status = 'running'
      existing.startedAt = nextTs()
      openTaskByAgent.set(`${round}:${agent}`, existing)
      return existing
    }
    // Create fresh
    const id = round === 'r2' ? `r2:${agent}:A` : `${round}:${agent}`
    const task: AgentTask = {
      id,
      agent,
      round,
      subRound: round === 'r2' ? 'A' : undefined,
      status: 'running',
      startedAt: nextTs(),
      endedAt: null,
      events: [],
    }
    getOrCreateRound(round).tasks.push(task)
    openTaskByAgent.set(`${round}:${agent}`, task)
    return task
  }

  const appendEvent = (
    task: AgentTask,
    kind: TaskEventKind,
    payload: Record<string, unknown>,
  ) => {
    task.events.push({
      id: `${task.id}:${task.events.length}`,
      kind,
      timestamp: nextTs(),
      agent: task.agent,
      round: task.round,
      payload,
    })
  }

  for (const ev of events) {
    switch (ev.type) {
      case 'run.start':
        getOrCreateRound('r1').status = 'running'
        getOrCreateRound('r1').transitionedAt = nextTs()
        break

      case 'round.transition': {
        const toRound = (ev as any).to_round as string
        const id: RoundId =
          toRound === 'round1' || toRound === 'r1' ? 'r1'
          : toRound === 'round2' || toRound === 'r2' ? 'r2'
          : 'r3'
        currentRoundId = id
        const r = getOrCreateRound(id)
        r.status = 'running'
        r.transitionedAt = nextTs()
        break
      }

      case 'agent.start': {
        const agent = (ev as any).agent as AgentName
        const roundRaw = (ev as any).round as string
        const round: RoundId =
          roundRaw === 'round1' || roundRaw === 'r1' ? 'r1'
          : roundRaw === 'round2' || roundRaw === 'r2' ? 'r2'
          : 'r3'
        const task = routeAgentStart(round, agent)
        appendEvent(task, 'start', ev as any)
        break
      }

      case 'tool.start': {
        const agent = (ev as any).agent as AgentName
        const task = openTaskByAgent.get(`${currentRoundId}:${agent}`)
        if (task) appendEvent(task, 'tool', ev as any)
        break
      }

      case 'tool.end': {
        const agent = (ev as any).agent as AgentName
        const task = openTaskByAgent.get(`${currentRoundId}:${agent}`)
        if (task) appendEvent(task, 'tool', ev as any)
        break
      }

      case 'agent.message': {
        const agent = (ev as any).agent as AgentName
        const task = openTaskByAgent.get(`${currentRoundId}:${agent}`)
        if (task) appendEvent(task, 'message', ev as any)
        break
      }

      case 'challenge.issued': {
        const issuer = (ev as any).issuer as AgentName
        const task = openTaskByAgent.get(`${currentRoundId}:${issuer}`)
        if (task) appendEvent(task, 'challenge_issued', ev as any)
        break
      }

      case 'challenge.responded': {
        const target = (ev as any).target as AgentName
        // Prefer R2-B task; fall back to R2-A (conservative — see spec §4.3)
        const r2Tasks = getOrCreateRound('r2').tasks.filter((t) => t.agent === target)
        const r2b = r2Tasks.find((t) => t.subRound === 'B')
        const r2a = r2Tasks.find((t) => t.subRound === 'A')
        const task = r2b ?? r2a
        if (task) appendEvent(task, 'challenge_responded', ev as any)
        break
      }

      case 'agent.end': {
        const agent = (ev as any).agent as AgentName
        const roundRaw = (ev as any).round as string
        const round: RoundId =
          roundRaw === 'round1' || roundRaw === 'r1' ? 'r1'
          : roundRaw === 'round2' || roundRaw === 'r2' ? 'r2'
          : 'r3'
        const key = `${round}:${agent}`
        // For R2 prefer the currently-open task (which could be A or B)
        const task = openTaskByAgent.get(key)
        if (task) {
          appendEvent(task, 'end', ev as any)
          const out = (ev as any).output_summary
          task.output_summary = out
          if (out && typeof out === 'object' && 'error' in (out as any)) {
            task.status = 'failed'
            task.error = String((out as any).error)
          } else {
            task.status = 'done'
          }
          task.endedAt = nextTs()
          openTaskByAgent.delete(key)
        }
        markRoundStatus(round)
        break
      }

      case 'run.complete':
        getOrCreateRound('r3').status = 'done'
        break

      case 'run.failed': {
        const errorStr = String((ev as any).error ?? '')
        // Conservative attribution: only mark agent failed on exact token match
        for (const name of ALL_AGENTS) {
          const key = `${currentRoundId}:${name}`
          const task = openTaskByAgent.get(key)
          if (task && errorStr.split(/\W+/).includes(name)) {
            task.status = 'failed'
            task.error = errorStr
            task.endedAt = nextTs()
            openTaskByAgent.delete(key)
          }
        }
        break
      }

      default:
        // Unknown event type — ignore
        break
    }

    inferWaitingStates()
  }

  // Aggregate per-agent summaries
  for (const summary of agents) {
    const tasksForAgent: AgentTask[] = []
    for (const r of rounds) {
      for (const t of r.tasks) {
        if (t.agent === summary.name) tasksForAgent.push(t)
      }
    }
    if (tasksForAgent.length === 0) continue

    // status precedence: failed > running > waiting > needs_input > done > pending
    const precedence: AgentStatus[] = ['failed', 'running', 'waiting', 'needs_input', 'done', 'pending']
    summary.status = precedence.find((s) => tasksForAgent.some((t) => t.status === s)) ?? 'pending'

    const doneCount = tasksForAgent.filter((t) => t.status === 'done').length
    summary.progress = { done: doneCount, total: EXPECTED_TASKS_PER_AGENT[summary.name] }

    // currentAction from most recent event
    const allEvents = tasksForAgent.flatMap((t) => t.events).sort((a, b) => b.timestamp - a.timestamp)
    summary.currentAction = describeCurrentAction(allEvents[0], summary.status)
  }

  const done = rounds.flatMap((r) => r.tasks).filter((t) => t.status === 'done').length
  const isComplete = runInfo?.status === 'complete'
  const anyFailed = rounds.some((r) => r.status === 'failed')
  const anyRunning = rounds.some((r) => r.status === 'running')

  return {
    rounds,
    agents,
    progress: {
      done,
      total: PROGRESS_TOTAL,
      percent: isComplete ? 100 : Math.round((done / PROGRESS_TOTAL) * 100),
    },
    status: anyFailed ? 'failed' : anyRunning ? 'running' : isComplete ? 'done' : 'pending',
  }
}

function describeCurrentAction(
  ev: AgentTaskEvent | undefined,
  status: AgentStatus,
): string {
  if (!ev) {
    if (status === 'waiting') return '等待前置任务完成'
    if (status === 'done') return '已完成'
    if (status === 'failed') return '执行失败'
    return '等待启动'
  }
  switch (ev.kind) {
    case 'start':
      return '开始分析'
    case 'tool': {
      const payload = ev.payload
      if (payload.type === 'tool.start') {
        return `正在搜索：${String(payload.input_preview ?? '').slice(0, 40)}`
      }
      const evidenceId = (payload as any).evidence_id
      return evidenceId ? `搜索完成 → ${evidenceId}` : '搜索完成'
    }
    case 'message':
      return String((ev.payload as any).content_summary ?? '').slice(0, 60)
    case 'challenge_issued': {
      const p = ev.payload as any
      return `向 ${AGENT_LABELS[p.target as AgentName] ?? p.target} 发起挑战：${String(p.claim ?? '').slice(0, 40)}`
    }
    case 'challenge_responded': {
      const p = ev.payload as any
      return `回应 ${AGENT_LABELS[p.issuer as AgentName] ?? p.issuer}：${String(p.response ?? '').slice(0, 40)}`
    }
    case 'end':
      return '提交产物'
  }
}
```

- [ ] **Step 8: Run tests — verify both pass**

Run: `cd frontend && npx vitest run src/lib/buildWorkspace.test.ts`
Expected: PASS (both tests).

- [ ] **Step 9: Add the rest of the edge-case tests**

Append to `buildWorkspace.test.ts`:

```ts
import type { AgentName } from './types'

function ev(partial: any): RunEvent {
  return partial as RunEvent
}

describe('buildWorkspace edge cases', () => {
  it('infers risk_reviewer waiting when first three R1 tasks done', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 1 } }),
      ev({ type: 'agent.start', agent: 'competitor_researcher', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'competitor_researcher', round: 'round1', output_summary: {} }),
      ev({ type: 'agent.start', agent: 'finance_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'finance_analyst', round: 'round1', output_summary: {} }),
    ]
    const state = buildWorkspace(events, null, null)
    const risk = state.rounds[0].tasks.find((t) => t.agent === 'risk_reviewer')
    expect(risk?.status).toBe('waiting')
    const riskSummary = state.agents.find((a) => a.name === 'risk_reviewer')
    expect(riskSummary?.status).toBe('waiting')
  })

  it('routes R2 second agent.start to a new R2-B task', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'round.transition', from_round: 'round1', to_round: 'round2' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round2', output_summary: {} }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
    ]
    const state = buildWorkspace(events, null, null)
    const marketR2 = state.rounds[1].tasks.filter((t) => t.agent === 'market_analyst')
    expect(marketR2).toHaveLength(2)
    expect(marketR2[0].subRound).toBe('A')
    expect(marketR2[0].status).toBe('done')
    expect(marketR2[1].subRound).toBe('B')
    expect(marketR2[1].status).toBe('running')
  })

  it('marks task failed when output_summary has error', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { error: 'timeout' } }),
    ]
    const state = buildWorkspace(events, null, null)
    const t = state.rounds[0].tasks.find((x) => x.agent === 'market_analyst')
    expect(t?.status).toBe('failed')
    expect(t?.error).toBe('timeout')
  })

  it('does NOT attribute run.failed to agent when name not present in error text', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'run.failed', run_id: 'r', error: 'network error', partial: false }),
    ]
    const state = buildWorkspace(events, null, null)
    const t = state.rounds[0].tasks.find((x) => x.agent === 'market_analyst')
    // task is still running because attribution didn't fire; round status reflects run failure via global state
    expect(t?.status).toBe('running')
  })

  it('attributes run.failed to agent on exact token match', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'run.failed', run_id: 'r', error: 'market_analyst crashed mid-call', partial: false }),
    ]
    const state = buildWorkspace(events, null, null)
    const t = state.rounds[0].tasks.find((x) => x.agent === 'market_analyst')
    expect(t?.status).toBe('failed')
  })

  it('forces 100% progress when runInfo.status is complete even if tasks under-counted', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: {} }),
    ]
    const state = buildWorkspace(events, { run_id: 'r', startup_idea: 'x', status: 'complete', created_at: null, completed_at: null }, null)
    expect(state.progress.percent).toBe(100)
    expect(state.status).toBe('done')
  })

  it('routes challenge.responded to R2-B when present, falls back to R2-A', () => {
    const eventsWithR2B: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'round.transition', from_round: 'round1', to_round: 'round2' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round2', output_summary: {} }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'challenge.responded', challenge_id: 'c1', target: 'market_analyst', response: 'ok', verdict: 'accepted' }),
    ]
    const s1 = buildWorkspace(eventsWithR2B, null, null)
    const r2b = s1.rounds[1].tasks.find((t) => t.agent === 'market_analyst' && t.subRound === 'B')!
    expect(r2b.events.some((e) => e.kind === 'challenge_responded')).toBe(true)

    const eventsWithoutR2B: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'round.transition', from_round: 'round1', to_round: 'round2' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'challenge.responded', challenge_id: 'c1', target: 'market_analyst', response: 'ok', verdict: 'accepted' }),
    ]
    const s2 = buildWorkspace(eventsWithoutR2B, null, null)
    const r2a = s2.rounds[1].tasks.find((t) => t.agent === 'market_analyst' && t.subRound === 'A')!
    expect(r2a.events.some((e) => e.kind === 'challenge_responded')).toBe(true)
  })
})
```

- [ ] **Step 10: Run full test suite for this file**

Run: `cd frontend && npx vitest run src/lib/buildWorkspace.test.ts`
Expected: all tests PASS.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/lib/buildWorkspace.ts frontend/src/lib/buildWorkspace.test.ts
git commit -m "feat(workspace): add buildWorkspace pure derivation function"
```

---

## Task 3: `useRunWorkspace` hook (restore + dedupe + selection)

**Files:**
- Create: `frontend/src/lib/useRunWorkspace.ts`
- Create: `frontend/src/lib/useRunWorkspace.test.ts`

**Interfaces:**
- Consumes: `buildWorkspace` from Task 2, `RunEvent`, `RunInfo` from `./types`.
- Produces: `useRunWorkspace(events, runInfo, report)` → `{ state, selectedTarget, setSelectedTarget }`

- [ ] **Step 1: Write the first failing test**

```ts
// frontend/src/lib/useRunWorkspace.test.ts
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRunWorkspace } from './useRunWorkspace'
import type { RunEvent } from './types'

describe('useRunWorkspace', () => {
  it('defaults selection to strategy_advisor', () => {
    const { result } = renderHook(() => useRunWorkspace([], null, null))
    expect(result.current.selectedTarget).toEqual({ kind: 'agent', agent: 'strategy_advisor' })
  })

  it('dedupes synthetic restore events when real events arrive', () => {
    const synthetic: RunEvent[] = [
      { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 'synthetic' } } as any,
    ]
    const { rerender, result } = renderHook(({ ev }: { ev: RunEvent[] }) => useRunWorkspace(ev, null, null), {
      initialProps: { ev: synthetic },
    })
    // First render: synthetic event counted
    expect(result.current.state.progress.done).toBe(1)

    const real: RunEvent[] = [
      { type: 'run.start', run_id: 'r', startup_idea: 'x' } as any,
      { type: 'agent.start', agent: 'market_analyst', round: 'round1' } as any,
      { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 'real' } } as any,
    ]
    rerender({ ev: real })
    // Real events fully replace synthetic ones; same single agent done
    expect(result.current.state.progress.done).toBe(1)
    const market = result.current.state.rounds[0].tasks.find((t) => t.agent === 'market_analyst')
    expect(market?.events).toHaveLength(2) // start + end (synthetic gone)
  })

  it('switches selection via setSelectedTarget', () => {
    const { result } = renderHook(() => useRunWorkspace([], null, null))
    act(() => {
      result.current.setSelectedTarget({ kind: 'agent', agent: 'market_analyst' })
    })
    expect(result.current.selectedTarget).toEqual({ kind: 'agent', agent: 'market_analyst' })
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd frontend && npx vitest run src/lib/useRunWorkspace.test.ts`
Expected: FAIL "Cannot find module './useRunWorkspace'".

- [ ] **Step 3: Implement `useRunWorkspace.ts`**

```ts
// frontend/src/lib/useRunWorkspace.ts
import { useMemo, useState } from 'react'
import type { RunEvent, RunInfo, AgentName } from './types'
import { buildWorkspace } from './buildWorkspace'
import type { WorkspaceState, SelectedTarget } from './workspace-types'

/**
 * Build synthetic events for an in-progress restore, mirroring the logic
 * originally in App.tsx (buildEventsFromR1Outputs). Prefer the live
 * checkpoint (deliberation_state.r1_outputs) over the legacy snapshot.
 */
export function synthesizeFromCheckpoint(runInfo: RunInfo | null): RunEvent[] {
  if (!runInfo) return []
  const anyInfo = runInfo as any
  const outputs = anyInfo.deliberation_state?.r1_outputs ?? anyInfo.round1_outputs ?? null
  if (!outputs || typeof outputs !== 'object') return []
  const events: RunEvent[] = []
  for (const [agent, output] of Object.entries(outputs as Record<string, unknown>)) {
    events.push({
      type: 'agent.end',
      agent: agent as AgentName,
      round: 'round1',
      output_summary: output,
    } as RunEvent)
  }
  return events
}

/**
 * Detect whether the current event stream looks like the synthetic restore
 * stream (only agent.end events, no run.start / agent.start). When the real
 * SSE stream arrives, it always contains at least one run.start, so this
 * becomes our "real" signal.
 */
function isSyntheticOnly(events: RunEvent[]): boolean {
  if (events.length === 0) return false
  return events.every((e) => e.type === 'agent.end')
}

export interface UseRunWorkspaceResult {
  state: WorkspaceState
  selectedTarget: SelectedTarget
  setSelectedTarget: (t: SelectedTarget) => void
}

export function useRunWorkspace(
  events: RunEvent[],
  runInfo: RunInfo | null,
  report: unknown,
): UseRunWorkspaceResult {
  const [selectedTarget, setSelectedTarget] = useState<SelectedTarget>({
    kind: 'agent',
    agent: 'strategy_advisor',
  })

  const state = useMemo<WorkspaceState>(() => {
    // If we have a real stream, use it as-is.
    // If we have a synthetic-only stream and no run.start yet, also
    // fold in synthesizeFromCheckpoint so a restored page shows
    // prior progress without waiting for SSE replay.
    let merged = events
    if (isSyntheticOnly(events)) {
      const synth = synthesizeFromCheckpoint(runInfo)
      if (synth.length > 0) merged = synth
    }
    // Dedupe: when the stream transitions from synthetic-only to real
    // (run.start appears), the synthetic agent.end events are dropped
    // because the real stream will re-supply them with full context.
    // We detect the transition by presence of any non-agent.end event.
    const hasRealSignal = merged.some((e) => e.type !== 'agent.end')
    const filtered = hasRealSignal ? merged.filter((e) => e.type !== 'agent.end' || !isFromSynthetic(e)) : merged
    return buildWorkspace(filtered, runInfo, report)
  }, [events, runInfo, report])

  return { state, selectedTarget, setSelectedTarget }
}

function isFromSynthetic(ev: RunEvent): boolean {
  // Synthetic events are tagged with a non-standard marker so we can
  // tell them apart from real agent.end events once both are present.
  // We add the marker in synthesizeFromCheckpoint via a Symbol-like key.
  return Boolean((ev as any).__synthetic__)
}
```

Update `synthesizeFromCheckpoint` to tag synthetic events:

```ts
export function synthesizeFromCheckpoint(runInfo: RunInfo | null): RunEvent[] {
  if (!runInfo) return []
  const anyInfo = runInfo as any
  const outputs = anyInfo.deliberation_state?.r1_outputs ?? anyInfo.round1_outputs ?? null
  if (!outputs || typeof outputs !== 'object') return []
  const events: RunEvent[] = []
  for (const [agent, output] of Object.entries(outputs as Record<string, unknown>)) {
    events.push({
      type: 'agent.end',
      agent: agent as AgentName,
      round: 'round1',
      output_summary: output,
      __synthetic__: true,
    } as RunEvent)
  }
  return events
}
```

- [ ] **Step 4: Update the test to tag synthetic events with `__synthetic__: true`**

In `useRunWorkspace.test.ts`, change the synthetic event to:

```ts
const synthetic: RunEvent[] = [
  { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 'synthetic' }, __synthetic__: true } as any,
]
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `cd frontend && npx vitest run src/lib/useRunWorkspace.test.ts`
Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/useRunWorkspace.ts frontend/src/lib/useRunWorkspace.test.ts
git commit -m "feat(workspace): add useRunWorkspace hook with restore/dedupe"
```

---

## Task 4: `workspace.css` — CSS variables + grid shell

**Files:**
- Create: `frontend/src/components/workspace/workspace.css`

- [ ] **Step 1: Create the CSS file**

```css
/* frontend/src/components/workspace/workspace.css */

:root {
  --ws-bg:            #f7f7f5;
  --ws-surface:       #ffffff;
  --ws-border:        #e8e8e8;
  --ws-border-strong: #d2d2d2;
  --ws-text:          #1d1d1f;
  --ws-text-muted:    #737377;
  --ws-text-faint:    #a1a1a6;
  --ws-radius:        10px;
  --ws-radius-sm:     6px;
  --ws-shadow-soft:   0 1px 2px rgba(0, 0, 0, 0.03);

  --ws-status-running:      #2563eb;
  --ws-status-running-bg:   #eff6ff;
  --ws-status-done:         #08783e;
  --ws-status-done-bg:      #edf8f2;
  --ws-status-waiting:      #86868b;
  --ws-status-waiting-bg:   #f2f4f7;
  --ws-status-needs_input:  #b45309;
  --ws-status-needs_input-bg:#fff5e8;
  --ws-status-failed:       #c22f2f;
  --ws-status-failed-bg:    #fff0f0;

  --ws-font-sans: -apple-system, "PingFang SC", "Microsoft YaHei",
                  "Helvetica Neue", Arial, sans-serif;
}

.ws-shell {
  min-width: 1280px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--ws-bg);
  color: var(--ws-text);
  font-family: var(--ws-font-sans);
  font-size: 13px;
  line-height: 1.5;
}

.ws-body {
  flex: 1;
  display: grid;
  grid-template-columns: 240px 1fr 320px;
  min-height: 0;
}

.ws-col-left,
.ws-col-center,
.ws-col-right {
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ws-col-left  { border-right: 1px solid var(--ws-border); background: var(--ws-surface); }
.ws-col-right { border-left:  1px solid var(--ws-border); background: var(--ws-surface); }
.ws-col-center{ background: var(--ws-bg); }

.ws-scroll {
  overflow-y: auto;
}

/* Status dot shared building block */
.ws-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.ws-dot--lg { width: 12px; height: 12px; }
.ws-dot--running { animation: history-pulse 1.8s ease-in-out infinite; }
.ws-dot--waiting {
  background: transparent;
  border: 2px solid currentColor;
}

/* Status color utility — applied to a wrapper that sets `color` */
.ws-clr-pending      { color: var(--ws-text-faint); }
.ws-clr-running      { color: var(--ws-status-running); }
.ws-clr-done         { color: var(--ws-status-done); }
.ws-clr-waiting      { color: var(--ws-status-waiting); }
.ws-clr-needs_input  { color: var(--ws-status-needs_input); }
.ws-clr-failed       { color: var(--ws-status-failed); }

.ws-clr-bg-pending      { background: var(--ws-text-faint); }
.ws-clr-bg-running      { background: var(--ws-status-running); }
.ws-clr-bg-done         { background: var(--ws-status-done); }
.ws-clr-bg-waiting      { background: var(--ws-status-waiting); }
.ws-clr-bg-needs_input  { background: var(--ws-status-needs_input); }
.ws-clr-bg-failed       { background: var(--ws-status-failed); }

/* Shared pill badge (smaller variant of HistoryCard) */
.ws-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
}
.ws-pill__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.ws-pill--running .ws-pill__dot { animation: history-pulse 1.8s ease-in-out infinite; }

.ws-section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ws-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ws-divider {
  height: 1px;
  background: var(--ws-border);
  margin: 16px 0;
}

.ws-muted { color: var(--ws-text-muted); }
.ws-faint { color: var(--ws-text-faint); }
.ws-mono  { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
```

- [ ] **Step 2: Commit**

No direct unit test for the CSS file itself — visual design tokens are validated by the component render tests that consume them and by manual inspection. Adding a `expect(true).toBe(true)` smoke test would be a test-hygiene defect.

```bash
git add frontend/src/components/workspace/workspace.css
git commit -m "feat(workspace): add workspace.css design tokens and grid shell"
```

---

## Task 5: `AgentAvatar` shared component

**Files:**
- Create: `frontend/src/components/workspace/AgentAvatar.tsx`
- Create: `frontend/src/components/workspace/AgentAvatar.test.tsx`

**Interfaces:**
- Consumes: `AgentSummary` from `workspace-types`, `STATUS_LABEL` from constants.
- Produces: `<AgentAvatar agent={summary} size="sm"|"lg" />`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/workspace/AgentAvatar.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentAvatar } from './AgentAvatar'
import type { AgentSummary } from '../../lib/workspace-types'

const mk = (over: Partial<AgentSummary>): AgentSummary => ({
  name: 'market_analyst',
  label: '市场分析师',
  role: 'analyst',
  status: 'pending',
  currentAction: '等待启动',
  progress: { done: 0, total: 3 },
  ...over,
})

describe('AgentAvatar', () => {
  it('renders the agent label and a status dot', () => {
    render(<AgentAvatar agent={mk({ label: '市场分析师', status: 'running' })} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()
    expect(document.querySelector('.ws-dot--running')).toBeTruthy()
  })

  it('uses the large dot when size=lg', () => {
    render(<AgentAvatar agent={mk({ status: 'running' })} size="lg" />)
    expect(document.querySelector('.ws-dot--lg')).toBeTruthy()
  })

  it('uses hollow ring when status=waiting', () => {
    render(<AgentAvatar agent={mk({ status: 'waiting' })} />)
    expect(document.querySelector('.ws-dot--waiting')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd frontend && npx vitest run src/components/workspace/AgentAvatar.test.tsx`
Expected: FAIL "Cannot find module './AgentAvatar'".

- [ ] **Step 3: Implement `AgentAvatar.tsx`**

```tsx
// frontend/src/components/workspace/AgentAvatar.tsx
import type { AgentSummary } from '../../lib/workspace-types'
import { STATUS_LABEL } from '../../lib/workspace-constants'

interface Props {
  agent: AgentSummary
  size?: 'sm' | 'lg'
  showLabel?: boolean
}

export function AgentAvatar({ agent, size = 'sm', showLabel = false }: Props) {
  const dotCls = [
    'ws-dot',
    size === 'lg' ? 'ws-dot--lg' : '',
    agent.status === 'running' ? 'ws-dot--running' : '',
    agent.status === 'waiting' ? 'ws-dot--waiting' : '',
  ].filter(Boolean).join(' ')

  return (
    <span className={`ws-clr-${agent.status}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span className={dotCls} aria-hidden="true" />
      <span style={{ fontSize: 13, fontWeight: 600 }}>{agent.label}</span>
      {showLabel && (
        <span className="ws-faint" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {agent.role === 'orchestrator' ? 'Orchestrator' : 'Analyst'}
        </span>
      )}
      <span className="ws-faint" style={{ fontSize: 11 }}>
        {STATUS_LABEL[agent.status]}
      </span>
    </span>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd frontend && npx vitest run src/components/workspace/AgentAvatar.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/AgentAvatar.tsx frontend/src/components/workspace/AgentAvatar.test.tsx
git commit -m "feat(workspace): add AgentAvatar shared component"
```

---

## Task 6: `WorkspaceTopbar`

**Files:**
- Create: `frontend/src/components/workspace/WorkspaceTopbar.tsx`
- Create: `frontend/src/components/workspace/WorkspaceTopbar.test.tsx`

**Interfaces:**
- Consumes: `WorkspaceState` from `workspace-types`, `RunInfo` from `lib/types`.
- Produces: `<WorkspaceTopbar state runInfo errorMsg onBack />`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/src/components/workspace/WorkspaceTopbar.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { WorkspaceTopbar } from './WorkspaceTopbar'
import type { WorkspaceState } from '../../lib/workspace-types'

const baseState: WorkspaceState = {
  rounds: [], agents: [],
  progress: { done: 4, total: 11, percent: 36 },
  status: 'running',
}

describe('WorkspaceTopbar', () => {
  it('renders startup_idea as the task name', () => {
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'AI Agent 创业', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={() => {}} />)
    expect(screen.getByText('AI Agent 创业')).toBeInTheDocument()
  })

  it('shows progress percent', () => {
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={() => {}} />)
    expect(screen.getByText(/36%/)).toBeInTheDocument()
  })

  it('disables pause and terminate buttons', () => {
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={() => {}} />)
    expect(screen.getByRole('button', { name: /暂停/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /终止/ })).toBeDisabled()
  })

  it('enables export only when report is present', () => {
    const { rerender } = render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" report={null} onBack={() => {}} />)
    expect(screen.getByRole('button', { name: /导出/ })).toBeDisabled()
    rerender(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'complete', created_at: null, completed_at: null }} errorMsg="" report={{ decision: 'Go' }} onBack={() => {}} />)
    expect(screen.getByRole('button', { name: /导出/ })).not.toBeDisabled()
  })

  it('clicking back calls onBack', () => {
    const onBack = vi.fn()
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={onBack} />)
    fireEvent.click(screen.getByRole('button', { name: /返回/ }))
    expect(onBack).toHaveBeenCalledOnce()
  })

  it('shows error message in failed state', () => {
    render(<WorkspaceTopbar state={{ ...baseState, status: 'failed' }} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'failed', created_at: null, completed_at: null }} errorMsg="网络中断" onBack={() => {}} />)
    expect(screen.getByText(/网络中断/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd frontend && npx vitest run src/components/workspace/WorkspaceTopbar.test.tsx`
Expected: FAIL "Cannot find module './WorkspaceTopbar'".

- [ ] **Step 3: Implement `WorkspaceTopbar.tsx`**

```tsx
// frontend/src/components/workspace/WorkspaceTopbar.tsx
import './workspace.css'
import type { WorkspaceState } from '../../lib/workspace-types'
import type { RunInfo } from '../../lib/types'

interface Props {
  state: WorkspaceState
  runInfo: RunInfo | null
  errorMsg: string
  report?: unknown
  onBack: () => void
}

const STATUS_PILL_LABEL: Record<WorkspaceState['status'], string> = {
  pending: '待启动',
  running: '进行中',
  done: '已完成',
  failed: '分析失败',
}

export function WorkspaceTopbar({ state, runInfo, errorMsg, report, onBack }: Props) {
  const percent = state.progress.percent
  const failed = state.status === 'failed'
  const barCls = failed ? 'ws-clr-bg-failed' : state.status === 'done' ? 'ws-clr-bg-done' : 'ws-clr-bg-running'

  function handleExport() {
    if (!report || !runInfo) return
    const payload = JSON.stringify({
      run_id: runInfo.run_id,
      startup_idea: runInfo.startup_idea,
      report,
    }, null, 2)
    const blob = new Blob([payload], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `市场进入策略分析-${runInfo.run_id.slice(0, 8)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const title = (runInfo?.startup_idea ?? '').length > 32
    ? (runInfo?.startup_idea ?? '').slice(0, 32) + '…'
    : (runInfo?.startup_idea ?? '')

  return (
    <header style={{
      display: 'flex', alignItems: 'center', gap: 12, height: 56,
      padding: '0 24px', background: 'var(--ws-surface)',
      borderBottom: '1px solid var(--ws-border)', flexShrink: 0,
    }}>
      <button
        onClick={onBack}
        style={{
          background: 'transparent', border: '1px solid var(--ws-border)',
          borderRadius: 6, padding: '6px 12px', cursor: 'pointer', fontSize: 13,
        }}
        aria-label="返回"
      >
        ← 返回
      </button>

      <div style={{ width: 1, height: 24, background: 'var(--ws-border)' }} />

      <h1 title={runInfo?.startup_idea} style={{
        fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--ws-text)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        maxWidth: 320,
      }}>
        {title}
      </h1>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{
          width: 180, height: 8, background: 'var(--ws-border)',
          borderRadius: 999, overflow: 'hidden',
        }}>
          <div className={barCls} style={{ width: `${percent}%`, height: '100%', transition: 'width 160ms ease, background 160ms ease' }} />
        </div>
        <span className="ws-mono ws-faint" style={{ fontSize: 12 }}>{percent}%</span>
      </div>

      <span className={`ws-pill ws-clr-${state.status}`} style={{ background: 'var(--ws-bg)' }}>
        <span className="ws-pill__dot" />
        {STATUS_PILL_LABEL[state.status]}
      </span>

      <div style={{ flex: 1 }} />

      <button disabled title="暂停功能即将支持" style={btnDisabled()}>⏸ 暂停</button>
      <button disabled title="终止功能即将支持" style={btnDisabled()}>⏹ 终止</button>
      <button
        onClick={handleExport}
        disabled={!report}
        title={!report ? '分析完成后可导出' : '导出 JSON'}
        style={report ? btnActive() : btnDisabled()}
        aria-label="导出"
      >
        ⤓ 导出
      </button>

      {failed && errorMsg && (
        <div style={{ position: 'absolute', top: 56, left: 0, right: 0, padding: '8px 24px', background: 'var(--ws-status-failed-bg)', color: 'var(--ws-status-failed)', fontSize: 12 }}>
          {errorMsg}
        </div>
      )}
    </header>
  )
}

function btnDisabled(): React.CSSProperties {
  return {
    background: 'transparent',
    border: '1px solid var(--ws-border)',
    borderRadius: 6,
    padding: '6px 12px',
    fontSize: 13,
    cursor: 'not-allowed',
    opacity: 0.45,
  }
}

function btnActive(): React.CSSProperties {
  return {
    background: 'var(--ws-surface)',
    border: '1px solid var(--ws-border-strong)',
    borderRadius: 6,
    padding: '6px 12px',
    fontSize: 13,
    cursor: 'pointer',
    color: 'var(--ws-text)',
  }
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd frontend && npx vitest run src/components/workspace/WorkspaceTopbar.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/WorkspaceTopbar.tsx frontend/src/components/workspace/WorkspaceTopbar.test.tsx
git commit -m "feat(workspace): add WorkspaceTopbar"
```

---

## Task 7: `AgentTeamSidebar`

**Files:**
- Create: `frontend/src/components/workspace/AgentTeamSidebar.tsx`
- Create: `frontend/src/components/workspace/AgentTeamSidebar.test.tsx`

**Interfaces:**
- Consumes: `AgentSummary[]`, `SelectedTarget` from `workspace-types`, `AGENT_ORDER` from constants.
- Produces: `<AgentTeamSidebar agents selected onSelect />`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/src/components/workspace/AgentTeamSidebar.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AgentTeamSidebar } from './AgentTeamSidebar'
import type { AgentSummary, SelectedTarget } from '../../lib/workspace-types'

const agents: AgentSummary[] = [
  { name: 'strategy_advisor', label: '战略顾问', role: 'orchestrator', status: 'running', currentAction: '正在综合 R3 战略', progress: { done: 0, total: 1 } },
  { name: 'market_analyst', label: '市场分析师', role: 'analyst', status: 'done', currentAction: '已完成', progress: { done: 2, total: 3 } },
  { name: 'competitor_researcher', label: '竞品调研员', role: 'analyst', status: 'running', currentAction: '正在搜索', progress: { done: 1, total: 3 } },
  { name: 'finance_analyst', label: '财务分析师', role: 'analyst', status: 'waiting', currentAction: '等待依赖', progress: { done: 0, total: 3 } },
  { name: 'risk_reviewer', label: '风险评审员', role: 'analyst', status: 'failed', currentAction: '执行失败', progress: { done: 0, total: 1 } },
]

describe('AgentTeamSidebar', () => {
  it('renders Orchestrator card first, above other agents', () => {
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    const items = screen.getAllByRole('button')
    expect(items[0]).toHaveTextContent('战略顾问')
    expect(items[0]).toHaveTextContent(/Orchestrator/i)
  })

  it('renders the other 4 agents in fixed order after Orchestrator', () => {
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    const items = screen.getAllByRole('button')
    const labels = items.map((b) => b.textContent)
    expect(labels.findIndex((l) => l?.includes('市场分析师'))).toBeLessThan(labels.findIndex((l) => l?.includes('竞品调研员')))
    expect(labels.findIndex((l) => l?.includes('竞品调研员'))).toBeLessThan(labels.findIndex((l) => l?.includes('财务分析师')))
    expect(labels.findIndex((l) => l?.includes('财务分析师'))).toBeLessThan(labels.findIndex((l) => l?.includes('风险评审员')))
  })

  it('clicking an agent fires onSelect with that agent name', () => {
    const onSelect = vi.fn()
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('市场分析师'))
    expect(onSelect).toHaveBeenCalledWith({ kind: 'agent', agent: 'market_analyst' })
  })

  it('applies running-pulse class to running agents', () => {
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    // Orchestrator is running, competitor_researcher is running
    const pulses = document.querySelectorAll('.ws-dot--running')
    expect(pulses.length).toBeGreaterThanOrEqual(2)
  })

  it('shows failed left-bar on failed agent', () => {
    const { container } = render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    expect(container.querySelector('.ws-agent-row--failed')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd frontend && npx vitest run src/components/workspace/AgentTeamSidebar.test.tsx`
Expected: FAIL "Cannot find module './AgentTeamSidebar'".

- [ ] **Step 3: Implement `AgentTeamSidebar.tsx`**

```tsx
// frontend/src/components/workspace/AgentTeamSidebar.tsx
import './workspace.css'
import { AGENT_ORDER } from '../../lib/workspace-constants'
import type { AgentName } from '../../lib/types'
import type { AgentSummary, SelectedTarget } from '../../lib/workspace-types'

interface Props {
  agents: AgentSummary[]
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
}

export function AgentTeamSidebar({ agents, selected, onSelect }: Props) {
  const orchestrator = agents.find((a) => a.role === 'orchestrator')
  const others = AGENT_ORDER
    .map((name) => agents.find((a) => a.name === name))
    .filter(Boolean) as AgentSummary[]

  return (
    <aside className="ws-col-left">
      <div className="ws-scroll" style={{ padding: '24px 0', flex: 1 }}>
        <div className="ws-section-label" style={{ padding: '0 16px 12px' }}>团队</div>

        {orchestrator && (
          <OrchestratorCard
            agent={orchestrator}
            selected={selected?.kind === 'agent' && selected.agent === orchestrator.name}
            onSelect={() => onSelect({ kind: 'agent', agent: orchestrator.name })}
          />
        )}

        <div className="ws-section-label" style={{ padding: '16px 16px 8px' }}>其他 Agent（{others.length}）</div>

        {others.map((a) => {
          const isSel = selected?.kind === 'agent' && selected.agent === a.name
          const isFailed = a.status === 'failed'
          return (
            <button
              key={a.name}
              type="button"
              onClick={() => onSelect({ kind: 'agent', agent: a.name as AgentName })}
              className={`ws-agent-row ${isSel ? 'ws-agent-row--selected' : ''} ${isFailed ? 'ws-agent-row--failed' : ''}`}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '10px 16px', background: isSel ? 'var(--ws-bg)' : 'transparent',
                border: 0, borderBottom: '1px solid transparent', cursor: 'pointer',
                borderLeft: `2px solid ${isSel ? 'var(--ws-status-running)' : isFailed ? 'var(--ws-status-failed)' : 'transparent'}`,
              }}
            >
              <AgentRowContent agent={a} />
            </button>
          )
        })}
      </div>
    </aside>
  )
}

function OrchestratorCard({ agent, selected, onSelect }: {
  agent: AgentSummary
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`ws-orchestrator-card ${selected ? 'ws-orchestrator-card--selected' : ''}`}
      style={{
        display: 'block', width: 'calc(100% - 32px)', margin: '0 16px 16px',
        padding: 12, textAlign: 'left',
        background: 'var(--ws-bg)',
        border: `1px solid ${selected ? 'var(--ws-status-running)' : 'var(--ws-border)'}`,
        borderRadius: 10, cursor: 'pointer',
        borderLeft: `2px solid ${selected ? 'var(--ws-status-running)' : 'transparent'}`,
      }}
    >
      <div className={`ws-clr-${agent.status}`} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`ws-dot ws-dot--lg ${agent.status === 'running' ? 'ws-dot--running' : ''}`} />
        <strong style={{ fontSize: 13, color: 'var(--ws-text)' }}>{agent.label}</strong>
      </div>
      <div className="ws-faint" style={{ fontSize: 10, letterSpacing: '0.05em', textTransform: 'uppercase', marginTop: 4 }}>
        Orchestrator
      </div>
      <div className="ws-muted" style={{ fontSize: 12, marginTop: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {agent.currentAction}
      </div>
    </button>
  )
}

function AgentRowContent({ agent }: { agent: AgentSummary }) {
  return (
    <>
      <div className={`ws-clr-${agent.status}`} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`ws-dot ${agent.status === 'running' ? 'ws-dot--running' : ''} ${agent.status === 'waiting' ? 'ws-dot--waiting' : ''}`} />
        <strong style={{ fontSize: 13, color: 'var(--ws-text)' }}>{agent.label}</strong>
      </div>
      <div className="ws-muted" style={{ fontSize: 12, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {agent.currentAction}
      </div>
      <div className="ws-faint" style={{ fontSize: 12 }}>
        {agent.progress.done}/{agent.progress.total} 任务
      </div>
    </>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd frontend && npx vitest run src/components/workspace/AgentTeamSidebar.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/AgentTeamSidebar.tsx frontend/src/components/workspace/AgentTeamSidebar.test.tsx
git commit -m "feat(workspace): add AgentTeamSidebar"
```

---

## Task 8: `TimelineTaskItem`

**Files:**
- Create: `frontend/src/components/workspace/TimelineTaskItem.tsx`
- Create: `frontend/src/components/workspace/TimelineTaskItem.test.tsx`

**Interfaces:**
- Consumes: `AgentTask`, `Round` from `workspace-types`, `SelectedTarget`.
- Produces: `<TimelineTaskItem task round selected onSelect />`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/src/components/workspace/TimelineTaskItem.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TimelineTaskItem } from './TimelineTaskItem'
import type { AgentTask, SelectedTarget } from '../../lib/workspace-types'

function task(over: Partial<AgentTask>): AgentTask {
  return {
    id: 'r1:market_analyst:',
    agent: 'market_analyst',
    round: 'r1',
    status: 'running',
    startedAt: 1,
    endedAt: null,
    events: [],
    ...over,
  }
}

describe('TimelineTaskItem', () => {
  it('renders agent label, sub-round tag and status', () => {
    render(<TimelineTaskItem task={task({ subRound: 'B', status: 'done' })} roundId="r2" selected={null} onSelect={() => {}} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()
    expect(screen.getByText(/R2-B/)).toBeInTheDocument()
  })

  it('shows expand button when task has output_summary', () => {
    render(<TimelineTaskItem task={task({ status: 'done', output_summary: { x: 1 } })} roundId="r1" selected={null} onSelect={() => {}} />)
    expect(screen.getByText(/展开产物/)).toBeInTheDocument()
  })

  it('does not show expand button when task has no output and no tool events', () => {
    render(<TimelineTaskItem task={task({ status: 'running' })} roundId="r1" selected={null} onSelect={() => {}} />)
    expect(screen.queryByText(/展开产物/)).not.toBeInTheDocument()
  })

  it('clicking expand toggles the artifact section', () => {
    render(<TimelineTaskItem task={task({ status: 'done', output_summary: { x: 1 } })} roundId="r1" selected={null} onSelect={() => {}} />)
    fireEvent.click(screen.getByText(/展开产物/))
    expect(screen.getByText(/时间线/)).toBeInTheDocument()
  })

  it('renders failed error text when status is failed', () => {
    render(<TimelineTaskItem task={task({ status: 'failed', error: 'timeout' })} roundId="r1" selected={null} onSelect={() => {}} />)
    expect(screen.getByText(/timeout/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd frontend && npx vitest run src/components/workspace/TimelineTaskItem.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/workspace/TimelineTaskItem.tsx
import './workspace.css'
import { useState } from 'react'
import { AGENT_LABELS } from '../../lib/workspace-constants'
import { STATUS_LABEL } from '../../lib/workspace-constants'
import type { AgentTask, RoundId, SelectedTarget, TaskEventKind } from '../../lib/workspace-types'
import { ArtifactPreview } from './artifact-renderers'

interface Props {
  task: AgentTask
  roundId: RoundId
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
}

export function TimelineTaskItem({ task, selected, onSelect }: Props) {
  const [expanded, setExpanded] = useState(false)
  const hasExpandable = task.output_summary != null || task.events.some((e) => e.kind === 'tool')

  const subRoundTag = task.subRound ? `R2-${task.subRound}` : `R${task.round.slice(1)}`
  const borderColor =
    task.status === 'running' ? 'var(--ws-status-running)'
    : task.status === 'done' ? 'var(--ws-status-done)'
    : task.status === 'failed' ? 'var(--ws-status-failed)'
    : task.status === 'waiting' ? 'var(--ws-status-waiting)'
    : 'transparent'

  return (
    <div className={`ws-task-item ${task.status === 'running' ? 'ws-task-item--running' : ''}`} style={{
      position: 'relative', padding: '12px 16px', borderBottom: '1px solid var(--ws-border)',
    }}>
      <span style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 2,
        background: borderColor,
      }} className={task.status === 'running' ? 'ws-bar--running' : ''} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`ws-dot ws-clr-${task.status} ${task.status === 'running' ? 'ws-dot--running' : ''} ${task.status === 'waiting' ? 'ws-dot--waiting' : ''}`} />
        <strong style={{ fontSize: 13 }}>{AGENT_LABELS[task.agent]}</strong>
        <span className="ws-faint" style={{ fontSize: 11 }}>{subRoundTag}</span>
        <div style={{ flex: 1 }} />
        <span className={`ws-pill ws-clr-${task.status}`} style={{ background: 'var(--ws-bg)' }}>
          <span className="ws-pill__dot" />
          {STATUS_LABEL[task.status]}
        </span>
      </div>

      <CurrentActionLine task={task} />

      {task.status === 'failed' && task.error && (
        <div className="ws-clr-failed" style={{ fontSize: 12, marginTop: 4 }}>{task.error}</div>
      )}

      <MetaLine task={task} onSelect={onSelect} />

      {hasExpandable && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="ws-faint"
          style={{ background: 'none', border: 0, padding: '4px 0', cursor: 'pointer', fontSize: 12 }}
        >
          {expanded ? '▾ 收起产物' : '▸ 展开产物'}
        </button>
      )}

      {expanded && hasExpandable && (
        <ExpandedSection task={task} onSelect={onSelect} />
      )}
    </div>
  )
}

function CurrentActionLine({ task }: { task: AgentTask }) {
  const text = describeAction(task)
  return (
    <div className="ws-muted" style={{ fontSize: 13, marginTop: 4 }}>
      {text}
    </div>
  )
}

function describeAction(task: AgentTask): string {
  if (task.status === 'failed') return '执行失败'
  if (task.status === 'done') return '已提交产物'
  if (task.status === 'pending') return '等待启动'
  if (task.status === 'waiting') return '等待前置任务完成'
  const last = task.events[task.events.length - 1]
  if (!last) return '开始分析'
  if (last.kind === 'tool' && last.payload.type === 'tool.start') {
    return `正在搜索：${String(last.payload.input_preview ?? '').slice(0, 40)}`
  }
  if (last.kind === 'tool' && last.payload.type === 'tool.end') {
    const ev = last.payload.evidence_id
    return ev ? `搜索完成 → ${ev}` : '搜索完成'
  }
  if (last.kind === 'challenge_issued') {
    return `向 ${AGENT_LABELS[last.payload.target as keyof typeof AGENT_LABELS] ?? last.payload.target} 发起挑战`
  }
  if (last.kind === 'challenge_responded') {
    return `回应挑战：${String(last.payload.response ?? '').slice(0, 40)}`
  }
  if (last.kind === 'message') {
    return String(last.payload.content_summary ?? '').slice(0, 60)
  }
  return '执行中'
}

function MetaLine({ task, onSelect }: { task: AgentTask; onSelect: (t: SelectedTarget) => void }) {
  const tools = task.events.filter((e) => e.kind === 'tool').length
  const challenges = task.events.filter((e) => e.kind === 'challenge_issued' || e.kind === 'challenge_responded').length
  return (
    <div className="ws-faint" style={{ fontSize: 12, marginTop: 4 }}>
      {tools} 条工具调用
      {challenges > 0 && <> · {challenges} 条挑战</>}
    </div>
  )
}

function ExpandedSection({ task, onSelect }: { task: AgentTask; onSelect: (t: SelectedTarget) => void }) {
  return (
    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--ws-border)' }}>
      <div className="ws-section-label" style={{ marginBottom: 8 }}>时间线</div>
      {task.events.map((ev) => (
        <EventRow key={ev.id} ev={ev} taskId={task.id} onSelect={onSelect} />
      ))}

      {task.output_summary != null && (
        <>
          <div className="ws-section-label" style={{ marginTop: 16, marginBottom: 8 }}>产物预览</div>
          <ArtifactPreview agent={task.agent} output={task.output_summary} />
          <CopyJsonButton data={task.output_summary} />
        </>
      )}
    </div>
  )
}

function EventRow({ ev, taskId, onSelect }: {
  ev: AgentTask['events'][number]
  taskId: string
  onSelect: (t: SelectedTarget) => void
}) {
  const time = formatTime(ev.timestamp)
  const text = eventRowText(ev.kind, ev.payload)
  const isTool = ev.kind === 'tool'
  return (
    <div style={{ display: 'flex', gap: 12, padding: '4px 0', fontSize: 12 }}>
      <span className="ws-mono ws-faint" style={{ flexShrink: 0, width: 48 }}>{time}</span>
      <button
        type="button"
        disabled={!isTool}
        onClick={() => isTool && onSelect({ kind: 'event', taskId, eventId: ev.id })}
        style={{
          background: 'none', border: 0, padding: 0, cursor: isTool ? 'pointer' : 'default',
          color: isTool ? 'var(--ws-text)' : 'var(--ws-text-muted)', textAlign: 'left', fontSize: 12,
        }}
      >
        {text}
      </button>
    </div>
  )
}

function eventRowText(kind: TaskEventKind, payload: Record<string, unknown>): string {
  switch (kind) {
    case 'start': return '开始分析'
    case 'tool': {
      if (payload.type === 'tool.start') {
        return `搜索：${String(payload.input_preview ?? '').slice(0, 40)}`
      }
      const ev = payload.evidence_id
      return `搜索完成 → ${ev ?? '无证据'}`
    }
    case 'message': return String(payload.content_summary ?? '').slice(0, 60)
    case 'challenge_issued':
      return `向 ${payload.target as string} 发起挑战：${String(payload.claim ?? '').slice(0, 40)}`
    case 'challenge_responded':
      return `回应 ${payload.issuer as string}：${String(payload.response ?? '').slice(0, 40)} [${payload.verdict as string}]`
    case 'end':
      return payload.error ? `失败：${payload.error}` : '提交产物'
  }
}

function formatTime(ts: number): string {
  // ts is a monotonic counter, not a real timestamp. Render as relative index.
  // For real wall-clock display we'd need actual event timestamps; out of scope.
  const minutes = Math.floor(ts / 60)
  const seconds = ts % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function CopyJsonButton({ data }: { data: unknown }) {
  return (
    <button
      type="button"
      onClick={() => navigator.clipboard?.writeText(JSON.stringify(data, null, 2))}
      className="ws-faint"
      style={{ marginTop: 8, background: 'none', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 12 }}
    >
      复制 JSON
    </button>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd frontend && npx vitest run src/components/workspace/TimelineTaskItem.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/TimelineTaskItem.tsx frontend/src/components/workspace/TimelineTaskItem.test.tsx
git commit -m "feat(workspace): add TimelineTaskItem"
```

---

## Task 9: `CollaborationTimeline`

**Files:**
- Create: `frontend/src/components/workspace/CollaborationTimeline.tsx`
- Create: `frontend/src/components/workspace/CollaborationTimeline.test.tsx`

**Interfaces:**
- Consumes: `WorkspaceState.rounds`, `SelectedTarget`.
- Produces: `<CollaborationTimeline rounds selected onSelect />`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/src/components/workspace/CollaborationTimeline.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CollaborationTimeline } from './CollaborationTimeline'
import type { Round, SelectedTarget } from '../../lib/workspace-types'

const rounds: Round[] = [
  {
    id: 'r1', title: '第一轮', subtitle: '', status: 'done',
    transitionedAt: 1,
    tasks: [{
      id: 'r1:market_analyst:', agent: 'market_analyst', round: 'r1', status: 'done',
      startedAt: 1, endedAt: 2, events: [],
      output_summary: { tam: 100 },
    }],
  },
  { id: 'r2', title: '第二轮', subtitle: '', status: 'running', transitionedAt: 3, tasks: [] },
  { id: 'r3', title: '第三轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
]

describe('CollaborationTimeline', () => {
  it('renders three round headers', () => {
    render(<CollaborationTimeline rounds={rounds} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('第一轮')).toBeInTheDocument()
    expect(screen.getByText('第二轮')).toBeInTheDocument()
    expect(screen.getByText('第三轮')).toBeInTheDocument()
  })

  it('expands done and running rounds by default; collapses pending', () => {
    render(<CollaborationTimeline rounds={rounds} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()       // r1 expanded
    expect(screen.queryByText('战略顾问')).not.toBeInTheDocument()   // r3 collapsed (no tasks rendered)
  })

  it('forces failed round expanded and disables collapse', () => {
    const failed: Round[] = [{ ...rounds[0], status: 'failed' }]
    render(<CollaborationTimeline rounds={failed} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()
  })

  it('renders R2 task twice (A and B sub-rounds) for same agent', () => {
    const r2Rounds: Round[] = [{
      id: 'r2', title: '第二轮', subtitle: '', status: 'running', transitionedAt: 1,
      tasks: [
        { id: 'r2:market_analyst:A', agent: 'market_analyst', round: 'r2', subRound: 'A', status: 'done', startedAt: 1, endedAt: 2, events: [] },
        { id: 'r2:market_analyst:B', agent: 'market_analyst', round: 'r2', subRound: 'B', status: 'running', startedAt: 3, endedAt: null, events: [] },
      ],
    }]
    render(<CollaborationTimeline rounds={r2Rounds} selected={null} onSelect={() => {}} />)
    expect(screen.getAllByText('市场分析师')).toHaveLength(2)
    expect(screen.getByText('R2-A')).toBeInTheDocument()
    expect(screen.getByText('R2-B')).toBeInTheDocument()
  })

  it('renders empty state when all rounds are empty', () => {
    const empty: Round[] = [
      { id: 'r1', title: '第一轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
      { id: 'r2', title: '第二轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
      { id: 'r3', title: '第三轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
    ]
    render(<CollaborationTimeline rounds={empty} selected={null} onSelect={() => {}} />)
    expect(screen.getByText(/战略顾问正在拆解任务/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd frontend && npx vitest run src/components/workspace/CollaborationTimeline.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/workspace/CollaborationTimeline.tsx
import './workspace.css'
import { useEffect, useRef, useState } from 'react'
import type { Round, SelectedTarget } from '../../lib/workspace-types'
import { TimelineTaskItem } from './TimelineTaskItem'
import { EvidenceReport } from '../EvidenceReport'

interface Props {
  rounds: Round[]
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
  report?: unknown
}

const STATUS_LABEL: Record<Round['status'], string> = {
  pending: '待启动',
  running: '进行中',
  done: '已完成',
  failed: '失败',
}

export function CollaborationTimeline({ rounds, selected, onSelect, report }: Props) {
  const allEmpty = rounds.every((r) => r.tasks.length === 0)

  if (allEmpty) {
    return (
      <main className="ws-col-center">
        <div className="ws-scroll" style={{ padding: '48px 32px', maxWidth: 920, margin: '0 auto', width: '100%' }}>
          <div className="ws-muted" style={{ fontSize: 17, textAlign: 'center' }}>
            战略顾问正在拆解任务，即将分配给其他 Agent…
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="ws-col-center">
      <div className="ws-scroll" style={{ padding: '24px 32px 48px', maxWidth: 920, margin: '0 auto', width: '100%' }}>
        {rounds.map((r) => (
          <RoundBlock key={r.id} round={r} selected={selected} onSelect={onSelect} report={report} />
        ))}
      </div>
    </main>
  )
}

function RoundBlock({ round, selected, onSelect, report }: {
  round: Round
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
  report?: unknown
}) {
  const defaultOpen = round.status === 'running' || round.status === 'done' || round.status === 'failed'
  const [open, setOpen] = useState(defaultOpen)
  const lastStatusRef = useRef(round.status)
  useEffect(() => {
    if (round.status !== lastStatusRef.current) {
      lastStatusRef.current = round.status
      setOpen(round.status === 'running' || round.status === 'done' || round.status === 'failed')
    }
  }, [round.status])

  const canCollapse = round.status !== 'failed'

  return (
    <section style={{ marginBottom: 24 }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0' }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>{round.title}</h2>
        <span className={`ws-pill ws-clr-${round.status}`} style={{ background: 'var(--ws-bg)' }}>
          <span className="ws-pill__dot" />
          {STATUS_LABEL[round.status]}
        </span>
        <div style={{ flex: 1 }} />
        {canCollapse && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="ws-faint"
            style={{ background: 'none', border: 0, cursor: 'pointer', fontSize: 14 }}
            aria-label={open ? '折叠' : '展开'}
          >
            {open ? '▾' : '▸'}
          </button>
        )}
      </header>

      {round.subtitle && <p className="ws-muted" style={{ fontSize: 12, margin: '0 0 8px' }}>{round.subtitle}</p>}

      {open && (
        <div style={{ border: '1px solid var(--ws-border)', borderRadius: 10, background: 'var(--ws-surface)', overflow: 'hidden' }}>
          {round.tasks.map((t) => (
            <TimelineTaskItem
              key={t.id}
              task={t}
              roundId={round.id}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
          {round.id === 'r3' && round.tasks.some((t) => t.agent === 'strategy_advisor' && t.status === 'done') && report && (
            <div style={{ padding: 16, borderTop: '1px solid var(--ws-border)' }}>
              <EvidenceReport report={report} />
            </div>
          )}
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd frontend && npx vitest run src/components/workspace/CollaborationTimeline.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/CollaborationTimeline.tsx frontend/src/components/workspace/CollaborationTimeline.test.tsx
git commit -m "feat(workspace): add CollaborationTimeline"
```

---

## Task 10: `DetailInspector` + `artifact-renderers`

**Files:**
- Create: `frontend/src/components/workspace/DetailInspector.tsx`
- Create: `frontend/src/components/workspace/DetailInspector.test.tsx`
- Create: `frontend/src/components/workspace/artifact-renderers.tsx`

**Interfaces:**
- Consumes: `WorkspaceState`, `SelectedTarget`.
- Produces: `<DetailInspector state selected onSelect report />`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/src/components/workspace/DetailInspector.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DetailInspector } from './DetailInspector'
import type { WorkspaceState, SelectedTarget } from '../../lib/workspace-types'

function stateOver(over: Partial<WorkspaceState>): WorkspaceState {
  return {
    rounds: [{
      id: 'r1', title: '第一轮', subtitle: '', status: 'done', transitionedAt: 1,
      tasks: [{
        id: 'r1:market_analyst:', agent: 'market_analyst', round: 'r1', status: 'done',
        startedAt: 1, endedAt: 2, events: [
          { id: 'r1:market_analyst:0', kind: 'start', timestamp: 1, agent: 'market_analyst', round: 'r1', payload: { type: 'agent.start' } },
          { id: 'r1:market_analyst:1', kind: 'tool', timestamp: 2, agent: 'market_analyst', round: 'r1', payload: { type: 'tool.start', tool: 'search', input_preview: 'AI Agent 市场' } },
          { id: 'r1:market_analyst:2', kind: 'tool', timestamp: 3, agent: 'market_analyst', round: 'r1', payload: { type: 'tool.end', tool: 'search', evidence_id: 'ev-3a2f', output_preview: '...' } },
          { id: 'r1:market_analyst:3', kind: 'end', timestamp: 4, agent: 'market_analyst', round: 'r1', payload: { type: 'agent.end', output_summary: { tam: 100, sam: 50, som: 10 } } },
        ],
        output_summary: { tam: 100, sam: 50, som: 10 },
      }],
    }, { id: 'r2', title: '第二轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
       { id: 'r3', title: '第三轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] }],
    agents: [],
    progress: { done: 1, total: 11, percent: 9 },
    status: 'running',
    ...over,
  }
}

describe('DetailInspector', () => {
  it('defaults to Orchestrator agent panel when selection is null', () => {
    render(<DetailInspector state={stateOver({})} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('战略顾问')).toBeInTheDocument()
    expect(screen.getByText(/Orchestrator/i)).toBeInTheDocument()
  })

  it('renders event panel when an event is selected', () => {
    const selected: SelectedTarget = { kind: 'event', taskId: 'r1:market_analyst:', eventId: 'r1:market_analyst:2' }
    render(<DetailInspector state={stateOver({})} selected={selected} onSelect={() => {}} />)
    expect(screen.getByText(/工具调用/)).toBeInTheDocument()
    expect(screen.getByText('search')).toBeInTheDocument()
    expect(screen.getByText(/ev-3a2f/)).toBeInTheDocument()
  })

  it('renders artifact panel with market analyst renderer', () => {
    const selected: SelectedTarget = { kind: 'artifact', taskId: 'r1:market_analyst:' }
    render(<DetailInspector state={stateOver({})} selected={selected} onSelect={() => {}} />)
    expect(screen.getByText(/TAM/)).toBeInTheDocument()
    expect(screen.getByText(/100/)).toBeInTheDocument()
  })

  it('shows JSON fallback when output_summary has unknown shape', () => {
    const state = stateOver({})
    state.rounds[0].tasks[0].agent = 'risk_reviewer'
    state.rounds[0].tasks[0].output_summary = { weird: 'data' }
    const selected: SelectedTarget = { kind: 'artifact', taskId: 'r1:market_analyst:' }
    const { container } = render(<DetailInspector state={state} selected={selected} onSelect={() => {}} />)
    expect(container.textContent).toMatch(/weird/)
  })

  it('shows disabled send-instruction button in agent panel', () => {
    render(<DetailInspector state={stateOver({})} selected={{ kind: 'agent', agent: 'strategy_advisor' }} onSelect={() => {}} />)
    const btn = screen.getByRole('button', { name: /发送/ })
    expect(btn).toBeDisabled()
  })
})
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd frontend && npx vitest run src/components/workspace/DetailInspector.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Create `artifact-renderers.tsx`**

```tsx
// frontend/src/components/workspace/artifact-renderers.tsx
import { useState } from 'react'
import type { AgentName } from '../../lib/types'

interface Props {
  agent: AgentName
  output: unknown
}

export function ArtifactPreview({ agent, output }: Props) {
  if (!output || typeof output !== 'object') {
    return <pre className="ws-mono" style={{ fontSize: 12 }}>{String(output ?? '')}</pre>
  }
  const obj = output as Record<string, unknown>
  switch (agent) {
    case 'market_analyst':    return <MarketRenderer data={obj} />
    case 'competitor_researcher': return <CompetitorRenderer data={obj} />
    case 'finance_analyst':   return <FinanceRenderer data={obj} />
    case 'risk_reviewer':     return <RiskRenderer data={obj} />
    case 'strategy_advisor':  return <StrategyRenderer data={obj} />
    default:                  return <JsonFallback data={obj} />
  }
}

function Field({ label, value }: { label: string; value: unknown }) {
  if (value == null || value === '') return null
  return (
    <div style={{ display: 'flex', gap: 12, padding: '4px 0', fontSize: 13 }}>
      <span className="ws-faint" style={{ width: 96, flexShrink: 0 }}>{label}</span>
      <span>{String(value)}</span>
    </div>
  )
}

function MarketRenderer({ data }: { data: Record<string, unknown> }) {
  return (
    <div>
      <Field label="TAM" value={data.tam} />
      <Field label="SAM" value={data.sam} />
      <Field label="SOM" value={data.som} />
      <Field label="增长率" value={data.growth_rate} />
      {Array.isArray(data.user_personas) && (
        <>
          <div className="ws-section-label" style={{ marginTop: 12, marginBottom: 4 }}>用户画像</div>
          <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13 }}>
            {(data.user_personas as unknown[]).map((p, i) => <li key={i}>{String(p)}</li>)}
          </ul>
        </>
      )}
      <ExtraFields data={data} knownKeys={['tam', 'sam', 'som', 'growth_rate', 'user_personas']} />
    </div>
  )
}

function CompetitorRenderer({ data }: { data: Record<string, unknown> }) {
  const competitors = Array.isArray(data.competitors) ? data.competitors as Record<string, unknown>[] : []
  return (
    <div>
      {competitors.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {['名称', '差异化', '威胁等级'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--ws-border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {competitors.map((c, i) => (
              <tr key={i}>
                <td style={{ padding: '6px 8px' }}>{String(c.name ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(c.differentiator ?? c.differentiation ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(c.threat_level ?? c.threat ?? '')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <div className="ws-muted">无竞品数据</div>}
      <ExtraFields data={data} knownKeys={['competitors']} />
    </div>
  )
}

function FinanceRenderer({ data }: { data: Record<string, unknown> }) {
  return (
    <div>
      <Field label="LTV" value={data.ltv} />
      <Field label="CAC" value={data.cac} />
      <Field label="毛利率" value={data.gross_margin} />
      <Field label="定价策略" value={data.pricing_strategy} />
      <Field label="资金需求" value={data.funding_required} />
      <ExtraFields data={data} knownKeys={['ltv', 'cac', 'gross_margin', 'pricing_strategy', 'funding_required']} />
    </div>
  )
}

function RiskRenderer({ data }: { data: Record<string, unknown> }) {
  const risks = Array.isArray(data.risks) ? data.risks as Record<string, unknown>[] : []
  return (
    <div>
      {risks.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {['维度', '严重程度', '缓解措施'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--ws-border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {risks.map((r, i) => (
              <tr key={i}>
                <td style={{ padding: '6px 8px' }}>{String(r.dimension ?? r.category ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(r.severity ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(r.mitigation ?? '')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <div className="ws-muted">无风险数据</div>}
      <ExtraFields data={data} knownKeys={['risks']} />
    </div>
  )
}

function StrategyRenderer({ data }: { data: Record<string, unknown> }) {
  // strategy_advisor uses EvidenceReport via the timeline; this renderer
  // is only hit when viewed as artifact from the inspector.
  return <JsonFallback data={data} />
}

function ExtraFields({ data, knownKeys }: { data: Record<string, unknown>; knownKeys: string[] }) {
  const extras = Object.keys(data).filter((k) => !knownKeys.includes(k))
  if (extras.length === 0) return null
  return (
    <>
      <div className="ws-section-label" style={{ marginTop: 12, marginBottom: 4 }}>其他字段</div>
      <dl style={{ fontSize: 12, margin: 0 }}>
        {extras.map((k) => (
          <div key={k} style={{ display: 'flex', gap: 12, padding: '2px 0' }}>
            <dt className="ws-faint" style={{ width: 120 }}>{k}</dt>
            <dd style={{ margin: 0 }}>{String(data[k])}</dd>
          </div>
        ))}
      </dl>
    </>
  )
}

function JsonFallback({ data }: { data: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="ws-faint"
        style={{ background: 'none', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 12 }}
      >
        {open ? '▾ 原始 JSON' : '▸ 原始 JSON'}
      </button>
      {open && (
        <pre className="ws-mono" style={{ fontSize: 11, background: 'var(--ws-bg)', padding: 8, borderRadius: 6, marginTop: 8, whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Implement `DetailInspector.tsx`**

```tsx
// frontend/src/components/workspace/DetailInspector.tsx
import './workspace.css'
import { useEffect, useState } from 'react'
import { AGENT_LABELS, STATUS_LABEL } from '../../lib/workspace-constants'
import type { WorkspaceState, SelectedTarget, AgentTask, AgentTaskEvent } from '../../lib/workspace-types'
import { EvidenceReport } from '../EvidenceReport'
import { ArtifactPreview } from './artifact-renderers'

interface Props {
  state: WorkspaceState
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
  report?: unknown
}

export function DetailInspector({ state, selected, onSelect, report }: Props) {
  const target = selected ?? { kind: 'agent' as const, agent: 'strategy_advisor' as const }

  return (
    <aside className="ws-col-right">
      <div className="ws-scroll" style={{ padding: '20px 24px' }}>
        {target.kind === 'agent' && <AgentPanel name={target.agent} state={state} />}
        {target.kind === 'event' && (
          <EventPanel state={state} taskId={target.taskId} eventId={target.eventId} onSelect={onSelect} />
        )}
        {target.kind === 'artifact' && (
          <ArtifactPanel state={state} taskId={target.taskId} report={report} onSelect={onSelect} />
        )}
      </div>
    </aside>
  )
}

function AgentPanel({ name, state }: { name: AgentName; state: WorkspaceState }) {
  const summary = state.agents.find((a) => a.name === name)
  const tasksForAgent: AgentTask[] = []
  for (const r of state.rounds) for (const t of r.tasks) if (t.agent === name) tasksForAgent.push(t)
  if (!summary) return <div className="ws-muted">无 Agent 信息</div>

  return (
    <div>
      <div className={`ws-clr-${summary.status}`} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`ws-dot ws-dot--lg ${summary.status === 'running' ? 'ws-dot--running' : ''} ${summary.status === 'waiting' ? 'ws-dot--waiting' : ''}`} />
        <strong style={{ fontSize: 14 }}>{summary.label}</strong>
      </div>
      <div className="ws-faint" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>
        {summary.role === 'orchestrator' ? 'Orchestrator' : 'Analyst'}
      </div>

      <Section label="状态">
        <span className={`ws-clr-${summary.status}`}>{STATUS_LABEL[summary.status]}</span>
      </Section>

      <Section label="当前动作">
        <span className="ws-muted">{summary.currentAction}</span>
      </Section>

      {tasksForAgent.length > 0 && (
        <Section label="跨轮任务">
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12 }}>
            {tasksForAgent.map((t) => (
              <li key={t.id} className={`ws-clr-${t.status}`}>
                {t.subRound ? `R2-${t.subRound}` : `R${t.round.slice(1)}`} · {STATUS_LABEL[t.status]}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="ws-divider" />

      <Section label="补充指令">
        <textarea
          placeholder="给该 Agent 追加一段提示…"
          style={{ width: '100%', minHeight: 64, padding: 8, border: '1px solid var(--ws-border)', borderRadius: 6, fontSize: 12, resize: 'vertical' }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
          <button
            type="button"
            disabled
            title="运行中追加指令将在下一版支持"
            style={{ background: 'transparent', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '4px 12px', fontSize: 12, cursor: 'not-allowed', opacity: 0.45 }}
          >
            发送
          </button>
        </div>
        <p className="ws-faint" style={{ fontSize: 11, marginTop: 8 }}>
          本期版本不支持运行中追加指令，将在下一版接入。
        </p>
      </Section>
    </div>
  )
}

function EventPanel({ state, taskId, eventId, onSelect }: {
  state: WorkspaceState
  taskId: string
  eventId: string
  onSelect: (t: SelectedTarget) => void
}) {
  const task = findTask(state, taskId)
  const ev = task?.events.find((e) => e.id === eventId)
  if (!task || !ev) return <div className="ws-muted">事件不存在</div>

  const payload = ev.payload as any
  const agentLabel = AGENT_LABELS[ev.agent]
  const evidenceId = payload.evidence_id as string | undefined

  const [evidence, setEvidence] = useState<any>(null)
  useEffect(() => {
    if (!evidenceId) return
    let cancelled = false
    fetch(`/evidence/${evidenceId}`).then((r) => r.json()).then((d) => {
      if (!cancelled) setEvidence(d)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [evidenceId])

  return (
    <div>
      <button
        type="button"
        onClick={() => onSelect({ kind: 'agent', agent: ev.agent })}
        className="ws-faint"
        style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', fontSize: 12, marginBottom: 12 }}
      >
        ← 返回 {agentLabel} 详情
      </button>

      <Section label="事件类型">
        <span className="ws-muted">{ev.kind === 'tool' ? '工具调用' : ev.kind === 'challenge_issued' ? '发起挑战' : ev.kind === 'challenge_responded' ? '回应挑战' : ev.kind === 'message' ? '中间思考' : ev.kind === 'start' ? '任务开始' : '任务结束'}</span>
      </Section>

      <Section label="Agent / 时间">
        <span className="ws-muted">{agentLabel}</span>
      </Section>

      {ev.kind === 'tool' && (
        <>
          <Section label="工具">
            <code className="ws-mono">{String(payload.tool ?? '')}</code>
          </Section>
          <Section label="输入预览">
            <pre className="ws-mono ws-muted" style={{ fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}>{String(payload.input_preview ?? '')}</pre>
          </Section>
          {payload.type === 'tool.end' && (
            <Section label="输出预览">
              <pre className="ws-mono ws-muted" style={{ fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}>{String(payload.output_preview ?? '')}</pre>
            </Section>
          )}
          {evidenceId && (
            <Section label="引用证据">
              {evidence ? (
                <div style={{ background: 'var(--ws-bg)', padding: 8, borderRadius: 6 }}>
                  <div style={{ fontSize: 12, fontWeight: 600 }}>{evidence.title ?? evidenceId}</div>
                  {evidence.url && <a href={evidence.url} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>{evidence.url}</a>}
                  <pre className="ws-muted ws-mono" style={{ fontSize: 11, marginTop: 6, whiteSpace: 'pre-wrap' }}>{String(evidence.content_excerpt ?? '').slice(0, 400)}</pre>
                </div>
              ) : <span className="ws-faint">加载中…</span>}
            </Section>
          )}
        </>
      )}

      <Section label="所属任务">
        <button
          type="button"
          onClick={() => onSelect({ kind: 'artifact', taskId: task.id })}
          className="ws-clr-running"
          style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', fontSize: 12 }}
        >
          {agentLabel} · R{task.round.slice(1)}{task.subRound ? `-${task.subRound}` : ''} →
        </button>
      </Section>
    </div>
  )
}

function ArtifactPanel({ state, taskId, report, onSelect }: {
  state: WorkspaceState
  taskId: string
  report?: unknown
  onSelect: (t: SelectedTarget) => void
}) {
  const task = findTask(state, taskId)
  if (!task) return <div className="ws-muted">任务不存在</div>

  const isR3Strategy = task.agent === 'strategy_advisor' && task.round === 'r3'
  return (
    <div>
      <Section label="任务产物">
        <strong style={{ fontSize: 13 }}>{AGENT_LABELS[task.agent]}</strong>
        <span className="ws-faint" style={{ marginLeft: 8, fontSize: 11 }}>
          R{task.round.slice(1)}{task.subRound ? `-${task.subRound}` : ''}
        </span>
      </Section>

      {isR3Strategy && report ? (
        <EvidenceReport report={report} />
      ) : (
        <ArtifactPreview agent={task.agent} output={task.output_summary} />
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button
          type="button"
          onClick={() => navigator.clipboard?.writeText(JSON.stringify(task.output_summary, null, 2))}
          style={{ flex: 1, background: 'transparent', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '6px', fontSize: 12, cursor: 'pointer' }}
        >
          复制 JSON
        </button>
        <button
          type="button"
          disabled
          title="重试任务将在下一版支持"
          style={{ flex: 1, background: 'transparent', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '6px', fontSize: 12, cursor: 'not-allowed', opacity: 0.45 }}
        >
          重试任务
        </button>
      </div>
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 16 }}>
      <div className="ws-section-label" style={{ marginBottom: 6 }}>{label}</div>
      <div>{children}</div>
    </div>
  )
}

function findTask(state: WorkspaceState, taskId: string): AgentTask | undefined {
  for (const r of state.rounds) {
    const t = r.tasks.find((x) => x.id === taskId)
    if (t) return t
  }
  return undefined
}

// Local import alias to avoid name clash with the `AgentName` import in artifact-renderers
import type { AgentName } from '../../lib/types'
```

- [ ] **Step 5: Run — expect PASS**

Run: `cd frontend && npx vitest run src/components/workspace/DetailInspector.test.tsx`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workspace/DetailInspector.tsx frontend/src/components/workspace/DetailInspector.test.tsx frontend/src/components/workspace/artifact-renderers.tsx
git commit -m "feat(workspace): add DetailInspector and artifact renderers"
```

---

## Task 11: `Workspace` container + `App.tsx` integration

**Files:**
- Create: `frontend/src/components/workspace/Workspace.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Everything from Tasks 1–10.
- Produces: `<Workspace events report errorMsg runInfo view onBack />`

- [ ] **Step 1: Create `Workspace.tsx`**

```tsx
// frontend/src/components/workspace/Workspace.tsx
import './workspace.css'
import { useRunWorkspace } from '../../lib/useRunWorkspace'
import type { RunEvent, RunInfo } from '../../lib/types'
import { WorkspaceTopbar } from './WorkspaceTopbar'
import { AgentTeamSidebar } from './AgentTeamSidebar'
import { CollaborationTimeline } from './CollaborationTimeline'
import { DetailInspector } from './DetailInspector'

interface Props {
  events: RunEvent[]
  report: unknown
  errorMsg: string
  runInfo: RunInfo | null
  onBack: () => void
}

export function Workspace({ events, report, errorMsg, runInfo, onBack }: Props) {
  const { state, selectedTarget, setSelectedTarget } = useRunWorkspace(events, runInfo, report)

  return (
    <div className="ws-shell" style={{ position: 'relative' }}>
      <WorkspaceTopbar state={state} runInfo={runInfo} errorMsg={errorMsg} report={report} onBack={onBack} />
      <div className="ws-body">
        <AgentTeamSidebar agents={state.agents} selected={selectedTarget} onSelect={setSelectedTarget} />
        <CollaborationTimeline rounds={state.rounds} selected={selectedTarget} onSelect={setSelectedTarget} report={report} />
        <DetailInspector state={state} selected={selectedTarget} onSelect={setSelectedTarget} report={report} />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Modify `App.tsx` — replace the running/report/failed branch**

Replace the bottom `return` of `App.tsx` (the one starting at line 212 in the current file with `<div style={{ padding: 32, maxWidth: 1000, margin: '0 auto' }}>`) with:

```tsx
import { Workspace } from './components/workspace/Workspace'

// ... (inside App component, after the form branch)

return (
  <Workspace
    events={events}
    report={report}
    errorMsg={errorMsg}
    runInfo={null /* fetched below if needed */}
    onBack={goBackToForm}
  />
)
```

To avoid breaking the restore path, the full updated `App.tsx` body for the running/report/failed branch is:

```tsx
return (
  <Workspace
    events={events}
    report={report}
    errorMsg={errorMsg}
    runInfo={runInfoState}
    onBack={goBackToForm}
  />
)
```

Where `runInfoState` is a new state variable we add to `App.tsx`. To keep the diff small, derive it inline from the URL-based restore in `useEffect`:

Add to `App.tsx`:

```ts
const [runInfoState, setRunInfoState] = useState<RunInfo | null>(null)
```

In the existing `restore()` function (inside the `useEffect`), after `const info = await r.json()`, add:

```ts
setRunInfoState(info)
```

And in `startAnalysis`, after the POST succeeds, add:

```ts
setRunInfoState({ run_id: run_id, startup_idea: idea, status: 'running', created_at: null, completed_at: null })
```

Remove the now-unused imports:

```ts
// Remove these from App.tsx imports:
import AgentCard from './components/AgentCard'
import ChallengeLog from './components/ChallengeLog'
// EvidenceReport import also no longer needed directly — it's used inside Workspace children
import { EvidenceReport } from './components/EvidenceReport'
```

Keep `subscribeToRun`, `getRunIdFromURL`, `setRunIdInURL`, `clearRunIdFromURL` as-is. The existing `buildEventsFromR1Outputs` helper can stay defined but is no longer called from App (the hook handles it). Optionally delete it to reduce dead code — leave this as a small cleanup step.

- [ ] **Step 3: Update `App.test.tsx`**

The existing test asserts on `市场分析师` and `● 已完成` text from the old `AgentCard`. Replace those assertions with ones appropriate for the new workspace:

```tsx
// frontend/src/App.test.tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

vi.mock('./lib/sse', () => ({
  subscribeToRun: vi.fn(() => vi.fn()),
}))

describe('App run restoration', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    vi.restoreAllMocks()
  })

  it('restores per-agent progress from the persisted deliberation checkpoint', async () => {
    window.history.replaceState({}, '', '/?run=run-in-progress')
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        run_id: 'run-in-progress',
        status: 'running',
        startup_idea: 'AI Agent 创业',
        round1_outputs: null,
        deliberation_state: {
          current_round: 'round1',
          r1_outputs: { market_analyst: { tam: '100亿' } },
          r1_completed_agents: ['market_analyst'],
        },
      }),
    }) as any

    render(<App />)

    await waitFor(() => {
      // New workspace mounts the sidebar which includes the agent label
      expect(screen.getAllByText('市场分析师').length).toBeGreaterThan(0)
    })
    // Workspace shell should be present (sidebar + timeline + inspector)
    expect(document.querySelector('.ws-shell')).toBeTruthy()
    expect(screen.queryByText('创业机会分析器')).not.toBeInTheDocument()
  })

  it('keeps the run URL and workspace visible when restoration is temporarily unavailable', async () => {
    window.history.replaceState({}, '', '/?run=run-in-progress')
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false }) as any

    render(<App />)

    await waitFor(() => expect(screen.getByText(/暂时无法恢复分析状态/)).toBeInTheDocument())
    expect(window.location.search).toBe('?run=run-in-progress')
  })
})
```

- [ ] **Step 4: Run all frontend tests**

Run: `cd frontend && npm run test`
Expected: all tests PASS.

- [ ] **Step 5: Run typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workspace/Workspace.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "refactor(workspace): mount Workspace from App, retire AgentCard grid"
```

---

## Task 12: Integration test

**Files:**
- Create: `frontend/src/components/workspace/workspace-flow.test.tsx`

- [ ] **Step 1: Write the integration test**

```tsx
// frontend/src/components/workspace/workspace-flow.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { Workspace } from './Workspace'
import type { RunEvent } from '../../lib/types'

// A recorded-style event stream that walks through R1 partial → R2 → R3.
function buildFlow(): RunEvent[] {
  const ev: RunEvent[] = []
  ev.push({ type: 'run.start', run_id: 'r', startup_idea: 'AI Agent 创业方向' } as any)
  // R1: market + competitor + finance
  for (const a of ['market_analyst', 'competitor_researcher', 'finance_analyst'] as const) {
    ev.push({ type: 'agent.start', agent: a, round: 'round1' } as any)
    ev.push({ type: 'tool.start', agent: a, tool: 'search', input_preview: 'AI Agent' } as any)
    ev.push({ type: 'tool.end', agent: a, tool: 'search', evidence_id: `ev-${a}`, output_preview: '' } as any)
    ev.push({ type: 'agent.end', agent: a, round: 'round1', output_summary: { tam: 100 } } as any)
  }
  // risk_reviewer (after first three)
  ev.push({ type: 'agent.start', agent: 'risk_reviewer', round: 'round1' } as any)
  ev.push({ type: 'agent.end', agent: 'risk_reviewer', round: 'round1', output_summary: { risks: [] } } as any)
  // R2 transition
  ev.push({ type: 'round.transition', from_round: 'round1', to_round: 'round2' } as any)
  // R2-A for market + competitor + finance
  for (const a of ['market_analyst', 'competitor_researcher', 'finance_analyst'] as const) {
    ev.push({ type: 'agent.start', agent: a, round: 'round2' } as any)
    ev.push({ type: 'challenge.issued', challenge_id: `c-${a}`, issuer: a, target: 'risk_reviewer', claim: '风险描述', reason: '理由' } as any)
    ev.push({ type: 'agent.end', agent: a, round: 'round2', output_summary: {} } as any)
  }
  // R2-B for the same three
  for (const a of ['market_analyst', 'competitor_researcher', 'finance_analyst'] as const) {
    ev.push({ type: 'agent.start', agent: a, round: 'round2' } as any)
    ev.push({ type: 'challenge.responded', challenge_id: `c-${a}`, target: a, response: '回应', verdict: 'accepted' } as any)
    ev.push({ type: 'agent.end', agent: a, round: 'round2', output_summary: {} } as any)
  }
  // R3
  ev.push({ type: 'round.transition', from_round: 'round2', to_round: 'round3' } as any)
  ev.push({ type: 'agent.start', agent: 'strategy_advisor', round: 'round3' } as any)
  ev.push({ type: 'agent.end', agent: 'strategy_advisor', round: 'round3', output_summary: {} } as any)
  ev.push({ type: 'run.complete', run_id: 'r', report: { decision: 'Go', executive_summary: '可行' } } as any)
  return ev
}

describe('Workspace flow', () => {
  it('progress reaches 100% and all rounds render when flow completes', () => {
    const events = buildFlow()
    let lastPercent = -1
    let lastReport: any = null

    const { rerender } = render(
      <Workspace
        events={[]}
        report={null}
        errorMsg=""
        runInfo={{ run_id: 'r', startup_idea: 'AI Agent 创业方向', status: 'running', created_at: null, completed_at: null }}
        onBack={() => {}}
      />,
    )

    // Incrementally feed events to verify progress increases
    for (let i = 1; i <= events.length; i++) {
      act(() => {
        rerender(
          <Workspace
            events={events.slice(0, i)}
            report={i === events.length ? { decision: 'Go' } : null}
            errorMsg=""
            runInfo={{ run_id: 'r', startup_idea: 'AI Agent 创业方向', status: i === events.length ? 'complete' : 'running', created_at: null, completed_at: null }}
            onBack={() => {}}
          />,
        )
      })
      const percentText = document.querySelector('.ws-mono.ws-faint')?.textContent ?? ''
      const m = percentText.match(/(\d+)%/)
      if (m) {
        const p = parseInt(m[1], 10)
        expect(p).toBeGreaterThanOrEqual(lastPercent)
        lastPercent = p
      }
    }

    // Final state: 100%
    expect(lastPercent).toBe(100)

    // Three round headers visible
    expect(screen.getByText(/第一轮/)).toBeInTheDocument()
    expect(screen.getByText(/第二轮/)).toBeInTheDocument()
    expect(screen.getByText(/第三轮/)).toBeInTheDocument()

    // R3 contains EvidenceReport (renders decision verdict)
    expect(screen.getAllByText('Go').length).toBeGreaterThan(0)
  })

  it('defaults selection to Orchestrator in the inspector', () => {
    render(
      <Workspace
        events={[]}
        report={null}
        errorMsg=""
        runInfo={null}
        onBack={() => {}}
      />,
    )
    // Right inspector shows Orchestrator label
    expect(document.querySelector('.ws-col-right')?.textContent).toMatch(/战略顾问/)
  })
})
```

- [ ] **Step 2: Run — expect PASS**

Run: `cd frontend && npx vitest run src/components/workspace/workspace-flow.test.tsx`
Expected: all PASS.

- [ ] **Step 3: Run the entire frontend test suite**

Run: `cd frontend && npm run test`
Expected: all PASS.

- [ ] **Step 4: Run typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workspace/workspace-flow.test.tsx
git commit -m "test(workspace): add end-to-end workspace flow integration test"
```

---

## Verification Checklist

After all 12 tasks complete, verify by hand in the browser:

1. `cd frontend && npm run dev` and open the dev server.
2. Start a new analysis from the form view. See the empty state `"战略顾问正在拆解任务…"` briefly, then R1 tasks light up one by one. Risk reviewer shows `等待依赖` until first three complete.
3. R2 transitions: market/competitor/finance show R2-A nodes (challenge issued) then R2-B nodes (responded).
4. R3 completes: the strategy_advisor task node embeds `<EvidenceReport>`.
5. Click an agent in the left sidebar — right inspector shows the Agent panel.
6. Click a tool event in the timeline — right inspector shows the Event panel, evidence modal appears when clicking the evidence chip.
7. Click `▸ 展开产物` on a task — artifact preview renders inline, copy-JSON works.
8. Refresh the page mid-run with `?run=xxx` — workspace restores from checkpoint, SSE reconnects.
9. Trigger a failed run (e.g. bad API key) — topbar shows red badge + error message, failed task has red left bar in sidebar and timeline.
10. Complete a run — Export button enables, downloads a JSON file.

## Self-Review Summary

**Spec coverage:**
- §1 Architecture → Task 1–4 (types/constants/CSS shell) + Task 11 (Workspace container, App.tsx integration)
- §2 Derived model → Tasks 1, 2
- §3 Visual system → Task 4 (CSS variables + grid)
- §4 WorkspaceTopbar → Task 6
- §5 AgentTeamSidebar → Task 7 (+ AgentAvatar Task 5)
- §6 CollaborationTimeline → Tasks 8, 9
- §7 DetailInspector → Task 10
- §8 Event mapping / edge cases → Task 2 tests + Task 3 restore/dedupe
- §9 Testing strategy → every task has tests; Task 12 is integration
- §10 Implementation order → matches the 12-task sequence
- §11 Acceptance criteria → covered by integration test + manual checklist

**Placeholder scan:** No "TBD" / "implement later" / "similar to X". All code blocks are complete.

**Type consistency:**
- `WorkspaceState`, `AgentSummary`, `AgentTask`, `Round`, `SelectedTarget` defined in Task 1, used unchanged in Tasks 2–12.
- `buildWorkspace(events, runInfo, report)` signature constant across Tasks 2, 3, 11.
- `useRunWorkspace` return shape `{ state, selectedTarget, setSelectedTarget }` consistent across Tasks 3, 11.
- `AGENT_LABELS`, `STATUS_LABEL`, `EXPECTED_TASKS_PER_AGENT`, `ROUND_META`, `AGENT_ORDER` defined in Task 1, imported by Tasks 5–10.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-22-multi-agent-workspace-redesign.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
