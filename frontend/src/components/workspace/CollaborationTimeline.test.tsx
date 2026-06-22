// frontend/src/components/workspace/CollaborationTimeline.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CollaborationTimeline } from './CollaborationTimeline'
import type { Round } from '../../lib/workspace-types'

const rounds: Round[] = [
  {
    id: 'r1', title: '第一轮', subtitle: '', status: 'done',
    transitionedAt: 1,
    tasks: [{
      id: 'r1:market_analyst:', agent: 'market_analyst', round: 'r1', status: 'done',
      startedAt: 1, endedAt: 2, events: [],
      output_summary: { tam: 100 },
    }],
  },
  { id: 'r2', title: '第二轮', subtitle: '', status: 'running', transitionedAt: 3, tasks: [] },
  { id: 'r3', title: '第三轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
]

describe('CollaborationTimeline', () => {
  it('renders three round headers', () => {
    render(<CollaborationTimeline rounds={rounds} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('第一轮')).toBeInTheDocument()
    expect(screen.getByText('第二轮')).toBeInTheDocument()
    expect(screen.getByText('第三轮')).toBeInTheDocument()
  })

  it('expands done and running rounds by default; collapses pending', () => {
    render(<CollaborationTimeline rounds={rounds} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()       // r1 expanded
    expect(screen.queryByText('战略顾问')).not.toBeInTheDocument()   // r3 collapsed (no tasks rendered)
  })

  it('forces failed round expanded and disables collapse', () => {
    const failed: Round[] = [{ ...rounds[0], status: 'failed' }]
    render(<CollaborationTimeline rounds={failed} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()
  })

  it('renders R2 task twice (A and B sub-rounds) for same agent', () => {
    const r2Rounds: Round[] = [{
      id: 'r2', title: '第二轮', subtitle: '', status: 'running', transitionedAt: 1,
      tasks: [
        { id: 'r2:market_analyst:A', agent: 'market_analyst', round: 'r2', subRound: 'A', status: 'done', startedAt: 1, endedAt: 2, events: [] },
        { id: 'r2:market_analyst:B', agent: 'market_analyst', round: 'r2', subRound: 'B', status: 'running', startedAt: 3, endedAt: null, events: [] },
      ],
    }]
    render(<CollaborationTimeline rounds={r2Rounds} selected={null} onSelect={() => {}} />)
    expect(screen.getAllByText('市场分析师')).toHaveLength(2)
    expect(screen.getByText('R2-A')).toBeInTheDocument()
    expect(screen.getByText('R2-B')).toBeInTheDocument()
  })

  it('renders empty state when all rounds are empty', () => {
    const empty: Round[] = [
      { id: 'r1', title: '第一轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
      { id: 'r2', title: '第二轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
      { id: 'r3', title: '第三轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
    ]
    render(<CollaborationTimeline rounds={empty} selected={null} onSelect={() => {}} />)
    expect(screen.getByText(/战略顾问正在拆解任务/)).toBeInTheDocument()
  })
})
