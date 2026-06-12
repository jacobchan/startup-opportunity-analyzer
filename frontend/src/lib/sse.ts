import type { RunEvent } from './types'

export type EventHandler = (event: RunEvent) => void

export function subscribeToRun(runId: string, onEvent: EventHandler, onError?: (e: Error) => void): () => void {
  const url = `/runs/${runId}/stream`
  const es = new EventSource(url)

  const handler = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data) as RunEvent
      onEvent(data)
    } catch (err) {
      onError?.(err as Error)
    }
  }

  const eventNames = [
    'run.start', 'round.transition', 'agent.start', 'agent.message', 'agent.end',
    'tool.start', 'tool.end', 'challenge.issued', 'challenge.responded',
    'run.complete', 'run.failed',
  ]
  for (const name of eventNames) {
    es.addEventListener(name, handler as EventListener)
  }

  return () => {
    for (const name of eventNames) {
      es.removeEventListener(name, handler as EventListener)
    }
    es.close()
  }
}
