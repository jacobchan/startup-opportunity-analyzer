import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ChallengeLog from './ChallengeLog'

describe('ChallengeLog', () => {
  it('renders nothing when no challenges', () => {
    const { container } = render(<ChallengeLog events={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders challenge with issuer and target names', () => {
    const events = [
      {
        type: 'challenge.issued',
        challenge_id: 'ch-1',
        issuer: 'market_analyst',
        target: 'finance_analyst',
        claim: 'LTV 假设过高',
        reason: '行业基准是 X',
      },
    ]
    render(<ChallengeLog events={events as any} />)
    expect(screen.getByText(/市场分析师/)).toBeInTheDocument()
    expect(screen.getByText(/财务分析师/)).toBeInTheDocument()
    expect(screen.getByText(/LTV 假设过高/)).toBeInTheDocument()
  })

  it('shows response with verdict when present', () => {
    const events = [
      {
        type: 'challenge.issued',
        challenge_id: 'ch-1', issuer: 'market_analyst', target: 'finance_analyst',
        claim: 'c', reason: 'd',
      },
      {
        type: 'challenge.responded',
        challenge_id: 'ch-1', target: 'finance_analyst',
        response: '已调整 - 采用你的建议', verdict: 'modified',
      },
    ]
    render(<ChallengeLog events={events as any} />)
    expect(screen.getByText(/已调整 - 采用你的建议/)).toBeInTheDocument()
    expect(screen.getByText(/modified/)).toBeInTheDocument()
  })
})
