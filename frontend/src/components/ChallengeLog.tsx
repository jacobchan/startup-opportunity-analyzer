import type { RunEvent } from '../lib/types'

interface Props {
  events: RunEvent[]
}

const NAME_MAP: Record<string, string> = {
  market_analyst: '市场分析师',
  competitor_researcher: '竞品调研员',
  finance_analyst: '财务分析师',
  risk_reviewer: '风险评审员',
  strategy_advisor: '战略顾问',
}

export default function ChallengeLog({ events }: Props) {
  const challenges = events.filter((e) => e.type === 'challenge.issued') as Extract<RunEvent, { type: 'challenge.issued' }>[]
  const responses = events.filter((e) => e.type === 'challenge.responded') as Extract<RunEvent, { type: 'challenge.responded' }>[]

  if (challenges.length === 0) return null

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ fontSize: 16 }}>挑战日志</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {challenges.map((ch) => {
          const response = responses.find((r) => r.challenge_id === ch.challenge_id)
          return (
            <div key={ch.challenge_id} style={{
              padding: 12, background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 8,
            }}>
              <div style={{ fontSize: 13 }}>
                <strong>{NAME_MAP[ch.issuer] || ch.issuer}</strong> 挑战 <strong>{NAME_MAP[ch.target] || ch.target}</strong>
              </div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                论断: {ch.claim}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>
                理由: {ch.reason}
              </div>
              {response && (
                <div style={{ fontSize: 12, marginTop: 8, padding: 8, background: '#fff', borderRadius: 4 }}>
                  <strong>{NAME_MAP[response.target] || response.target} 回应:</strong> {response.response}
                  <span style={{ marginLeft: 8, color: response.verdict === 'rejected' ? '#dc2626' : '#10b981' }}>
                    [{response.verdict}]
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
