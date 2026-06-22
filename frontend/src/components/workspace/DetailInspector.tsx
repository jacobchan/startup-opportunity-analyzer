// frontend/src/components/workspace/DetailInspector.tsx
import './workspace.css'
import { useEffect, useState } from 'react'
import { AGENT_LABELS, STATUS_LABEL } from '../../lib/workspace-constants'
import type { WorkspaceState, SelectedTarget, AgentTask, AgentTaskEvent } from '../../lib/workspace-types'
import type { AgentName } from '../../lib/types'
import EvidenceReport from '../EvidenceReport'
import { ArtifactPreview } from './artifact-renderers'

interface Props {
  state: WorkspaceState
  selected: SelectedTarget
  onSelect: (t: SelectedTarget) => void
  report?: unknown
}

export function DetailInspector({ state, selected, onSelect, report }: Props) {
  const target = selected ?? { kind: 'agent' as const, agent: 'strategy_advisor' as const }

  return (
    <aside className="ws-col-right">
      <div className="ws-scroll" style={{ padding: '20px 24px' }}>
        {target.kind === 'agent' && <AgentPanel name={target.agent} state={state} />}
        {target.kind === 'event' && (
          <EventPanel state={state} taskId={target.taskId} eventId={target.eventId} onSelect={onSelect} />
        )}
        {target.kind === 'artifact' && (
          <ArtifactPanel state={state} taskId={target.taskId} report={report} />
        )}
      </div>
    </aside>
  )
}

function AgentPanel({ name, state }: { name: AgentName; state: WorkspaceState }) {
  const summary = state.agents.find((a) => a.name === name)
  const tasksForAgent: AgentTask[] = []
  for (const r of state.rounds) for (const t of r.tasks) if (t.agent === name) tasksForAgent.push(t)
  if (!summary) return <div className="ws-muted">无 Agent 信息</div>

  return (
    <div>
      <div className={`ws-clr-${summary.status}`} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`ws-dot ws-dot--lg ${summary.status === 'running' ? 'ws-dot--running' : ''} ${summary.status === 'waiting' ? 'ws-dot--waiting' : ''}`} />
        <strong style={{ fontSize: 14 }}>{summary.label}</strong>
      </div>
      <div className="ws-faint" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>
        {summary.role === 'orchestrator' ? 'Orchestrator' : 'Analyst'}
      </div>

      <Section label="状态">
        <span className={`ws-clr-${summary.status}`}>{STATUS_LABEL[summary.status]}</span>
      </Section>

      <Section label="当前动作">
        <span className="ws-muted">{summary.currentAction}</span>
      </Section>

      {tasksForAgent.length > 0 && (
        <Section label="跨轮任务">
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12 }}>
            {tasksForAgent.map((t) => (
              <li key={t.id} className={`ws-clr-${t.status}`}>
                {t.subRound ? `R2-${t.subRound}` : `R${t.round.slice(1)}`} · {STATUS_LABEL[t.status]}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="ws-divider" />

      <Section label="补充指令">
        <textarea
          placeholder="给该 Agent 追加一段提示…"
          style={{ width: '100%', minHeight: 64, padding: 8, border: '1px solid var(--ws-border)', borderRadius: 6, fontSize: 12, resize: 'vertical' }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
          <button
            type="button"
            disabled
            title="运行中追加指令将在下一版支持"
            style={{ background: 'transparent', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '4px 12px', fontSize: 12, cursor: 'not-allowed', opacity: 0.45 }}
          >
            发送
          </button>
        </div>
        <p className="ws-faint" style={{ fontSize: 11, marginTop: 8 }}>
          本期版本不支持运行中追加指令，将在下一版接入。
        </p>
      </Section>
    </div>
  )
}

function EventPanel({ state, taskId, eventId, onSelect }: {
  state: WorkspaceState
  taskId: string
  eventId: string
  onSelect: (t: SelectedTarget) => void
}) {
  const task = findTask(state, taskId)
  const ev = task?.events.find((e) => e.id === eventId)
  if (!task || !ev) return <div className="ws-muted">事件不存在</div>
  return <EventPanelInner task={task} ev={ev} onSelect={onSelect} />
}

function EventPanelInner({ task, ev, onSelect }: {
  task: AgentTask
  ev: AgentTaskEvent
  onSelect: (t: SelectedTarget) => void
}) {
  const payload = ev.payload as Record<string, unknown>
  const agentLabel = AGENT_LABELS[ev.agent]
  const evidenceId = payload.evidence_id as string | undefined

  const [evidence, setEvidence] = useState<Record<string, unknown> | null>(null)
  useEffect(() => {
    if (!evidenceId) return
    let cancelled = false
    fetch(`/evidence/${evidenceId}`).then((r) => r.json()).then((d) => {
      if (!cancelled) setEvidence(d)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [evidenceId])

  return (
    <div>
      <button
        type="button"
        onClick={() => onSelect({ kind: 'agent', agent: ev.agent })}
        className="ws-faint"
        style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', fontSize: 12, marginBottom: 12 }}
      >
        ← 返回 {agentLabel} 详情
      </button>

      <Section label="事件类型">
        <span className="ws-muted">{ev.kind === 'tool' ? '工具调用' : ev.kind === 'challenge_issued' ? '发起挑战' : ev.kind === 'challenge_responded' ? '回应挑战' : ev.kind === 'message' ? '中间思考' : ev.kind === 'start' ? '任务开始' : '任务结束'}</span>
      </Section>

      <Section label="Agent / 时间">
        <span className="ws-muted">{agentLabel}</span>
      </Section>

      {ev.kind === 'tool' && (
        <>
          <Section label="工具">
            <code className="ws-mono">{String(payload.tool ?? '')}</code>
          </Section>
          <Section label="输入预览">
            <pre className="ws-mono ws-muted" style={{ fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}>{String(payload.input_preview ?? '')}</pre>
          </Section>
          {payload.type === 'tool.end' && (
            <Section label="输出预览">
              <pre className="ws-mono ws-muted" style={{ fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}>{String(payload.output_preview ?? '')}</pre>
            </Section>
          )}
          {evidenceId && (
            <Section label="引用证据">
              {evidence ? (
                <div style={{ background: 'var(--ws-bg)', padding: 8, borderRadius: 6 }}>
                  <div style={{ fontSize: 12, fontWeight: 600 }}>{String(evidence.title ?? evidenceId)}</div>
                  {Boolean(evidence.url) && <a href={String(evidence.url)} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>{String(evidence.url)}</a>}
                  <pre className="ws-muted ws-mono" style={{ fontSize: 11, marginTop: 6, whiteSpace: 'pre-wrap' }}>{String(evidence.content_excerpt ?? '').slice(0, 400)}</pre>
                </div>
              ) : <span className="ws-faint">{evidenceId} · 加载中…</span>}
            </Section>
          )}
        </>
      )}

      <Section label="所属任务">
        <button
          type="button"
          onClick={() => onSelect({ kind: 'artifact', taskId: task.id })}
          className="ws-clr-running"
          style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer', fontSize: 12 }}
        >
          {agentLabel} · R{task.round.slice(1)}{task.subRound ? `-${task.subRound}` : ''} →
        </button>
      </Section>
    </div>
  )
}

function ArtifactPanel({ state, taskId, report }: {
  state: WorkspaceState
  taskId: string
  report?: unknown
}) {
  const task = findTask(state, taskId)
  if (!task) return <div className="ws-muted">任务不存在</div>

  const isR3Strategy = task.agent === 'strategy_advisor' && task.round === 'r3'
  return (
    <div>
      <Section label="任务产物">
        <strong style={{ fontSize: 13 }}>{AGENT_LABELS[task.agent]}</strong>
        <span className="ws-faint" style={{ marginLeft: 8, fontSize: 11 }}>
          R{task.round.slice(1)}{task.subRound ? `-${task.subRound}` : ''}
        </span>
      </Section>

      {isR3Strategy && report ? (
        <EvidenceReport report={report} />
      ) : (
        <ArtifactPreview agent={task.agent} output={task.output_summary} />
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button
          type="button"
          onClick={() => navigator.clipboard?.writeText(JSON.stringify(task.output_summary, null, 2))}
          style={{ flex: 1, background: 'transparent', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '6px', fontSize: 12, cursor: 'pointer' }}
        >
          复制 JSON
        </button>
        <button
          type="button"
          disabled
          title="重试任务将在下一版支持"
          style={{ flex: 1, background: 'transparent', border: '1px solid var(--ws-border)', borderRadius: 6, padding: '6px', fontSize: 12, cursor: 'not-allowed', opacity: 0.45 }}
        >
          重试任务
        </button>
      </div>
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 16 }}>
      <div className="ws-section-label" style={{ marginBottom: 6 }}>{label}</div>
      <div>{children}</div>
    </div>
  )
}

function findTask(state: WorkspaceState, taskId: string): AgentTask | undefined {
  for (const r of state.rounds) {
    const t = r.tasks.find((x) => x.id === taskId)
    if (t) return t
  }
  return undefined
}
