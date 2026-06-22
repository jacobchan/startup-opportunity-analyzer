export type RunStatus = 'queued' | 'running' | 'complete' | 'failed' | 'partial'

export interface RunInfo {
  run_id: string
  startup_idea: string
  status: RunStatus
  created_at: string | null
  completed_at: string | null
  deliberation_state?: {
    current_round?: string
    r1_outputs?: Record<string, unknown>
    r1_completed_agents?: string[]
  }
  round1_outputs?: Record<string, unknown> | null
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
