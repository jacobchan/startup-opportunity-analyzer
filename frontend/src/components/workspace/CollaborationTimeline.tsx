// frontend/src/components/workspace/CollaborationTimeline.tsx
import './workspace.css'
import { useEffect, useRef, useState } from 'react'
import type { Round, SelectedTarget } from '../../lib/workspace-types'
import { TimelineTaskItem } from './TimelineTaskItem'
import EvidenceReport from '../EvidenceReport'

interface Props {
  rounds: Round[]
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  report?: any
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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  report?: any
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
