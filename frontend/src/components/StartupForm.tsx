import { useState } from 'react'

interface Props {
  onSubmit: (idea: string) => void
  loading: boolean
}

export default function StartupForm({ onSubmit, loading }: Props) {
  const [idea, setIdea] = useState('')
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (idea.trim()) onSubmit(idea.trim())
      }}
      style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 720 }}
    >
      <label style={{ fontSize: 14, fontWeight: 600 }}>描述你的创业方向</label>
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        rows={8}
        placeholder="例如：面向中小企业的 AI Agent 客服平台，支持多轮对话、工单自动创建..."
        style={{
          padding: 12, fontSize: 14, border: '1px solid #ddd',
          borderRadius: 8, fontFamily: 'inherit', resize: 'vertical',
        }}
      />
      <button
        type="submit"
        disabled={loading || !idea.trim()}
        style={{
          padding: '10px 20px', fontSize: 14, fontWeight: 600,
          background: loading ? '#aaa' : '#1a1a1a', color: '#fff',
          border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? '分析中...' : '开始分析'}
      </button>
    </form>
  )
}
