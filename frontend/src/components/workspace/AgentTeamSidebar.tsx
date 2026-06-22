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
