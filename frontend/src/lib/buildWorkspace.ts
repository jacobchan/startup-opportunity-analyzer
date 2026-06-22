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
  _report: unknown,
): WorkspaceState {
  const rounds = emptyRounds()
  const agents = emptyAgentSummaries()
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
    if (!firstThreeDone) return
    let riskTask = r1TasksByAgent.get('risk_reviewer')
    if (!riskTask) {
      // Create the risk_reviewer task in waiting state (it hasn't emitted agent.start yet)
      riskTask = {
        id: 'r1:risk_reviewer',
        agent: 'risk_reviewer',
        round: 'r1',
        status: 'pending',
        startedAt: null,
        endedAt: null,
        events: [],
      }
      r1.tasks.push(riskTask)
    }
    if (riskTask.status === 'pending') {
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
