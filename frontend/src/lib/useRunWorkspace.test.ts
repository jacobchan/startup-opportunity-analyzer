import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRunWorkspace } from './useRunWorkspace'
import type { RunEvent } from './types'

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
    // First render: synthetic event counted
    expect(result.current.state.progress.done).toBe(1)

    const real: RunEvent[] = [
      { type: 'run.start', run_id: 'r', startup_idea: 'x' } as any,
      { type: 'agent.start', agent: 'market_analyst', round: 'round1' } as any,
      { type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 'real' } } as any,
    ]
    rerender({ ev: real })
    // Real events fully replace synthetic ones; same single agent done
    expect(result.current.state.progress.done).toBe(1)
    const market = result.current.state.rounds[0].tasks.find((t) => t.agent === 'market_analyst')
    expect(market?.events).toHaveLength(2) // start + end (synthetic gone)
  })

  it('switches selection via setSelectedTarget', () => {
    const { result } = renderHook(() => useRunWorkspace([], null, null))
    act(() => {
      result.current.setSelectedTarget({ kind: 'agent', agent: 'market_analyst' })
    })
    expect(result.current.selectedTarget).toEqual({ kind: 'agent', agent: 'market_analyst' })
  })
})
