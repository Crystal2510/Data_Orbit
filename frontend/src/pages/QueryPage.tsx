import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import { runQuery } from '../api/aiApi'
import { Send, Loader2, Database, Download, Copy, Check } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import Badge from '../components/ui/Badge'
import { exportQueryPDF } from '../utils/exportPDF'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sql?: string
  explanation?: string
  tables_used?: string[]
  confidence?: number
  error?: string
}

const SUGGESTIONS = [
  'Show top 5 customers by total revenue',
  'How many orders were delivered late?',
  'What are the top 10 product categories?',
  'Average delivery time by seller state',
  'Monthly order volume trend',
]

export default function QueryPage() {
  const { connectionId } = useAppStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (question: string) => {
    if (!question.trim() || !connectionId || loading) return
    const q = question.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await runQuery(connectionId, q)
      setMessages(m => [...m, {
        role: 'assistant',
        content: res.explanation,
        sql: res.sql,
        explanation: res.explanation,
        tables_used: res.tables_used,
        confidence: res.confidence,
      }])
    } catch (e: unknown) {
      setMessages(m => [...m, { role: 'assistant', content: '', error: (e as Error).message }])
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (sql: string, idx: number) => {
    navigator.clipboard.writeText(sql)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  const handleExportPDF = () => {
    const results = messages
      .filter(m => m.role === 'assistant' && m.sql)
      .map(m => ({
        question: messages[messages.indexOf(m) - 1]?.content ?? '',
        sql: m.sql!,
        explanation: m.explanation ?? '',
        tables_used: m.tables_used ?? [],
        confidence: m.confidence ?? 0,
      }))
    if (results.length) exportQueryPDF(results)
  }

  const confidenceColor = (c: number) => c >= 0.8 ? 'text-emerald-400' : c >= 0.5 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="flex flex-col h-full">
      {/* Header toolbar */}
      {messages.length > 0 && (
        <div className="px-6 py-2 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs text-slate-500">{messages.filter(m => m.role === 'user').length} queries</span>
          <button
            onClick={handleExportPDF}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-indigo-400 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Download size={12} /> Export SQL Report
          </button>
        </div>
      )}
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-4">
              <Database size={24} className="text-indigo-400" />
            </div>
            <h2 className="text-lg font-semibold text-slate-200">Ask anything about your data</h2>
            <p className="text-sm text-slate-500 mt-2 max-w-sm">
              Natural language questions get turned into optimized SQL, grounded in your schema.
            </p>
            <div className="flex flex-wrap justify-center gap-2 mt-6 max-w-lg">
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => send(s)} className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 hover:text-slate-200 px-3 py-2 rounded-lg transition-all">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}>
              {msg.role === 'user' ? (
                <div className="bg-indigo-600 text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-md">
                  {msg.content}
                </div>
              ) : (
                <div className="max-w-2xl w-full space-y-3">
                  {msg.error ? (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">{msg.error}</div>
                  ) : (
                    <>
                      {msg.explanation && (
                        <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3">
                          <p className="text-sm text-slate-300 leading-relaxed">{msg.explanation}</p>
                        </div>
                      )}
                      {msg.sql && (
                        <div className="rounded-xl overflow-hidden border border-slate-800">
                          <div className="flex items-center justify-between px-4 py-2 bg-slate-800/80 border-b border-slate-700">
                            <span className="text-xs font-medium text-slate-400">SQL</span>
                            <button
                              onClick={() => handleCopy(msg.sql!, i)}
                              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-200 transition-colors"
                            >
                              {copiedIdx === i ? <><Check size={11} className="text-emerald-400" /> Copied</> : <><Copy size={11} /> Copy</>}
                            </button>
                          </div>
                          <SyntaxHighlighter
                            language="sql"
                            style={vscDarkPlus}
                            customStyle={{ margin: 0, background: '#0f172a', fontSize: '12px', padding: '16px' }}
                          >
                            {msg.sql}
                          </SyntaxHighlighter>
                        </div>
                      )}
                      <div className="flex items-center gap-2 flex-wrap">
                        {msg.tables_used?.map(t => (
                          <Badge key={t} variant="default"><span className="font-mono">{t}</span></Badge>
                        ))}
                        {msg.confidence != null && (
                          <span className={`text-xs font-mono ml-auto ${confidenceColor(msg.confidence)}`}>
                            {Math.round(msg.confidence * 100)}% confidence
                          </span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 flex items-center gap-2">
              <Loader2 size={14} className="text-indigo-400 animate-spin" />
              <span className="text-sm text-slate-500">Generating SQL…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions row */}
      {messages.length > 0 && (
        <div className="px-6 py-2 flex gap-2 overflow-x-auto border-t border-slate-800/50">
          {SUGGESTIONS.slice(0, 3).map(s => (
            <button key={s} onClick={() => send(s)} className="text-xs bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-500 hover:text-slate-300 px-3 py-1.5 rounded-lg transition-all flex-shrink-0">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-6 pb-6 pt-3 border-t border-slate-800">
        <div className="flex items-end gap-3 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 focus-within:border-indigo-500/50 transition-colors">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) } }}
            placeholder="Ask a question about your data… (Enter to send)"
            rows={1}
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-600 focus:outline-none resize-none leading-relaxed"
          />
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || loading}
            className="w-8 h-8 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 flex items-center justify-center flex-shrink-0 transition-all active:scale-90"
          >
            <Send size={14} className="text-white" />
          </button>
        </div>
        <p className="text-xs text-slate-700 mt-2 text-center">SQL is grounded in your actual schema — no hallucinated table names</p>
      </div>
    </div>
  )
}