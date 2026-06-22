import { useState, useEffect, useRef } from 'react'
import StartupForm from './components/StartupForm'
import HistoryList from './components/HistoryList'
import { subscribeToRun } from './lib/sse'
import type { RunEvent, RunInfo } from './lib/types'
import { Workspace } from './components/workspace/Workspace'

type View = 'form' | 'running' | 'report' | 'failed' | 'loading'

function getRunIdFromURL(): string | null {
  return new URLSearchParams(window.location.search).get('run')
}

function setRunIdInURL(runId: string) {
  window.history.replaceState({}, '', `?run=${runId}`)
}

function clearRunIdFromURL() {
  window.history.replaceState({}, '', window.location.pathname)
}

export default function App() {
  const [view, setView] = useState<View>(getRunIdFromURL() ? 'loading' : 'form')
  const [events, setEvents] = useState<RunEvent[]>([])
  const [report, setReport] = useState<any>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [runInfoState, setRunInfoState] = useState<RunInfo | null>(null)
  const restoreTried = useRef(false)

  // On mount: if URL has run_id, restore session from backend
  useEffect(() => {
    const rawId = getRunIdFromURL()
    if (!rawId || restoreTried.current) return
    restoreTried.current = true
    const runId = rawId

    async function restore() {
      try {
        const r = await fetch(`/runs/${runId}`)
        if (!r.ok) throw new Error('run not found')
        const info = await r.json()
        setRunInfoState(info)

        // The engine checkpoints after every agent. round1_outputs is only a
        // legacy snapshot written after all of R1 finishes, so prefer the
        // live checkpoint when restoring a page mid-run. The workspace hook
        // (useRunWorkspace) synthesizes preview events from the checkpoint.

        if (info.status === 'complete') {
          const repResp = await fetch(`/runs/${runId}/report`)
          const rep = await repResp.json()
          setReport(rep)
          setView('report')
          return
        }

        if (info.status === 'failed') {
          setErrorMsg('分析失败')
          setView('failed')
          return
        }

        // running or queued — reconnect SSE. The hook will synthesize
        // preview events from the checkpoint while we wait for live events.
        setView('running')
        subscribeToRun(
          runId,
          (event) => {
            setEvents((prev) => [...prev, event])
            if (event.type === 'run.complete') {
              setReport((event as any).report)
              setView('report')
            } else if (event.type === 'run.failed') {
              setErrorMsg((event as any).error || '分析失败')
              setView('failed')
            }
          },
          async () => {
            try {
              const r2 = await fetch(`/runs/${runId}`)
              const info2 = await r2.json()
              if (info2.status === 'complete') {
                const repResp2 = await fetch(`/runs/${runId}/report`)
                const rep2 = await repResp2.json()
                setReport(rep2)
                setView('report')
              } else if (info2.status === 'failed') {
                setErrorMsg('分析失败')
                setView('failed')
              }
            } catch { /* ignore */ }
          },
        )
      } catch {
        // A transient API/SSE outage must not erase the run identity and
        // strand the user on the homepage. Keep the workspace + URL so a
        // later refresh can restore from the persisted checkpoint.
        setErrorMsg('暂时无法恢复分析状态，请稍后刷新重试')
        setView('failed')
      }
    }

    restore()
  }, [])

  async function startAnalysis(idea: string) {
    setEvents([])
    setReport(null)
    setErrorMsg('')
    setView('running')

    const resp = await fetch('/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ startup_idea: idea }),
    })
    if (!resp.ok) {
      setErrorMsg('启动失败')
      setView('failed')
      return
    }
    const { run_id } = await resp.json()
    setRunIdInURL(run_id)
    setRunInfoState({ run_id, startup_idea: idea, status: 'running', created_at: null, completed_at: null })

    const cleanup = subscribeToRun(
      run_id,
      (event) => {
        setEvents((prev) => [...prev, event])
        if (event.type === 'run.complete') {
          setReport((event as any).report)
          setView('report')
          cleanup()
        } else if (event.type === 'run.failed') {
          setErrorMsg((event as any).error)
          setView('failed')
          cleanup()
        }
      },
      (err) => {
        setErrorMsg(err.message)
        setView('failed')
      },
    )
  }

  function goBackToForm() {
    clearRunIdFromURL()
    setView('form')
    setEvents([])
    setReport(null)
    setErrorMsg('')
    setRunInfoState(null)
  }

  if (view === 'loading') {
    return (
      <div style={{ padding: 32, maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
        <p>正在恢复分析状态...</p>
      </div>
    )
  }

  if (view === 'form') {
    return (
      <div style={{
        maxWidth: 680, margin: '0 auto', padding: '60px 32px 80px',
      }}>
        <div style={{ marginBottom: 48, textAlign: 'center' }}>
          <h1 style={{
            fontSize: 28, fontWeight: 700, color: '#0d0d0d', margin: '0 0 8px',
            letterSpacing: '-0.02em',
          }}>
            创业机会分析器
          </h1>
          <p style={{ color: '#8a8a8a', fontSize: 15, margin: 0, lineHeight: 1.5 }}>
            5 个 AI Agent 协作分析你的创业想法，10–20 分钟输出 Go / No-Go 结论
          </p>
        </div>

        <StartupForm onSubmit={startAnalysis} loading={false} />

        <HistoryList
          onRerun={(idea) => startAnalysis(idea)}
          onViewRun={(runId) => {
            setRunIdInURL(runId)
            window.location.reload()
          }}
        />
      </div>
    )
  }

  return (
    <Workspace
      events={events}
      report={report}
      errorMsg={errorMsg}
      runInfo={runInfoState}
      onBack={goBackToForm}
      view={view as 'running' | 'report' | 'failed'}
    />
  )
}
