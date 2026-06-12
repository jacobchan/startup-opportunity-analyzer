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

const decisionConfig: Record<string, { bg: string; fg: string; dot: string }> = {
  'Go':             { bg: '#ecfdf3', fg: '#0e6245', dot: '#16a34a' },
  'No-Go':          { bg: '#fef2f2', fg: '#991b1b', dot: '#dc2626' },
  'Conditional-Go': { bg: '#fff7ed', fg: '#7c2d12', dot: '#ea580c' },
}

const statusConfig: Record<string, { bg: string; fg: string; label: string }> = {
  running: { bg: '#eff6ff', fg: '#1e40af', label: '进行中' },
  queued:  { bg: '#eff6ff', fg: '#1e40af', label: '排队中' },
  failed:  { bg: '#fef2f2', fg: '#991b1b', label: '失败' },
}

export default function HistoryCard({ run, onRerun, onDelete, onClick }: Props) {
  const isComplete = run.status === 'complete'
  const decision = run.decision ? decisionConfig[run.decision] : null
  const status = statusConfig[run.status] ?? statusConfig.queued

  const summary = isComplete
    ? run.executive_summary
    : run.status === 'failed'
      ? '分析未能完成'
      : run.status === 'running'
        ? 'AI 正在分析中...'
        : '等待开始分析'

  return (
    <div
      onClick={() => isComplete && onClick(run.run_id)}
      style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        padding: '20px 24px',
        border: '1px solid #eaeaea',
        borderRadius: 12,
        cursor: isComplete ? 'pointer' : 'default',
        background: '#fff',
        transition: 'border-color 120ms ease, box-shadow 120ms ease',
      }}
      onMouseEnter={(e) => {
        if (isComplete) {
          e.currentTarget.style.borderColor = '#d4d4d4'
          e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)'
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#eaeaea'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Top row: idea + badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{
            fontSize: 15, fontWeight: 500, color: '#111',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            maxWidth: 340,
          }}>
            {run.startup_idea.length > 40 ? run.startup_idea.slice(0, 40) + '...' : run.startup_idea}
          </span>

          {isComplete && decision && (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              background: decision.bg, color: decision.fg,
              padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500,
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%', background: decision.dot,
              }} />
              {run.decision}
            </span>
          )}

          {!isComplete && (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              background: status.bg, color: status.fg,
              padding: '2px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500,
            }}>
              {run.status === 'running' && (
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: '#3b82f6',
                  animation: 'pulse 2s ease-in-out infinite',
                }} />
              )}
              {status.label}
            </span>
          )}
        </div>

        {/* Summary */}
        <p style={{
          color: run.status === 'running' || run.status === 'queued' ? '#9e9e9e' : '#5f5f5f',
          fontSize: 13, lineHeight: 1.5, margin: 0,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          maxWidth: 460,
        }}>
          {summary ?? ''}
        </p>

        {/* Time */}
        <span style={{ color: '#b0b0b0', fontSize: 12, marginTop: 6, display: 'inline-block' }}>
          {formatTime(run.created_at)}
        </span>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, marginLeft: 16, flexShrink: 0 }}
           onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => onRerun(run.startup_idea)}
          style={{
            padding: '6px 14px', fontSize: 12, fontWeight: 500,
            border: '1px solid #e0e0e0', borderRadius: 8,
            cursor: 'pointer', background: '#fff', color: '#333',
            transition: 'background 120ms ease',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = '#f5f5f5' }}
          onMouseLeave={(e) => { e.currentTarget.style.background = '#fff' }}
        >
          重跑
        </button>
        <button
          onClick={() => onDelete(run.run_id)}
          style={{
            padding: '6px 14px', fontSize: 12, fontWeight: 500,
            border: '1px solid #fecaca', borderRadius: 8,
            cursor: 'pointer', background: '#fff', color: '#dc2626',
            transition: 'background 120ms ease',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = '#fef2f2' }}
          onMouseLeave={(e) => { e.currentTarget.style.background = '#fff' }}
        >
          删除
        </button>
      </div>
    </div>
  )
}
