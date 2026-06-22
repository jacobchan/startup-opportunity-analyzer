// frontend/src/components/workspace/TimelineTaskItem.tsx
import './workspace.css'
import { useState } from 'react'
import { AGENT_LABELS, STATUS_LABEL } from '../../lib/workspace-constants'
import type { AgentTask, RoundId, SelectedTarget, TaskEventKind } from '../../lib/workspace-types'
import { ArtifactPreview } from './artifact-renderers'

interface Props {
  task: AgentTask
  roundId: RoundId
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
}

export function TimelineTaskItem({ task, onSelect }: Props) {
  const [expanded, setExpanded] = useState(false)
  const hasExpandable = task.output_summary != null || task.events.some((e) => e.kind === 'tool')

  const subRoundTag = task.subRound ? `R2-${task.subRound}` : `R${task.round.slice(1)}`
  const borderColor =
    task.status === 'running' ? 'var(--ws-status-running)'
    : task.status === 'done' ? 'var(--ws-status-done)'
    : task.status === 'failed' ? 'var(--ws-status-failed)'
    : task.status === 'waiting' ? 'var(--ws-status-waiting)'
    : 'transparent'

  return (
    <div className={`ws-task-item ${task.status === 'running' ? 'ws-task-item--running' : ''}`} style={{
      position: 'relative', padding: '12px 16px', borderBottom: '1px solid var(--ws-border)',
    }}>
      <span style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 2,
        background: borderColor,
      }} className={task.status === 'running' ? 'ws-bar--running' : ''} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`ws-dot ws-clr-${task.status} ${task.status === 'running' ? 'ws-dot--running' : ''} ${task.status === 'waiting' ? 'ws-dot--waiting' : ''}`} />
        <strong style={{ fontSize: 13 }}>{AGENT_LABELS[task.agent]}</strong>
        <span className="ws-faint" style={{ fontSize: 11 }}>{subRoundTag}</span>
        <div style={{ flex: 1 }} />
        <span className={`ws-pill ws-clr-${task.status}`} style={{ background: 'var(--ws-bg)' }}>
          <span className="ws-pill__dot" />
          {STATUS_LABEL[task.status]}
        </span>
      </div>

      <CurrentActionLine task={task} />

      {task.status === 'failed' && task.error && (
        <div className="ws-clr-failed" style={{ fontSize: 12, marginTop: 4 }}>{task.error}</div>
      )}

      <MetaLine task={task} />

      {hasExpandable && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="ws-faint"
          style={{ background: 'none', border: 0, padding: '4px 0', cursor: 'pointer', fontSize: 12 }}
        >
          {expanded ? '▾ 收起产物' : '▸ 展开产物'}
        </button>
      )}

      {expanded && hasExpandable && (
        <ExpandedSection task={task} onSelect={onSelect} />
      )}
    </div>
  )
}

function CurrentActionLine({ task }: { task: AgentTask }) {
  const text = describeAction(task)
  return (
    <div className="ws-muted" style={{ fontSize: 13, marginTop: 4 }}>
      {text}
    </div>
  )
}

function describeAction(task: AgentTask): string {
  if (task.status === 'failed') return '执行失败'
  if (task.status === 'done') return '已提交产物'
  if (task.status === 'pending') return '等待启动'
  if (task.status === 'waiting') return '等待前置任务完成'
  const last = task.events[task.events.length - 1]
  if (!last) return '开始分析'
  if (last.kind === 'tool' && last.payload.type === 'tool.start') {
    return `正在搜索：${String(last.payload.input_preview ?? '').slice(0, 40)}`
  }
  if (last.kind === 'tool' && last.payload.type === 'tool.end') {
    const ev = last.payload.evidence_id
    return ev ? `搜索完成 → ${ev}` : '搜索完成'
  }
  if (last.kind === 'challenge_issued') {
    return `向 ${AGENT_LABELS[last.payload.target as keyof typeof AGENT_LABELS] ?? last.payload.target} 发起挑战`
  }
  if (last.kind === 'challenge_responded') {
    return `回应挑战：${String(last.payload.response ?? '').slice(0, 40)}`
  }
  if (last.kind === 'message') {
    return String(last.payload.content_summary ?? '').slice(0, 60)
  }
  return '执行中'
}

function MetaLine({ task }: { task: AgentTask }) {
  const tools = task.events.filter((e) => e.kind === 'tool').length
  const challenges = task.events.filter((e) => e.kind === 'challenge_issued' || e.kind === 'challenge_responded').length
  return (
    <div className="ws-faint" style={{ fontSize: 12, marginTop: 4 }}>
      {tools} 条工具调用
      {challenges > 0 && <> · {challenges} 条挑战</>}
    </div>
  )
}

function ExpandedSection({ task, onSelect }: { task: AgentTask; onSelect: (t: SelectedTarget) => void }) {
  return (
    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--ws-border)' }}>
      <div className="ws-section-label" style={{ marginBottom: 8 }}>时间线</div>
      {task.events.map((ev) => (
        <EventRow key={ev.id} ev={ev} taskId={task.id} onSelect={onSelect} />
      ))}

      {task.output_summary != null && (
        <>
          <div className="ws-section-label" style={{ marginTop: 16, marginBottom: 8 }}>产物预览</div>
          <ArtifactPreview agent={task.agent} output={task.output_summary} />
          <CopyJsonButton data={task.output_summary} />
        </>
      )}
    </div>
  )
}

function EventRow({ ev, taskId, onSelect }: {
  ev: AgentTask['events'][number]
  taskId: string
  onSelect: (t: SelectedTarget) => void
}) {
  const time = formatTime(ev.timestamp)
  const text = eventRowText(ev.kind, ev.payload)
  const isTool = ev.kind === 'tool'
  return (
    <div style={{ display: 'flex', gap: 12, padding: '4px 0', fontSize: 12 }}>
      <span className="ws-mono ws-faint" style={{ flexShrink: 0, width: 48 }}>{time}</span>
      <button
        type="button"
        disabled={!isTool}
        onClick={() => isTool && onSelect({ kind: 'event', taskId, eventId: ev.id })}
        style={{
          background: 'none', border: 0, padding: 0, cursor: isTool ? 'pointer' : 'default',
          color: isTool ? 'var(--ws-text)' : 'var(--ws-text-muted)', textAlign: 'left', fontSize: 12,
        }}
      >
        {text}
      </button>
    </div>
  )
}

function eventRowText(kind: TaskEventKind, payload: Record<string, unknown>): string {
  switch (kind) {
    case 'start': return '开始分析'
    case 'tool': {
      if (payload.type === 'tool.start') {
        return `搜索：${String(payload.input_preview ?? '').slice(0, 40)}`
      }
      const ev = payload.evidence_id
      return `搜索完成 → ${ev ?? '无证据'}`
    }
    case 'message': return String(payload.content_summary ?? '').slice(0, 60)
    case 'challenge_issued':
      return `向 ${payload.target as string} 发起挑战：${String(payload.claim ?? '').slice(0, 40)}`
    case 'challenge_responded':
      return `回应 ${payload.issuer as string}：${String(payload.response ?? '').slice(0, 40)} [${payload.verdict as string}]`
    case 'end':
      return payload.error ? `失败：${payload.error}` : '提交产物'
  }
}

function formatTime(ts: number): string {
  // ts is a monotonic counter, not a real timestamp. Render as relative index.
  const minutes = Math.floor(ts / 60)
  const seconds = ts % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function CopyJsonButton({ data }: { data: unknown }) {
  return (
    <button
      type="button"
      onClick={() => navigator.clipboard?.writeText(JSON.stringify(data, null, 2))}
      className="ws-faint"
      style={{ marginTop: 8, background: 'none', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 12 }}
    >
      复制 JSON
    </button>
  )
}
