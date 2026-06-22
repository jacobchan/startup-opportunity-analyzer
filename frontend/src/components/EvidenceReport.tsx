import { useEffect, useState } from 'react'

interface EvidenceContent {
  evidence_id: string
  title: string | null
  url: string | null
  content_excerpt: string
}

interface Props {
  report: any
}

const VERDICT_COLOR: Record<string, string> = {
  Go: '#10b981',
  'No-Go': '#dc2626',
  'Conditional-Go': '#f59e0b',
}

export default function EvidenceReport({ report }: Props) {
  const [modal, setModal] = useState<EvidenceContent | null>(null)

  useEffect(() => {
    if (!modal) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setModal(null)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [modal])

  const verdict = report?.decision
  const color = verdict ? (VERDICT_COLOR[verdict] || '#666') : '#666'

  async function showEvidence(evidenceId: string) {
    const resp = await fetch(`/evidence/${evidenceId}`)
    if (resp.ok) {
      setModal(await resp.json())
    }
  }

  function renderEvidenceLinks(text: string | undefined) {
    if (!text) return text
    // evidence_id pattern: ev-xxx (UUID hex prefix)
    const parts = text.split(/(ev-[a-f0-9]+)/g)
    return parts.map((part, i) => {
      if (/^ev-[a-f0-9]+$/i.test(part)) {
        return (
          <button
            key={i}
            onClick={() => showEvidence(part)}
            style={{
              background: '#e0f2fe', border: '1px solid #7dd3fc',
              borderRadius: 4, padding: '0 4px', cursor: 'pointer',
              fontSize: 'inherit', fontFamily: 'inherit',
            }}
          >
            [{part}]
          </button>
        )
      }
      return part
    })
  }

  return (
    <section style={{ marginTop: 32, background: '#fff', padding: 24, borderRadius: 8, border: '1px solid #e5e5e5' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, margin: 0 }}>最终评估</h2>
        <span style={{
          padding: '4px 12px', background: color, color: '#fff',
          borderRadius: 4, fontSize: 14, fontWeight: 600,
        }}>{verdict || 'N/A'}</span>
      </div>

      <div style={{ fontSize: 14, lineHeight: 1.6 }}>
        <p><strong>结论：</strong>{renderEvidenceLinks(report?.executive_summary)}</p>
        <p><strong>市场机会：</strong>{report?.market_opportunity_summary}</p>
        <p><strong>竞争优势：</strong>{report?.competitive_advantage}</p>
        <p><strong>财务可行性：</strong>{report?.financial_viability}</p>
        <p><strong>信心度：</strong>{report?.final_confidence}</p>
      </div>

      {report?.key_risks?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong style={{ fontSize: 14 }}>关键风险：</strong>
          <ul style={{ fontSize: 13, marginTop: 8 }}>
            {report.key_risks.map((r: string, i: number) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {report?.challenge_disposition && (report.challenge_disposition.modified?.length > 0 || report.challenge_disposition.accepted?.length > 0) && (
        <div style={{ marginTop: 16, padding: 12, background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 8 }}>
          <strong style={{ fontSize: 14 }}>经挑战修正的关键结论：</strong>
          <div style={{ fontSize: 12, color: '#666', marginTop: 4, marginBottom: 8 }}>
            R2 交叉辩论中，以下论断被其他 agent 接受 (accepted) 或修正 (modified)：
          </div>
          {[...(report.challenge_disposition.modified || []), ...(report.challenge_disposition.accepted || [])].map((c: any, i: number) => (
            <div key={i} style={{ marginTop: 8, padding: 8, background: '#fff', borderRadius: 4 }}>
              <div style={{ fontSize: 12 }}>
                <strong>{c.issuer || '其他 agent'}</strong> 挑战了:
                <em style={{ marginLeft: 4 }}>“{c.claim}”</em>
              </div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                回应: {c.response}
              </div>
              <code style={{ fontSize: 11, color: '#92400e' }}>[{c.challenge_id}]</code>
            </div>
          ))}
        </div>
      )}

      {report?.next_steps?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong style={{ fontSize: 14 }}>下一步行动：</strong>
          <ul style={{ fontSize: 13, marginTop: 8 }}>
            {report.next_steps.map((s: any, i: number) => (
              <li key={i}>
                <strong>[{s.priority}]</strong> {s.action} <em style={{ color: '#666' }}>({s.timeline})</em>
              </li>
            ))}
          </ul>
        </div>
      )}

      {modal && (
        <div
          onClick={() => setModal(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: '#fff', padding: 24, maxWidth: 720, maxHeight: '80vh',
              overflow: 'auto', borderRadius: 8,
            }}
          >
            <h3 style={{ margin: 0 }}>{modal.title || '证据原文'}</h3>
            {modal.url && <a href={modal.url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>{modal.url}</a>}
            <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 12 }}>{modal.content_excerpt}</pre>
            <button onClick={() => setModal(null)} style={{ marginTop: 12, padding: '6px 12px', cursor: 'pointer' }}>关闭</button>
          </div>
        </div>
      )}
    </section>
  )
}
