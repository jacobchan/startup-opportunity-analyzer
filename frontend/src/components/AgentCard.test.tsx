import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgentCard from './AgentCard'

describe('AgentCard', () => {
  it('shows waiting status when no events', () => {
    render(<AgentCard agent="market_analyst" events={[]} />)
    expect(screen.getByText(/待命/)).toBeInTheDocument()
  })

  it('shows running status when agent started but not ended', () => {
    const events = [{ type: 'agent.start', agent: 'market_analyst', round: 'round1' }]
    render(<AgentCard agent="market_analyst" events={events as any} />)
    expect(screen.getByText(/运行中/)).toBeInTheDocument()
  })

  it('shows completed status when agent ended', () => {
    const events = [
      { type: 'agent.start', agent: 'market_analyst', round: 'round1' },
      { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: {} },
    ]
    render(<AgentCard agent="market_analyst" events={events as any} />)
    expect(screen.getByText(/已完成/)).toBeInTheDocument()
  })

  it('shows last tool call when available', () => {
    const events = [
      { type: 'agent.start', agent: 'market_analyst', round: 'round1' },
      { type: 'tool.start', agent: 'market_analyst', tool: 'search', input_preview: 'AI Agent 市场规模' },
    ]
    render(<AgentCard agent="market_analyst" events={events as any} />)
    expect(screen.getByText(/工具: search/)).toBeInTheDocument()
  })
})
