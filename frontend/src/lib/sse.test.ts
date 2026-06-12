import { describe, it, expect, vi } from 'vitest'
import { subscribeToRun } from './sse'

describe('subscribeToRun', () => {
  it('opens EventSource to correct URL', () => {
    const close = vi.fn()
    const addEventListener = vi.fn()
    const Ctor = vi.fn().mockImplementation(() => ({
      close,
      addEventListener,
      removeEventListener: vi.fn(),
      onerror: null as any,
    }))
    vi.stubGlobal('EventSource', Ctor)

    subscribeToRun('run-123', () => {})
    expect(Ctor).toHaveBeenCalledWith('/runs/run-123/stream')
  })

  it('cleanup closes EventSource', () => {
    const close = vi.fn()
    const addEventListener = vi.fn()
    const Ctor = vi.fn().mockImplementation(() => ({
      close,
      addEventListener,
      removeEventListener: vi.fn(),
      onerror: null as any,
    }))
    vi.stubGlobal('EventSource', Ctor)

    const cleanup = subscribeToRun('run-1', () => {})
    cleanup()
    expect(close).toHaveBeenCalled()
  })
})
