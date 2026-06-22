// frontend/src/lib/useRunWorkspace.ts
import { useMemo, useState } from 'react'
import type { RunEvent, RunInfo, AgentName } from './types'
import { buildWorkspace } from './buildWorkspace'
import type { WorkspaceState, SelectedTarget } from './workspace-types'

/**
 * Build synthetic events for an in-progress restore, mirroring the logic
 * originally in App.tsx (buildEventsFromR1Outputs). Prefer the live
 * checkpoint (deliberation_state.r1_outputs) over the legacy snapshot.
 *
 * For each persisted R1 output we emit a matched pair of synthetic
 * `agent.start` + `agent.end` events so `buildWorkspace` opens the task
 * before closing it (a bare `agent.end` would be ignored).
 *
 * Each synthetic event is tagged with `__synthetic__: true` so the dedupe
 * pass in `useRunWorkspace` can drop it once real stream events arrive.
 */
export function synthesizeFromCheckpoint(runInfo: RunInfo | null): RunEvent[] {
  if (!runInfo) return []
  const outputs = runInfo.deliberation_state?.r1_outputs ?? runInfo.round1_outputs ?? null
  if (!outputs || typeof outputs !== 'object') return []
  const events: RunEvent[] = []
  for (const [agent, output] of Object.entries(outputs as Record<string, unknown>)) {
    events.push({
      type: 'agent.start',
      agent: agent as AgentName,
      round: 'round1',
      __synthetic__: true,
    } as RunEvent)
    events.push({
      type: 'agent.end',
      agent: agent as AgentName,
      round: 'round1',
      output_summary: output,
      __synthetic__: true,
    } as RunEvent)
  }
  return events
}

/**
 * Detect whether the current event stream looks like the synthetic restore
 * stream (only agent.end events, no run.start / agent.start). When the real
 * SSE stream arrives, it always contains at least one run.start, so this
 * becomes our "real" signal.
 */
function isSyntheticOnly(events: RunEvent[]): boolean {
  if (events.length === 0) return false
  return events.every((e) => e.type === 'agent.end')
}

/**
 * Detect a synthetic-tagged event. Synthetic events are tagged with a
 * non-standard `__synthetic__` marker so we can tell them apart from real
 * agent.end events once both are present.
 */
function isFromSynthetic(ev: RunEvent): boolean {
  return Boolean((ev as any).__synthetic__)
}

/**
 * `buildWorkspace` ignores a bare `agent.end` that has no preceding
 * `agent.start`. Synthetic restore events (whether produced by
 * `synthesizeFromCheckpoint` or passed in directly by callers replaying a
 * checkpoint) carry only the `agent.end` half. Pair each one with a
 * matching synthetic `agent.start` so the workspace counts the task as
 * done. The `__synthetic__` marker is preserved so the dedupe pass can
 * still drop these events later.
 */
function pairSyntheticStarts(events: RunEvent[]): RunEvent[] {
  const out: RunEvent[] = []
  for (const ev of events) {
    if (ev.type === 'agent.end') {
      out.push({
        type: 'agent.start',
        agent: (ev as any).agent as AgentName,
        round: (ev as any).round ?? 'round1',
        __synthetic__: true,
      } as RunEvent)
    }
    out.push(ev)
  }
  return out
}

export interface UseRunWorkspaceResult {
  state: WorkspaceState
  selectedTarget: SelectedTarget
  setSelectedTarget: (t: SelectedTarget) => void
}

export function useRunWorkspace(
  events: RunEvent[],
  runInfo: RunInfo | null,
  report: unknown,
): UseRunWorkspaceResult {
  const [selectedTarget, setSelectedTarget] = useState<SelectedTarget>({
    kind: 'agent',
    agent: 'strategy_advisor',
  })

  const state = useMemo<WorkspaceState>(() => {
    // "Real signal" = the incoming stream contains at least one event that
    // is neither a synthetic-tagged event nor an agent.end. The real SSE
    // stream always begins with run.start, so this becomes our transition
    // signal from the synthetic restore stream to the live stream.
    const hasRealSignal = events.some((e) => !isFromSynthetic(e) && e.type !== 'agent.end')

    // Always seed from the persisted checkpoint so a stale or partial run
    // (where the SSE stream never delivers new events) still shows the
    // already-completed work. Real events override synth on a per-event
    // basis via the `__synthetic__` tag below.
    const synth = synthesizeFromCheckpoint(runInfo)

    let merged: RunEvent[]
    if (hasRealSignal) {
      // Real stream has arrived. Drop every synthetic event so the live
      // stream fully replaces the synthetic preview.
      merged = events.filter((e) => !isFromSynthetic(e))
    } else if (events.length === 0) {
      // No SSE events yet (initial restore with empty events array).
      // Seed entirely from the checkpoint.
      merged = synth
    } else if (isSyntheticOnly(events)) {
      // Caller passed a partial synthetic fragment — prefer the canonical
      // checkpoint-derived stream.
      merged = synth.length > 0 ? synth : events
    } else {
      // Caller passed real events but none triggered hasRealSignal yet
      // (e.g., a single agent.end from a real replay). Use the events as-is.
      merged = events
    }

    let filtered: RunEvent[]
    if (hasRealSignal) {
      filtered = merged
    } else if (merged === synth) {
      // synthesizeFromCheckpoint emits matched start+end pairs, so no
      // additional pairing is needed. Calling pairSyntheticStarts here
      // would inject duplicate start events and create orphan running
      // tasks for every agent.
      filtered = merged
    } else {
      // Caller passed partial events (e.g. legacy `agent.end` only).
      // Pair each bare agent.end with a synthetic agent.start so
      // buildWorkspace opens the task before closing it.
      filtered = pairSyntheticStarts(merged)
    }
    return buildWorkspace(filtered, runInfo, report)
  }, [events, runInfo, report])

  return { state, selectedTarget, setSelectedTarget }
}
