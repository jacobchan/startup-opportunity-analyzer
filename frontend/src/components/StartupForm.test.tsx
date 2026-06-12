import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StartupForm from './StartupForm'

describe('StartupForm', () => {
  it('calls onSubmit with trimmed idea on submit', () => {
    const onSubmit = vi.fn()
    render(<StartupForm onSubmit={onSubmit} loading={false} />)
    fireEvent.change(screen.getByPlaceholderText(/描述你的创业方向/), {
      target: { value: '  AI Agent 平台  ' },
    })
    fireEvent.click(screen.getByText('开始分析'))
    expect(onSubmit).toHaveBeenCalledWith('AI Agent 平台')
  })

  it('disables button when loading', () => {
    render(<StartupForm onSubmit={vi.fn()} loading={true} />)
    expect(screen.getByText('分析中...')).toBeDisabled()
  })

  it('does not call onSubmit with empty idea', () => {
    const onSubmit = vi.fn()
    render(<StartupForm onSubmit={onSubmit} loading={false} />)
    fireEvent.click(screen.getByText('开始分析'))
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
