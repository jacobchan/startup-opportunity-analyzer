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
