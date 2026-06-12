import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import EvidenceReport from './EvidenceReport'

describe('EvidenceReport', () => {
  it('renders decision verdict', () => {
    render(<EvidenceReport report={{ decision: 'Go', executive_summary: 'x' }} />)
    expect(screen.getByText('Go')).toBeInTheDocument()
  })

  it('renders key risks', () => {
    render(<EvidenceReport report={{ decision: 'Go', key_risks: ['风险 A', '风险 B'] }} />)
    expect(screen.getByText('风险 A')).toBeInTheDocument()
    expect(screen.getByText('风险 B')).toBeInTheDocument()
  })

  it('renders next steps with priority and timeline', () => {
    render(<EvidenceReport report={{
      decision: 'Conditional-Go',
      next_steps: [{ action: '做 MVP', priority: 'P0', timeline: '1 月' }],
    }} />)
    expect(screen.getByText(/做 MVP/)).toBeInTheDocument()
    expect(screen.getByText(/P0/)).toBeInTheDocument()
  })

  it('shows N/A when no verdict', () => {
    render(<EvidenceReport report={{}} />)
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })
})
