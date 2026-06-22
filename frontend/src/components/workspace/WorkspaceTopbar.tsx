// frontend/src/components/workspace/WorkspaceTopbar.tsx
import './workspace.css'
import type { WorkspaceState } from '../../lib/workspace-types'
import type { RunInfo } from '../../lib/types'

interface Props {
  state: WorkspaceState
  runInfo: RunInfo | null
  errorMsg: string
  report?: unknown
  onBack: () => void
  view: 'running' | 'report' | 'failed'
}

const STATUS_PILL_LABEL: Record<WorkspaceState['status'], string> = {
  pending: '待启动',
  running: '进行中',
  done: '已完成',
  failed: '分析失败',
}

export function WorkspaceTopbar({ state, runInfo, errorMsg, report, onBack, view }: Props) {
  const percent = state.progress.percent
  const barCls = state.status === 'failed' ? 'ws-clr-bg-failed' : state.status === 'done' ? 'ws-clr-bg-done' : 'ws-clr-bg-running'

  function handleExport() {
    if (!report || !runInfo) return
    const payload = JSON.stringify({
      run_id: runInfo.run_id,
      startup_idea: runInfo.startup_idea,
      report,
    }, null, 2)
    const blob = new Blob([payload], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `市场进入策略分析-${runInfo.run_id.slice(0, 8)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const startupIdea = runInfo?.startup_idea ?? ''
  const title = startupIdea.length > 32
    ? startupIdea.slice(0, 32) + '…'
    : startupIdea

  return (
    <header style={{
      display: 'flex', alignItems: 'center', gap: 12, height: 56,
      padding: '0 24px', background: 'var(--ws-surface)',
      borderBottom: '1px solid var(--ws-border)', flexShrink: 0,
      position: 'relative',
    }}>
      <button
        onClick={onBack}
        style={{
          background: 'transparent', border: '1px solid var(--ws-border)',
          borderRadius: 6, padding: '6px 12px', cursor: 'pointer', fontSize: 13,
        }}
        aria-label="返回"
      >
        ← 返回
      </button>

      <div style={{ width: 1, height: 24, background: 'var(--ws-border)' }} />

      <h1 title={startupIdea} style={{
        fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--ws-text)',
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        maxWidth: 320,
      }}>
        {title}
      </h1>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{
          width: 180, height: 8, background: 'var(--ws-border)',
          borderRadius: 999, overflow: 'hidden',
        }}>
          <div className={barCls} style={{ width: `${percent}%`, height: '100%', transition: 'width 160ms ease, background 160ms ease' }} />
        </div>
        <span data-testid="ws-progress-percent" className="ws-mono ws-faint" style={{ fontSize: 12 }}>{percent}%</span>
      </div>

      <span className={`ws-pill ws-clr-${state.status}`} style={{ background: 'var(--ws-bg)' }}>
        <span className="ws-pill__dot" />
        {STATUS_PILL_LABEL[state.status]}
      </span>

      <div style={{ flex: 1 }} />

      <button disabled title="暂停功能即将支持" style={btnDisabled()}>⏸ 暂停</button>
      <button disabled title="终止功能即将支持" style={btnDisabled()}>⏹ 终止</button>
      <button
        onClick={handleExport}
        disabled={!report}
        title={!report ? '分析完成后可导出' : '导出 JSON'}
        style={report ? btnActive() : btnDisabled()}
        aria-label="导出"
      >
        ⤓ 导出
      </button>

      {view === 'failed' && errorMsg && (
        <div style={{ position: 'absolute', top: 56, left: 0, right: 0, padding: '8px 24px', background: 'var(--ws-status-failed-bg)', color: 'var(--ws-status-failed)', fontSize: 12 }}>
          {errorMsg}
        </div>
      )}
    </header>
  )
}

function btnDisabled(): React.CSSProperties {
  return {
    background: 'transparent',
    border: '1px solid var(--ws-border)',
    borderRadius: 6,
    padding: '6px 12px',
    fontSize: 13,
    cursor: 'not-allowed',
    opacity: 0.45,
  }
}

function btnActive(): React.CSSProperties {
  return {
    background: 'var(--ws-surface)',
    border: '1px solid var(--ws-border-strong)',
    borderRadius: 6,
    padding: '6px 12px',
    fontSize: 13,
    cursor: 'pointer',
    color: 'var(--ws-text)',
  }
}
