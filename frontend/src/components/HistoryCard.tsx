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
  const summary = isComplete
    ? run.executive_summary
    : run.status === 'failed'
      ? '分析失败'
      : '分析进行中，预计 10-20 分钟...'

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
