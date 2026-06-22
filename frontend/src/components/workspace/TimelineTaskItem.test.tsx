// frontend/src/components/workspace/TimelineTaskItem.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TimelineTaskItem } from './TimelineTaskItem'
import type { AgentTask } from '../../lib/workspace-types'

function task(over: Partial<AgentTask>): AgentTask {
  return {
    id: 'r1:market_analyst:',
    agent: 'market_analyst',
    round: 'r1',
    status: 'running',
    startedAt: 1,
    endedAt: null,
    events: [],
    ...over,
  }
}

describe('TimelineTaskItem', () => {
  it('renders agent label, sub-round tag and status', () => {
    render(<TimelineTaskItem task={task({ subRound: 'B', status: 'done' })} roundId="r2" selected={null} onSelect={() => {}} />)
    expect(screen.getByText('市场分析师')).toBeInTheDocument()
    expect(screen.getByText(/R2-B/)).toBeInTheDocument()
  })

  it('shows expand button when task has output_summary', () => {
    render(<TimelineTaskItem task={task({ status: 'done', output_summary: { x: 1 } })} roundId="r1" selected={null} onSelect={() => {}} />)
    expect(screen.getByText(/展开产物/)).toBeInTheDocument()
  })

  it('does not show expand button when task has no output and no tool events', () => {
    render(<TimelineTaskItem task={task({ status: 'running' })} roundId="r1" selected={null} onSelect={() => {}} />)
    expect(screen.queryByText(/展开产物/)).not.toBeInTheDocument()
  })

  it('clicking expand toggles the artifact section', () => {
    render(<TimelineTaskItem task={task({ status: 'done', output_summary: { x: 1 } })} roundId="r1" selected={null} onSelect={() => {}} />)
    fireEvent.click(screen.getByText(/展开产物/))
    expect(screen.getByText(/时间线/)).toBeInTheDocument()
  })

  it('renders failed error text when status is failed', () => {
    render(<TimelineTaskItem task={task({ status: 'failed', error: 'timeout' })} roundId="r1" selected={null} onSelect={() => {}} />)
    expect(screen.getByText(/timeout/)).toBeInTheDocument()
  })
})
