import { useState } from 'react'
import './HistoryCard.css'

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

const decisionConfig: Record<string, { tone: string; label: string }> = {
  Go: { tone: 'success', label: 'Go' },
  'No-Go': { tone: 'danger', label: 'No-Go' },
  'Conditional-Go': { tone: 'warning', label: 'Conditional-Go' },
}

const statusConfig: Record<string, { tone: string; label: string }> = {
  complete: { tone: 'success', label: '已完成' },
  running: { tone: 'running', label: '进行中' },
  queued: { tone: 'queued', label: '排队中' },
  partial: { tone: 'warning', label: '部分完成' },
  failed: { tone: 'danger', label: '失败' },
}

export default function HistoryCard({ run, onRerun, onDelete, onClick }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const isComplete = run.status === 'complete'
  const isActive = run.status === 'running' || run.status === 'queued'
  const badge = isComplete && run.decision
    ? decisionConfig[run.decision] ?? statusConfig.complete
    : statusConfig[run.status] ?? statusConfig.queued

  const summary = isComplete
    ? run.executive_summary
    : run.status === 'failed'
      ? '分析未能完成'
      : run.status === 'partial'
        ? '已有部分分析结果，可继续查看'
        : run.status === 'running'
          ? 'AI 正在分析中…'
          : '等待开始分析'

  function openRun() {
    onClick(run.run_id)
  }

  return (
    <article
      className="history-card"
      onClick={openRun}
    >
      <div className="history-card__content">
        <div className="history-card__heading">
          <h3 className="history-card__title" title={run.startup_idea}>
            {run.startup_idea}
          </h3>
          <span className={`history-card__badge history-card__badge--${badge.tone}`}>
            <span className="history-card__dot" aria-hidden="true" />
            {badge.label}
          </span>
        </div>

        <p className="history-card__summary">{summary ?? ''}</p>
        <time className="history-card__time" dateTime={run.created_at ?? undefined}>
          {formatTime(run.created_at)}
        </time>
      </div>

      <div className="history-card__actions" onClick={(event) => event.stopPropagation()}>
        <button className="history-card__open" onClick={openRun}>
          {isComplete ? '查看报告' : '查看进度'}
          <span aria-hidden="true">›</span>
        </button>

        <div className="history-card__more">
          <button
            className="history-card__more-button"
            aria-label="更多操作"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            •••
          </button>

          {menuOpen && (
            <div className="history-card__menu" role="menu">
              {!isActive && (
                <button
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false)
                    onRerun(run.startup_idea)
                  }}
                >
                  重新分析
                </button>
              )}
              <button
                className="history-card__delete"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  onDelete(run.run_id)
                }}
              >
                删除记录
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
