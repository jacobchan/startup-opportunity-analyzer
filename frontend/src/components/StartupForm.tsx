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
      style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
    >
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value)}
        rows={10}
        placeholder="描述你的创业方向，越具体分析越准确..."
        style={{
          padding: '16px 20px', fontSize: 15, lineHeight: 1.7,
          border: '1px solid #e0e0e0', borderRadius: 14,
          fontFamily: 'inherit', resize: 'vertical',
          outline: 'none',
          color: '#111',
          background: '#fff',
          transition: 'border-color 150ms ease, box-shadow 150ms ease',
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = '#b0b0b0'
          e.currentTarget.style.boxShadow = '0 0 0 1px rgba(0,0,0,0.03)'
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = '#e0e0e0'
          e.currentTarget.style.boxShadow = 'none'
        }}
      />
      <button
        type="submit"
        disabled={loading || !idea.trim()}
        style={{
          alignSelf: 'center',
          padding: '10px 28px', fontSize: 14, fontWeight: 600,
          background: loading || !idea.trim() ? '#d4d4d4' : '#d97706',
          color: '#fff',
          border: 'none', borderRadius: 10,
          cursor: loading || !idea.trim() ? 'not-allowed' : 'pointer',
          transition: 'background 120ms ease',
        }}
      >
        {loading ? '分析中...' : '开始分析'}
      </button>
    </form>
  )
}
