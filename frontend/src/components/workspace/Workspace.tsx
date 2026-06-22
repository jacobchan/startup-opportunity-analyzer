// frontend/src/components/workspace/Workspace.tsx
import './workspace.css'
import { useRunWorkspace } from '../../lib/useRunWorkspace'
import type { RunEvent, RunInfo } from '../../lib/types'
import { WorkspaceTopbar } from './WorkspaceTopbar'
import { AgentTeamSidebar } from './AgentTeamSidebar'
import { CollaborationTimeline } from './CollaborationTimeline'
import { DetailInspector } from './DetailInspector'

interface Props {
  events: RunEvent[]
  report: unknown
  errorMsg: string
  runInfo: RunInfo | null
  onBack: () => void
}

export function Workspace({ events, report, errorMsg, runInfo, onBack }: Props) {
  const { state, selectedTarget, setSelectedTarget } = useRunWorkspace(events, runInfo, report)

  return (
    <div className="ws-shell" style={{ position: 'relative' }}>
      <WorkspaceTopbar state={state} runInfo={runInfo} errorMsg={errorMsg} report={report} onBack={onBack} />
      <div className="ws-body">
        <AgentTeamSidebar agents={state.agents} selected={selectedTarget} onSelect={setSelectedTarget} />
        <CollaborationTimeline rounds={state.rounds} selected={selectedTarget} onSelect={setSelectedTarget} report={report} />
        <DetailInspector state={state} selected={selectedTarget} onSelect={setSelectedTarget} report={report} />
      </div>
    </div>
  )
}
