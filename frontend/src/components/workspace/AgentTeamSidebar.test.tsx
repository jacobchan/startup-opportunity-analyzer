// frontend/src/components/workspace/AgentTeamSidebar.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AgentTeamSidebar } from './AgentTeamSidebar'
import type { AgentSummary } from '../../lib/workspace-types'

const agents: AgentSummary[] = [
  { name: 'strategy_advisor', label: '战略顾问', role: 'orchestrator', status: 'running', currentAction: '正在综合 R3 战略', progress: { done: 0, total: 1 } },
  { name: 'market_analyst', label: '市场分析师', role: 'analyst', status: 'done', currentAction: '已完成', progress: { done: 2, total: 3 } },
  { name: 'competitor_researcher', label: '竞品调研员', role: 'analyst', status: 'running', currentAction: '正在搜索', progress: { done: 1, total: 3 } },
  { name: 'finance_analyst', label: '财务分析师', role: 'analyst', status: 'waiting', currentAction: '等待依赖', progress: { done: 0, total: 3 } },
  { name: 'risk_reviewer', label: '风险评审员', role: 'analyst', status: 'failed', currentAction: '执行失败', progress: { done: 0, total: 1 } },
]

describe('AgentTeamSidebar', () => {
  it('renders Orchestrator card first, above other agents', () => {
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    const items = screen.getAllByRole('button')
    expect(items[0]).toHaveTextContent('战略顾问')
    expect(items[0]).toHaveTextContent(/Orchestrator/i)
  })

  it('renders the other 4 agents in fixed order after Orchestrator', () => {
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    const items = screen.getAllByRole('button')
    const labels = items.map((b) => b.textContent)
    expect(labels.findIndex((l) => l?.includes('市场分析师'))).toBeLessThan(labels.findIndex((l) => l?.includes('竞品调研员')))
    expect(labels.findIndex((l) => l?.includes('竞品调研员'))).toBeLessThan(labels.findIndex((l) => l?.includes('财务分析师')))
    expect(labels.findIndex((l) => l?.includes('财务分析师'))).toBeLessThan(labels.findIndex((l) => l?.includes('风险评审员')))
  })

  it('clicking an agent fires onSelect with that agent name', () => {
    const onSelect = vi.fn()
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('市场分析师'))
    expect(onSelect).toHaveBeenCalledWith({ kind: 'agent', agent: 'market_analyst' })
  })

  it('applies running-pulse class to running agents', () => {
    render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    // Orchestrator is running, competitor_researcher is running
    const pulses = document.querySelectorAll('.ws-dot--running')
    expect(pulses.length).toBeGreaterThanOrEqual(2)
  })

  it('shows failed left-bar on failed agent', () => {
    const { container } = render(<AgentTeamSidebar agents={agents} selected={null} onSelect={() => {}} />)
    expect(container.querySelector('.ws-agent-row--failed')).toBeTruthy()
  })
})
