// frontend/src/components/workspace/DetailInspector.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { DetailInspector } from './DetailInspector'
import type { WorkspaceState, SelectedTarget } from '../../lib/workspace-types'

function stateOver(over: Partial<WorkspaceState>): WorkspaceState {
  return {
    rounds: [{
      id: 'r1', title: '第一轮', subtitle: '', status: 'done', transitionedAt: 1,
      tasks: [{
        id: 'r1:market_analyst:', agent: 'market_analyst', round: 'r1', status: 'done',
        startedAt: 1, endedAt: 2, events: [
          { id: 'r1:market_analyst:0', kind: 'start', timestamp: 1, agent: 'market_analyst', round: 'r1', payload: { type: 'agent.start' } },
          { id: 'r1:market_analyst:1', kind: 'tool', timestamp: 2, agent: 'market_analyst', round: 'r1', payload: { type: 'tool.start', tool: 'search', input_preview: 'AI Agent 市场' } },
          { id: 'r1:market_analyst:2', kind: 'tool', timestamp: 3, agent: 'market_analyst', round: 'r1', payload: { type: 'tool.end', tool: 'search', evidence_id: 'ev-3a2f', output_preview: '...' } },
          { id: 'r1:market_analyst:3', kind: 'end', timestamp: 4, agent: 'market_analyst', round: 'r1', payload: { type: 'agent.end', output_summary: { tam: 100, sam: 50, som: 10 } } },
        ],
        output_summary: { tam: 100, sam: 50, som: 10 },
      }],
    }, { id: 'r2', title: '第二轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] },
       { id: 'r3', title: '第三轮', subtitle: '', status: 'pending', transitionedAt: null, tasks: [] }],
    agents: [
      { name: 'strategy_advisor', label: '战略顾问', role: 'orchestrator', status: 'waiting', currentAction: '等待 R1/R2 完成', progress: { done: 0, total: 1 } },
    ],
    progress: { done: 1, total: 11, percent: 9 },
    status: 'running',
    ...over,
  }
}

describe('DetailInspector', () => {
  beforeEach(() => {
    // Stub fetch to avoid jsdom network errors during EventPanel evidence lookup.
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        evidence_id: 'ev-3a2f',
        title: 'ev-3a2f',
        url: null,
        content_excerpt: '',
      }),
    } as unknown as Response)))
  })

  it('defaults to Orchestrator agent panel when selection is null', () => {
    render(<DetailInspector state={stateOver({})} selected={null} onSelect={() => {}} />)
    expect(screen.getByText('战略顾问')).toBeInTheDocument()
    expect(screen.getByText(/Orchestrator/i)).toBeInTheDocument()
  })

  it('renders event panel when an event is selected', async () => {
    const selected: SelectedTarget = { kind: 'event', taskId: 'r1:market_analyst:', eventId: 'r1:market_analyst:2' }
    render(<DetailInspector state={stateOver({})} selected={selected} onSelect={() => {}} />)
    expect(screen.getByText(/工具调用/)).toBeInTheDocument()
    expect(screen.getByText('search')).toBeInTheDocument()
    await waitFor(() => { expect(screen.getByText(/ev-3a2f/)).toBeInTheDocument() })
  })

  it('renders artifact panel with market analyst renderer', () => {
    const selected: SelectedTarget = { kind: 'artifact', taskId: 'r1:market_analyst:' }
    render(<DetailInspector state={stateOver({})} selected={selected} onSelect={() => {}} />)
    expect(screen.getByText(/TAM/)).toBeInTheDocument()
    expect(screen.getByText(/100/)).toBeInTheDocument()
  })

  it('shows JSON fallback when output_summary has unknown shape', () => {
    const state = stateOver({})
    state.rounds[0].tasks[0].agent = 'risk_reviewer'
    state.rounds[0].tasks[0].output_summary = { weird: 'data' }
    const selected: SelectedTarget = { kind: 'artifact', taskId: 'r1:market_analyst:' }
    const { container } = render(<DetailInspector state={state} selected={selected} onSelect={() => {}} />)
    expect(container.textContent).toMatch(/weird/)
  })

  it('shows disabled send-instruction button in agent panel', () => {
    render(<DetailInspector state={stateOver({})} selected={{ kind: 'agent', agent: 'strategy_advisor' }} onSelect={() => {}} />)
    const btn = screen.getByRole('button', { name: /发送/ })
    expect(btn).toBeDisabled()
  })
})
