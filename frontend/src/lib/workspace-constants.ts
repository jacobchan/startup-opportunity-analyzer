// frontend/src/lib/workspace-constants.ts
import type { AgentName } from './types'
import type { AgentStatus, RoundId } from './workspace-types'

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
