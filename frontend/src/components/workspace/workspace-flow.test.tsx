// frontend/src/components/workspace/workspace-flow.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { Workspace } from './Workspace'
import type { RunEvent } from '../../lib/types'

// A recorded-style event stream that walks through R1 partial → R2 → R3.
function buildFlow(): RunEvent[] {
  const ev: RunEvent[] = []
  ev.push({ type: 'run.start', run_id: 'r', startup_idea: 'AI Agent 创业方向' } as any)
  // R1: market + competitor + finance
  for (const a of ['market_analyst', 'competitor_researcher', 'finance_analyst'] as const) {
    ev.push({ type: 'agent.start', agent: a, round: 'round1' } as any)
    ev.push({ type: 'tool.start', agent: a, tool: 'search', input_preview: 'AI Agent' } as any)
    ev.push({ type: 'tool.end', agent: a, tool: 'search', evidence_id: `ev-${a}`, output_preview: '' } as any)
    ev.push({ type: 'agent.end', agent: a, round: 'round1', output_summary: { tam: 100 } } as any)
  }
  // risk_reviewer (after first three)
  ev.push({ type: 'agent.start', agent: 'risk_reviewer', round: 'round1' } as any)
  ev.push({ type: 'agent.end', agent: 'risk_reviewer', round: 'round1', output_summary: { risks: [] } } as any)
  // R2 transition
  ev.push({ type: 'round.transition', from_round: 'round1', to_round: 'round2' } as any)
  // R2-A for market + competitor + finance
  for (const a of ['market_analyst', 'competitor_researcher', 'finance_analyst'] as const) {
    ev.push({ type: 'agent.start', agent: a, round: 'round2' } as any)
    ev.push({ type: 'challenge.issued', challenge_id: `c-${a}`, issuer: a, target: 'risk_reviewer', claim: '风险描述', reason: '理由' } as any)
    ev.push({ type: 'agent.end', agent: a, round: 'round2', output_summary: {} } as any)
  }
  // R2-B for the same three
  for (const a of ['market_analyst', 'competitor_researcher', 'finance_analyst'] as const) {
    ev.push({ type: 'agent.start', agent: a, round: 'round2' } as any)
    ev.push({ type: 'challenge.responded', challenge_id: `c-${a}`, target: a, response: '回应', verdict: 'accepted' } as any)
    ev.push({ type: 'agent.end', agent: a, round: 'round2', output_summary: {} } as any)
  }
  // R3
  ev.push({ type: 'round.transition', from_round: 'round2', to_round: 'round3' } as any)
  ev.push({ type: 'agent.start', agent: 'strategy_advisor', round: 'round3' } as any)
  ev.push({ type: 'agent.end', agent: 'strategy_advisor', round: 'round3', output_summary: {} } as any)
  ev.push({ type: 'run.complete', run_id: 'r', report: { decision: 'Go', executive_summary: '可行' } } as any)
  return ev
}

describe('Workspace flow', () => {
  it('progress reaches 100% and all rounds render when flow completes', () => {
    const events = buildFlow()
    let lastPercent = -1

    const { rerender } = render(
      <Workspace
        events={[]}
        report={null}
        errorMsg=""
        runInfo={{ run_id: 'r', startup_idea: 'AI Agent 创业方向', status: 'running', created_at: null, completed_at: null }}
        onBack={() => {}}
      />,
    )

    // Incrementally feed events to verify progress increases monotonically.
    for (let i = 1; i <= events.length; i++) {
      act(() => {
        rerender(
          <Workspace
            events={events.slice(0, i)}
            report={i === events.length ? { decision: 'Go' } : null}
            errorMsg=""
            runInfo={{ run_id: 'r', startup_idea: 'AI Agent 创业方向', status: i === events.length ? 'complete' : 'running', created_at: null, completed_at: null }}
            onBack={() => {}}
          />,
        )
      })
      const percentText = document.querySelector('.ws-mono.ws-faint')?.textContent ?? ''
      const m = percentText.match(/(\d+)%/)
      if (m) {
        const p = parseInt(m[1], 10)
        expect(p).toBeGreaterThanOrEqual(lastPercent)
        lastPercent = p
      }
    }

    // Final state: 100%
    expect(lastPercent).toBe(100)

    // Three round headers visible
    expect(screen.getByText(/第一轮/)).toBeInTheDocument()
    expect(screen.getByText(/第二轮/)).toBeInTheDocument()
    expect(screen.getByText(/第三轮/)).toBeInTheDocument()

    // R3 contains EvidenceReport (renders decision verdict)
    expect(screen.getAllByText('Go').length).toBeGreaterThan(0)
  })

  it('defaults selection to Orchestrator in the inspector', () => {
    render(
      <Workspace
        events={[]}
        report={null}
        errorMsg=""
        runInfo={null}
        onBack={() => {}}
      />,
    )
    // Right inspector shows Orchestrator label
    expect(document.querySelector('.ws-col-right')?.textContent).toMatch(/战略顾问/)
  })
})
