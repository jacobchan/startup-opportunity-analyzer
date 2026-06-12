import { useState, useEffect, useRef } from 'react'
import StartupForm from './components/StartupForm'
import HistoryList from './components/HistoryList'
import { subscribeToRun } from './lib/sse'
import type { RunEvent } from './lib/types'
import AgentCard from './components/AgentCard'
import ChallengeLog from './components/ChallengeLog'
import EvidenceReport from './components/EvidenceReport'

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

function buildEventsFromR1Outputs(outputs: Record<string, unknown> | null): RunEvent[] {
  if (!outputs) return []
  const events: RunEvent[] = []
  for (const [agent, output] of Object.entries(outputs)) {
    events.push({
      type: 'agent.end',
      agent: agent as any,
      round: 'round1',
      output_summary: output,
    })
  }
  return events
}

export default function App() {
  const [view, setView] = useState<View>(getRunIdFromURL() ? 'loading' : 'form')
  const [events, setEvents] = useState<RunEvent[]>([])
  const [report, setReport] = useState<any>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')
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

        const synthEvents = buildEventsFromR1Outputs(info.round1_outputs ?? null)

        if (info.status === 'complete') {
          const repResp = await fetch(`/runs/${runId}/report`)
          const rep = await repResp.json()
          setEvents(synthEvents)
          setReport(rep)
          setView('report')
          return
        }

        if (info.status === 'failed') {
          setEvents(synthEvents)
          setErrorMsg('分析失败')
          setView('failed')
          return
        }

        // running or queued — preload synthetic events + reconnect SSE
        setEvents(synthEvents)
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
        clearRunIdFromURL()
        setView('form')
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
      <div style={{ padding: 32, maxWidth: 800, margin: '0 auto' }}>
        <h1>创业机会分析器</h1>
        <p style={{ color: '#666' }}>5 个 AI Agent 协作分析你的想法，10-20 分钟出 Go/No-Go 结论</p>
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
    <div style={{ padding: 32, maxWidth: 1000, margin: '0 auto' }}>
      <button onClick={goBackToForm} style={{ marginBottom: 16, background: 'none', border: '1px solid #ddd', borderRadius: 6, padding: '6px 12px', cursor: 'pointer' }}>← 重新开始</button>
      {view === 'failed' && <div style={{ color: '#dc2626', marginBottom: 16, padding: 12, background: '#fef2f2', borderRadius: 8 }}>错误：{errorMsg}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
        {(['market_analyst', 'competitor_researcher', 'finance_analyst', 'risk_reviewer', 'strategy_advisor'] as const).map((agent) => (
          <AgentCard key={agent} agent={agent} events={events} />
        ))}
      </div>
      <ChallengeLog events={events} />
      {view === 'report' && report && <EvidenceReport report={report} />}
    </div>
  )
}
