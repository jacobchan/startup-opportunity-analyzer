import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import HistoryList from './HistoryList'

const mockRuns = [
  {
    run_id: 'r1',
    startup_idea: 'AI Agent 平台',
    status: 'complete',
    decision: 'Go',
    executive_summary: '市场好',
    created_at: new Date().toISOString(),
    completed_at: null,
  },
  {
    run_id: 'r2',
    startup_idea: '跨境电商工具',
    status: 'running',
    decision: null,
    executive_summary: null,
    created_at: new Date().toISOString(),
    completed_at: null,
  },
]

describe('HistoryList', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ runs: mockRuns, total: 15 }),
    }) as any
  })

  it('renders runs from API', async () => {
    render(<HistoryList onRerun={vi.fn()} onViewRun={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(/AI Agent/)).toBeInTheDocument()
      expect(screen.getByText(/跨境电商/)).toBeInTheDocument()
    })
  })

  it('shows empty state when no runs', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ runs: [], total: 0 }),
    }) as any
    render(<HistoryList onRerun={vi.fn()} onViewRun={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(/暂无历史记录/)).toBeInTheDocument()
    })
  })

  it('calls onRerun with startup idea', async () => {
    const onRerun = vi.fn()
    render(<HistoryList onRerun={onRerun} onViewRun={vi.fn()} />)
    await waitFor(() => screen.getByText(/AI Agent/))
    fireEvent.click(screen.getAllByText('重跑')[0])
    expect(onRerun).toHaveBeenCalledWith('AI Agent 平台')
  })

  it('calls onViewRun with run_id on card click', async () => {
    const onViewRun = vi.fn()
    render(<HistoryList onRerun={vi.fn()} onViewRun={onViewRun} />)
    await waitFor(() => screen.getByText(/AI Agent/))
    fireEvent.click(screen.getByText(/AI Agent/))
    expect(onViewRun).toHaveBeenCalledWith('r1')
  })

  it('shows load more button when more runs available', async () => {
    render(<HistoryList onRerun={vi.fn()} onViewRun={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(/查看更多/)).toBeInTheDocument()
    })
  })
})
