import { useState, useEffect, useCallback } from 'react'
import HistoryCard, { type HistoryRun } from './HistoryCard'

interface Props {
  onRerun: (idea: string) => void
  onViewRun: (runId: string) => void
}

const PAGE_SIZE = 10

export default function HistoryList({ onRerun, onViewRun }: Props) {
  const [runs, setRuns] = useState<HistoryRun[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)

  const fetchRuns = useCallback(async (newOffset: number) => {
    setLoading(true)
    try {
      const resp = await fetch(`/runs?limit=${PAGE_SIZE}&offset=${newOffset}`)
      if (!resp.ok) return
      const data = await resp.json()
      if (newOffset === 0) {
        setRuns(data.runs)
      } else {
        setRuns((prev) => [...prev, ...data.runs])
      }
      setTotal(data.total)
      setOffset(newOffset + data.runs.length)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchRuns(0) }, [fetchRuns])

  async function handleDelete(runId: string) {
    if (!window.confirm('确认删除这条分析记录？')) return
    const resp = await fetch(`/runs/${runId}`, { method: 'DELETE' })
    if (resp.ok || resp.status === 404) {
      setRuns((prev) => prev.filter((r) => r.run_id !== runId))
      setTotal((t) => t - 1)
    }
  }

  const hasMore = offset < total

  return (
    <section style={{ marginTop: 56 }}>
      {/* Section header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 20,
      }}>
        <h2 style={{
          fontSize: 18, fontWeight: 600, color: '#111', margin: 0,
          letterSpacing: '-0.01em',
        }}>
          最近分析
        </h2>
        {total > 0 && (
          <span style={{ fontSize: 13, color: '#9e9e9e' }}>
            {total} 条记录
          </span>
        )}
      </div>

      {loading && runs.length === 0 ? (
        <div style={{
          padding: '48px 0', textAlign: 'center',
        }}>
          <p style={{ color: '#b0b0b0', fontSize: 14, margin: 0 }}>加载中...</p>
        </div>
      ) : runs.length === 0 ? (
        <div style={{
          padding: '48px 0', textAlign: 'center',
          border: '1px solid #eaeaea', borderRadius: 12,
        }}>
          <p style={{ color: '#b0b0b0', fontSize: 14, margin: 0 }}>
            暂无历史记录
          </p>
          <p style={{ color: '#d0d0d0', fontSize: 13, margin: '4px 0 0' }}>
            分析完成后将在这里展示
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {runs.map((run) => (
            <HistoryCard
              key={run.run_id}
              run={run}
              onRerun={onRerun}
              onDelete={handleDelete}
              onClick={onViewRun}
            />
          ))}
        </div>
      )}

      {hasMore && (
        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <button
            onClick={() => fetchRuns(offset)}
            disabled={loading}
            style={{
              padding: '10px 24px', fontSize: 13, fontWeight: 500,
              background: '#fff', color: '#333',
              border: '1px solid #e0e0e0', borderRadius: 10,
              cursor: 'pointer',
              transition: 'background 120ms ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#f5f5f5' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '#fff' }}
          >
            {loading ? '加载中...' : `查看更多`}
          </button>
        </div>
      )}
    </section>
  )
}
