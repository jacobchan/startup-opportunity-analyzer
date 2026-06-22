// frontend/src/components/workspace/artifact-renderers.tsx
// STUB: Task 10 will replace this with full per-agent renderers.
import type { AgentName } from '../../lib/types'

interface Props {
  agent: AgentName
  output: unknown
}

export function ArtifactPreview({ agent, output }: Props) {
  return (
    <pre className="ws-mono" style={{ fontSize: 12, whiteSpace: 'pre-wrap' }} data-agent={agent}>
      {JSON.stringify(output, null, 2)}
    </pre>
  )
}
