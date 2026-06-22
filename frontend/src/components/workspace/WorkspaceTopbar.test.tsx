// frontend/src/components/workspace/WorkspaceTopbar.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { WorkspaceTopbar } from './WorkspaceTopbar'
import type { WorkspaceState } from '../../lib/workspace-types'

const baseState: WorkspaceState = {
  rounds: [], agents: [],
  progress: { done: 4, total: 11, percent: 36 },
  status: 'running',
}

describe('WorkspaceTopbar', () => {
  it('renders startup_idea as the task name', () => {
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'AI Agent 创业', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={() => {}} view="running" />)
    expect(screen.getByText('AI Agent 创业')).toBeInTheDocument()
  })

  it('shows progress percent', () => {
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={() => {}} view="running" />)
    expect(screen.getByText(/36%/)).toBeInTheDocument()
  })

  it('disables pause and terminate buttons', () => {
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={() => {}} view="running" />)
    expect(screen.getByRole('button', { name: /暂停/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /终止/ })).toBeDisabled()
  })

  it('enables export only when report is present', () => {
    const { rerender } = render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" report={null} onBack={() => {}} view="running" />)
    expect(screen.getByRole('button', { name: /导出/ })).toBeDisabled()
    rerender(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'complete', created_at: null, completed_at: null }} errorMsg="" report={{ decision: 'Go' }} onBack={() => {}} view="report" />)
    expect(screen.getByRole('button', { name: /导出/ })).not.toBeDisabled()
  })

  it('clicking back calls onBack', () => {
    const onBack = vi.fn()
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="" onBack={onBack} view="running" />)
    fireEvent.click(screen.getByRole('button', { name: /返回/ }))
    expect(onBack).toHaveBeenCalledOnce()
  })

  it('shows error message in failed state', () => {
    render(<WorkspaceTopbar state={{ ...baseState, status: 'failed' }} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'failed', created_at: null, completed_at: null }} errorMsg="网络中断" onBack={() => {}} view="failed" />)
    expect(screen.getByText(/网络中断/)).toBeInTheDocument()
  })

  it('does NOT show error banner in running view even if errorMsg is set', () => {
    render(<WorkspaceTopbar state={baseState} runInfo={{ run_id: 'r', startup_idea: 'x', status: 'running', created_at: null, completed_at: null }} errorMsg="transient" onBack={() => {}} view="running" />)
    expect(screen.queryByText(/transient/)).not.toBeInTheDocument()
  })
})
