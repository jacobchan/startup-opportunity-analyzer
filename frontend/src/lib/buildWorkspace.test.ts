import { describe, it, expect } from 'vitest'
import { buildWorkspace } from './buildWorkspace'
import type { RunEvent } from './types'

// Helper cast for partial event objects in edge-case tests (added below).
function ev(partial: any): RunEvent {
  return partial as RunEvent
}

describe('buildWorkspace', () => {
  it('returns all-pending state for empty events', () => {
    const state = buildWorkspace([], { run_id: 'r1', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }, null)
    expect(state.status).toBe('pending')
    expect(state.progress).toEqual({ done: 0, total: 11, percent: 0 })
    expect(state.rounds).toHaveLength(3)
    expect(state.rounds[0].status).toBe('pending')
    expect(state.agents.every((a) => a.status === 'pending')).toBe(true)
    expect(state.agents.find((a) => a.name === 'strategy_advisor')?.role).toBe('orchestrator')
  })

  it('marks r1 as running when run.start fires', () => {
    const events: RunEvent[] = [
      { type: 'run.start', run_id: 'r1', startup_idea: 'x' },
    ]
    const state = buildWorkspace(events, null, null)
    expect(state.rounds[0].status).toBe('running')
    expect(state.status).toBe('running')
  })
})

describe('buildWorkspace edge cases', () => {
  it('infers risk_reviewer waiting when first three R1 tasks done', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { tam: 1 } }),
      ev({ type: 'agent.start', agent: 'competitor_researcher', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'competitor_researcher', round: 'round1', output_summary: {} }),
      ev({ type: 'agent.start', agent: 'finance_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'finance_analyst', round: 'round1', output_summary: {} }),
    ]
    const state = buildWorkspace(events, null, null)
    const risk = state.rounds[0].tasks.find((t) => t.agent === 'risk_reviewer')
    expect(risk?.status).toBe('waiting')
    const riskSummary = state.agents.find((a) => a.name === 'risk_reviewer')
    expect(riskSummary?.status).toBe('waiting')
  })

  it('routes R2 second agent.start to a new R2-B task', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'round.transition', from_round: 'round1', to_round: 'round2' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round2', output_summary: {} }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
    ]
    const state = buildWorkspace(events, null, null)
    const marketR2 = state.rounds[1].tasks.filter((t) => t.agent === 'market_analyst')
    expect(marketR2).toHaveLength(2)
    expect(marketR2[0].subRound).toBe('A')
    expect(marketR2[0].status).toBe('done')
    expect(marketR2[1].subRound).toBe('B')
    expect(marketR2[1].status).toBe('running')
  })

  it('marks task failed when output_summary has error', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: { error: 'timeout' } }),
    ]
    const state = buildWorkspace(events, null, null)
    const t = state.rounds[0].tasks.find((x) => x.agent === 'market_analyst')
    expect(t?.status).toBe('failed')
    expect(t?.error).toBe('timeout')
  })

  it('does NOT attribute run.failed to agent when name not present in error text', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'run.failed', run_id: 'r', error: 'network error', partial: false }),
    ]
    const state = buildWorkspace(events, null, null)
    const t = state.rounds[0].tasks.find((x) => x.agent === 'market_analyst')
    // task is still running because attribution didn't fire; round status reflects run failure via global state
    expect(t?.status).toBe('running')
  })

  it('attributes run.failed to agent on exact token match', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'run.failed', run_id: 'r', error: 'market_analyst crashed mid-call', partial: false }),
    ]
    const state = buildWorkspace(events, null, null)
    const t = state.rounds[0].tasks.find((x) => x.agent === 'market_analyst')
    expect(t?.status).toBe('failed')
  })

  it('forces 100% progress when runInfo.status is complete even if tasks under-counted', () => {
    const events: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round1' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round1', output_summary: {} }),
    ]
    const state = buildWorkspace(events, { run_id: 'r', startup_idea: 'x', status: 'complete', created_at: null, completed_at: null }, null)
    expect(state.progress.percent).toBe(100)
    expect(state.status).toBe('done')
  })

  it('routes challenge.responded to R2-B when present, falls back to R2-A', () => {
    const eventsWithR2B: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'round.transition', from_round: 'round1', to_round: 'round2' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'agent.end', agent: 'market_analyst', round: 'round2', output_summary: {} }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'challenge.responded', challenge_id: 'c1', target: 'market_analyst', response: 'ok', verdict: 'accepted' }),
    ]
    const s1 = buildWorkspace(eventsWithR2B, null, null)
    const r2b = s1.rounds[1].tasks.find((t) => t.agent === 'market_analyst' && t.subRound === 'B')!
    expect(r2b.events.some((e) => e.kind === 'challenge_responded')).toBe(true)

    const eventsWithoutR2B: RunEvent[] = [
      ev({ type: 'run.start', run_id: 'r', startup_idea: 'x' }),
      ev({ type: 'round.transition', from_round: 'round1', to_round: 'round2' }),
      ev({ type: 'agent.start', agent: 'market_analyst', round: 'round2' }),
      ev({ type: 'challenge.responded', challenge_id: 'c1', target: 'market_analyst', response: 'ok', verdict: 'accepted' }),
    ]
    const s2 = buildWorkspace(eventsWithoutR2B, null, null)
    const r2a = s2.rounds[1].tasks.find((t) => t.agent === 'market_analyst' && t.subRound === 'A')!
    expect(r2a.events.some((e) => e.kind === 'challenge_responded')).toBe(true)
  })
})
