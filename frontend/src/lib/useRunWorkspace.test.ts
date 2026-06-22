import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRunWorkspace } from './useRunWorkspace'
import type { RunEvent, RunInfo } from './types'

describe('useRunWorkspace', () => {
  it('defaults selection to strategy_advisor', () => {
    const { result } = renderHook(() => useRunWorkspace([], null, null))
    expect(result.current.selectedTarget).toEqual({ kind: 'agent', agent: 'strategy_advisor' })
  })

  it('dedupes synthetic restore events when real events arrive', () => {
    const synthetic: RunEvent[] = [
      { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 'synthetic' }, __synthetic__: true } as any,
    ]
    const { rerender, result } = renderHook(({ ev }: { ev: RunEvent[] }) => useRunWorkspace(ev, null, null), {
      initialProps: { ev: synthetic },
    })
    expect(result.current.state.progress.done).toBe(1)

    const real: RunEvent[] = [
      { type: 'run.start', run_id: 'r', startup_idea: 'x' } as any,
      { type: 'agent.start', agent: 'market_analyst', round: 'round1' } as any,
      { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 'real' } } as any,
    ]
    rerender({ ev: real })
    expect(result.current.state.progress.done).toBe(1)
    const market = result.current.state.rounds[0].tasks.find((t) => t.agent === 'market_analyst')
    expect(market?.events).toHaveLength(2)
  })

  it('switches selection via setSelectedTarget', () => {
    const { result } = renderHook(() => useRunWorkspace([], null, null))
    act(() => {
      result.current.setSelectedTarget({ kind: 'agent', agent: 'market_analyst' })
    })
    expect(result.current.selectedTarget).toEqual({ kind: 'agent', agent: 'market_analyst' })
  })

  it('restores done tasks from runInfo checkpoint when events is empty (stale / partial run)', () => {
    const runInfo: RunInfo = {
      run_id: 'stale-run',
      startup_idea: 'x',
      status: 'partial',
      created_at: null,
      completed_at: null,
      deliberation_state: {
        r1_outputs: { market_analyst: { tam: 100 }, competitor_researcher: {} },
        r1_completed_agents: ['market_analyst', 'competitor_researcher'],
      },
    }
    const { result } = renderHook(() => useRunWorkspace([], runInfo, null))
    const market = result.current.state.rounds[0].tasks.find((t) => t.agent === 'market_analyst')
    const competitor = result.current.state.rounds[0].tasks.find((t) => t.agent === 'competitor_researcher')
    expect(market?.status).toBe('done')
    expect(competitor?.status).toBe('done')
    // Finance has no R1 output so no task node is created for it.
    // Verify via the agent summary instead.
    const financeSummary = result.current.state.agents.find((a) => a.name === 'finance_analyst')
    expect(financeSummary?.status).toBe('pending')
    expect(financeSummary?.progress).toEqual({ done: 0, total: 3 })
    expect(result.current.state.progress.done).toBe(2)
  })

  it('falls back to all-pending when runInfo has no checkpoint and events is empty', () => {
    const { result } = renderHook(() => useRunWorkspace([], null, null))
    expect(result.current.state.status).toBe('pending')
    expect(result.current.state.progress.percent).toBe(0)
  })

  it('shows partial state when runInfo.status is partial', () => {
    const runInfo: RunInfo = {
      run_id: 'partial-run',
      startup_idea: 'x',
      status: 'partial',
      created_at: null,
      completed_at: null,
    }
    const { result } = renderHook(() => useRunWorkspace([], runInfo, null))
    // runInfo.status === 'complete' gates the 100% override; 'partial' should
    // not force 100%. Progress should reflect only checkpoint completion.
    expect(result.current.state.progress.percent).toBe(0)
  })
})
