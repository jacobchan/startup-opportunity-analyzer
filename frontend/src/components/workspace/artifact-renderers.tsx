// frontend/src/components/workspace/artifact-renderers.tsx
import { useState } from 'react'
import type { AgentName } from '../../lib/types'

interface Props {
  agent: AgentName
  output: unknown
}

export function ArtifactPreview({ agent, output }: Props) {
  if (!output || typeof output !== 'object') {
    return <pre className="ws-mono" style={{ fontSize: 12 }}>{String(output ?? '')}</pre>
  }
  const obj = output as Record<string, unknown>
  switch (agent) {
    case 'market_analyst':    return <MarketRenderer data={obj} />
    case 'competitor_researcher': return <CompetitorRenderer data={obj} />
    case 'finance_analyst':   return <FinanceRenderer data={obj} />
    case 'risk_reviewer':     return <RiskRenderer data={obj} />
    case 'strategy_advisor':  return <StrategyRenderer data={obj} />
    default:                  return <JsonFallback data={obj} />
  }
}

function Field({ label, value }: { label: string; value: unknown }) {
  if (value == null || value === '') return null
  return (
    <div style={{ display: 'flex', gap: 12, padding: '4px 0', fontSize: 13 }}>
      <span className="ws-faint" style={{ width: 96, flexShrink: 0 }}>{label}</span>
      <span>{String(value)}</span>
    </div>
  )
}

function MarketRenderer({ data }: { data: Record<string, unknown> }) {
  return (
    <div>
      <Field label="TAM" value={data.tam} />
      <Field label="SAM" value={data.sam} />
      <Field label="SOM" value={data.som} />
      <Field label="增长率" value={data.growth_rate} />
      {Array.isArray(data.user_personas) && (
        <>
          <div className="ws-section-label" style={{ marginTop: 12, marginBottom: 4 }}>用户画像</div>
          <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13 }}>
            {(data.user_personas as unknown[]).map((p, i) => <li key={i}>{String(p)}</li>)}
          </ul>
        </>
      )}
      <ExtraFields data={data} knownKeys={['tam', 'sam', 'som', 'growth_rate', 'user_personas']} />
    </div>
  )
}

function CompetitorRenderer({ data }: { data: Record<string, unknown> }) {
  const competitors = Array.isArray(data.competitors) ? data.competitors as Record<string, unknown>[] : []
  return (
    <div>
      {competitors.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {['名称', '差异化', '威胁等级'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--ws-border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {competitors.map((c, i) => (
              <tr key={i}>
                <td style={{ padding: '6px 8px' }}>{String(c.name ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(c.differentiator ?? c.differentiation ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(c.threat_level ?? c.threat ?? '')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <div className="ws-muted">无竞品数据</div>}
      <ExtraFields data={data} knownKeys={['competitors']} />
    </div>
  )
}

function FinanceRenderer({ data }: { data: Record<string, unknown> }) {
  return (
    <div>
      <Field label="LTV" value={data.ltv} />
      <Field label="CAC" value={data.cac} />
      <Field label="毛利率" value={data.gross_margin} />
      <Field label="定价策略" value={data.pricing_strategy} />
      <Field label="资金需求" value={data.funding_required} />
      <ExtraFields data={data} knownKeys={['ltv', 'cac', 'gross_margin', 'pricing_strategy', 'funding_required']} />
    </div>
  )
}

function RiskRenderer({ data }: { data: Record<string, unknown> }) {
  const risks = Array.isArray(data.risks) ? data.risks as Record<string, unknown>[] : []
  return (
    <div>
      {risks.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              {['维度', '严重程度', '缓解措施'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--ws-border)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {risks.map((r, i) => (
              <tr key={i}>
                <td style={{ padding: '6px 8px' }}>{String(r.dimension ?? r.category ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(r.severity ?? '')}</td>
                <td style={{ padding: '6px 8px' }}>{String(r.mitigation ?? '')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <div className="ws-muted">无风险数据</div>}
      <ExtraFields data={data} knownKeys={['risks']} />
    </div>
  )
}

function StrategyRenderer({ data }: { data: Record<string, unknown> }) {
  // strategy_advisor uses EvidenceReport via the timeline; this renderer
  // is only hit when viewed as artifact from the inspector.
  return <JsonFallback data={data} />
}

function ExtraFields({ data, knownKeys }: { data: Record<string, unknown>; knownKeys: string[] }) {
  const extras = Object.keys(data).filter((k) => !knownKeys.includes(k))
  if (extras.length === 0) return null
  return (
    <>
      <div className="ws-section-label" style={{ marginTop: 12, marginBottom: 4 }}>其他字段</div>
      <dl style={{ fontSize: 12, margin: 0 }}>
        {extras.map((k) => (
          <div key={k} style={{ display: 'flex', gap: 12, padding: '2px 0' }}>
            <dt className="ws-faint" style={{ width: 120 }}>{k}</dt>
            <dd style={{ margin: 0 }}>{String(data[k])}</dd>
          </div>
        ))}
      </dl>
    </>
  )
}

function JsonFallback({ data }: { data: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="ws-faint"
        style={{ background: 'none', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 12 }}
      >
        {open ? '▾ 原始 JSON' : '▸ 原始 JSON'}
      </button>
      {open && (
        <pre className="ws-mono" style={{ fontSize: 11, background: 'var(--ws-bg)', padding: 8, borderRadius: 6, marginTop: 8, whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}
