// frontend/src/components/workspace/AgentAvatar.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentAvatar } from './AgentAvatar'
import type { AgentSummary } from '../../lib/workspace-types'

const mk = (over: Partial<AgentSummary>): AgentSummary => ({
  name: 'market_analyst',
  label: '市场分析师',
  role: 'analyst',
  status: 'pending',
  currentAction: '等待启动',
  progress: { done: 0, total: 3 },
  ...over,
})

describe('AgentAvatar', () => {
  it('renders the agent label and a status dot', () => {
    render(<AgentAvatar agent={mk({ label: '市场分析师', status: 'running' })} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()
    expect(document.querySelector('.ws-dot--running')).toBeTruthy()
  })

  it('uses the large dot when size=lg', () => {
    render(<AgentAvatar agent={mk({ status: 'running' })} size="lg" />)
    expect(document.querySelector('.ws-dot--lg')).toBeTruthy()
  })

  it('uses hollow ring when status=waiting', () => {
    render(<AgentAvatar agent={mk({ status: 'waiting' })} />)
    expect(document.querySelector('.ws-dot--waiting')).toBeTruthy()
  })
})
