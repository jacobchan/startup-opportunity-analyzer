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
