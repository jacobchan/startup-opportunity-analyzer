import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import HistoryCard from './HistoryCard'

const completeRun = {
  run_id: 'run-1',
  startup_idea: 'AI Agent 客服平台',
  status: 'complete',
  decision: 'Go',
  executive_summary: '市场空间充足',
  created_at: new Date().toISOString(),
  completed_at: null,
}

const runningRun = {
  run_id: 'run-2',
  startup_idea: '跨境电商选品工具',
  status: 'running',
  decision: null,
  executive_summary: null,
  created_at: new Date().toISOString(),
  completed_at: null,
}

describe('HistoryCard', () => {
  it('renders startup idea', () => {
    render(
      <HistoryCard
        run={completeRun}
        onRerun={vi.fn()}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    expect(screen.getByText(/AI Agent/)).toBeInTheDocument()
  })

  it('shows decision badge for complete runs', () => {
    render(
      <HistoryCard
        run={completeRun}
        onRerun={vi.fn()}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    expect(screen.getByText('Go')).toBeInTheDocument()
  })

  it('shows running status for non-complete runs', () => {
    render(
      <HistoryCard
        run={runningRun}
        onRerun={vi.fn()}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    const badges = screen.getAllByText(/进行中/)
    expect(badges.length).toBeGreaterThanOrEqual(1)
  })

  it('calls onRerun when re-run button clicked', () => {
    const onRerun = vi.fn()
    render(
      <HistoryCard
        run={completeRun}
        onRerun={onRerun}
        onDelete={vi.fn()}
        onClick={vi.fn()}
      />
    )
    fireEvent.click(screen.getByText('重跑'))
    expect(onRerun).toHaveBeenCalledWith('AI Agent 客服平台')
  })

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn()
    render(
      <HistoryCard
        run={completeRun}
        onRerun={vi.fn()}
        onDelete={onDelete}
        onClick={vi.fn()}
      />
    )
    fireEvent.click(screen.getByText('删除'))
    expect(onDelete).toHaveBeenCalledWith('run-1')
  })
})
