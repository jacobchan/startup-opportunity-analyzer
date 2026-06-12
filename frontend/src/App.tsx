import { useState } from 'react'
import StartupForm from './components/StartupForm'
import { subscribeToRun } from './lib/sse'
import type { RunEvent } from './lib/types'
import AgentCard from './components/AgentCard'
import ChallengeLog from './components/ChallengeLog'
import EvidenceReport from './components/EvidenceReport'

type View = 'form' | 'running' | 'report' | 'failed'

export default function App() {
  const [view, setView] = useState<View>('form')
  const [events, setEvents] = useState<RunEvent[]>([])
  const [report, setReport] = useState<any>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')

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

  if (view === 'form') {
    return (
      <div style={{ padding: 32, maxWidth: 800, margin: '0 auto' }}>
        <h1>创业机会分析器</h1>
        <p style={{ color: '#666' }}>5 个 AI Agent 协作分析你的想法，10-20 分钟出 Go/No-Go 结论</p>
        <StartupForm onSubmit={startAnalysis} loading={false} />
      </div>
    )
  }

  if (view === 'running' || view === 'report' || view === 'failed') {
    return (
      <div style={{ padding: 32, maxWidth: 1000, margin: '0 auto' }}>
        <button onClick={() => setView('form')} style={{ marginBottom: 16, background: 'none', border: '1px solid #ddd', borderRadius: 6, padding: '6px 12px', cursor: 'pointer' }}>← 重新开始</button>
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

  return null
}
