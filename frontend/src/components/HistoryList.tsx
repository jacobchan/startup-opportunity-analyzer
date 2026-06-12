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

  if (loading && runs.length === 0) {
    return (
      <div style={{ marginTop: 24 }}>
        <h3 style={{ fontSize: 15, marginBottom: 12 }}>最近分析</h3>
        <p style={{ color: '#aaa', fontSize: 13 }}>加载中...</p>
      </div>
    )
  }

  return (
    <div style={{ marginTop: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, margin: 0 }}>最近分析</h3>
        <span style={{ fontSize: 12, color: '#888' }}>共 {total} 条记录</span>
      </div>

      {runs.length === 0 ? (
        <p style={{ color: '#aaa', fontSize: 13 }}>暂无历史记录</p>
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
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            onClick={() => fetchRuns(offset)}
            disabled={loading}
            style={{
              padding: '6px 16px', fontSize: 13, background: '#fff',
              border: '1px solid #ddd', borderRadius: 6, cursor: 'pointer',
            }}
          >
            {loading ? '加载中...' : '查看更多'}
          </button>
        </div>
      )}
    </div>
  )
}
