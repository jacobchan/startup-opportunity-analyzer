import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

vi.mock('./lib/sse', () => ({
  subscribeToRun: vi.fn(() => vi.fn()),
}))

describe('App run restoration', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    vi.restoreAllMocks()
  })

  it('restores per-agent progress from the persisted deliberation checkpoint', async () => {
    window.history.replaceState({}, '', '/?run=run-in-progress')
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        run_id: 'run-in-progress',
        status: 'running',
        startup_idea: 'AI Agent 创业',
        round1_outputs: null,
        deliberation_state: {
          current_round: 'round1',
          r1_outputs: { market_analyst: { tam: '100亿' } },
          r1_completed_agents: ['market_analyst'],
        },
      }),
    }) as any

    render(<App />)

    await waitFor(() => {
      // New workspace mounts the sidebar which includes the agent label
      expect(screen.getAllByText('市场分析师').length).toBeGreaterThan(0)
    })
    // Workspace shell should be present (sidebar + timeline + inspector)
    expect(document.querySelector('.ws-shell')).toBeTruthy()
    expect(screen.queryByText('创业机会分析器')).not.toBeInTheDocument()
  })

  it('keeps the run URL and workspace visible when restoration is temporarily unavailable', async () => {
    window.history.replaceState({}, '', '/?run=run-in-progress')
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false }) as any

    render(<App />)

    await waitFor(() => expect(screen.getByText(/暂时无法恢复分析状态/)).toBeInTheDocument())
    expect(window.location.search).toBe('?run=run-in-progress')
  })
})
