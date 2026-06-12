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
