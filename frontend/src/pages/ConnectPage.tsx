import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Database, Zap, Shield, GitBranch, Loader2 } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { connectDatabase, getDefaultConnection } from '../api/schemaApi'

const PRESETS = [
  { label: 'Neon PostgreSQL (Demo)', value: 'postgresql://neondb_owner:npg_91hgMFarmtNI@ep-lingering-truth-a1vskwc3-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require' },
  { label: 'SQLite local',           value: 'sqlite:///./olist.db' },
  { label: 'PostgreSQL local',       value: 'postgresql://user:password@localhost:5432/dbname' },
  { label: 'MySQL local',            value: 'mysql+pymysql://user:password@localhost:3306/dbname' },
  { label: 'MySQL (remote)',         value: 'mysql+pymysql://user:password@host:3306/dbname' },
  { label: 'Custom…',               value: '' },
]

const FEATURES = [
  { icon: GitBranch, label: 'Interactive ER diagrams',    desc: 'Drag, zoom, explore relationships' },
  { icon: Zap,       label: 'AI-generated documentation', desc: 'Business context for every table' },
  { icon: Shield,    label: 'PII risk detection',         desc: 'GDPR-aware column classification' },
  { icon: Database,  label: 'NL-to-SQL queries',          desc: 'Ask questions in plain English' },
]

export default function ConnectPage() {
  const [connStr, setConnStr] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [checkingDefault, setCheckingDefault] = useState(true)
  const { setConnectionId, setConnectionStatus } = useAppStore()
  const navigate = useNavigate()

  // Check if backend already has a default connection (from .env DATABASE_URL)
  useEffect(() => {
    getDefaultConnection()
      .then(({ connection_id }) => {
        if (connection_id) {
          setConnectionId(connection_id)
          setConnectionStatus('connected')
          navigate('/dashboard')
        }
      })
      .catch(() => {})
      .finally(() => setCheckingDefault(false))
  }, [])

  const handleConnect = async () => {
    if (!connStr.trim()) { setError('Enter a connection string'); return }
    setLoading(true)
    setError('')
    try {
      const res = await connectDatabase(connStr.trim())
      setConnectionId(res.connection_id)
      setConnectionStatus('connected')
      navigate('/dashboard')
    } catch (e: unknown) {
      setError((e as Error).message)
      setConnectionStatus('error')
    } finally {
      setLoading(false)
    }
  }

  if (checkingDefault) {
    return (
      <div className="h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <Loader2 className="animate-spin" size={20} />
          <span>Checking connection…</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-2/5 flex-col justify-between p-12 bg-gradient-to-br from-slate-900 to-slate-950 border-r border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
            <Database size={20} className="text-white" />
          </div>
          <div>
            <p className="font-semibold text-slate-100">Data Dictionary Agent</p>
            <p className="text-xs text-slate-500">Powered by LangGraph + RAG</p>
          </div>
        </div>

        <div className="space-y-8">
          <div>
            <h2 className="text-3xl font-semibold text-slate-100 leading-tight">
              Understand any database<br />
              <span className="text-indigo-400">in seconds</span>
            </h2>
            <p className="mt-4 text-slate-400 leading-relaxed">
              Drop in a connection string. Our multi-agent AI analyzes your schema,
              generates business documentation, and lets you query with plain English.
            </p>
          </div>
          <div className="space-y-4">
            {FEATURES.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon size={15} className="text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-200">{label}</p>
                  <p className="text-xs text-slate-500">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-slate-700">TriVector · VIT CodeApex 2025</p>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md animate-slide-up">
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
              <Database size={17} className="text-white" />
            </div>
            <p className="font-semibold text-slate-100">Data Dictionary Agent</p>
          </div>

          <h1 className="text-2xl font-semibold text-slate-100">Connect a database</h1>
          <p className="mt-2 text-sm text-slate-500">Supports PostgreSQL, MySQL, and SQLite</p>

          <div className="mt-8 space-y-5">
            {/* Preset selector */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wide">Quick connect</label>
              <select
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
                onChange={e => setConnStr(e.target.value)}
                defaultValue=""
              >
                <option value="" disabled>Select a preset…</option>
                {PRESETS.map(p => <option key={p.label} value={p.value}>{p.label}</option>)}
              </select>
            </div>

            {/* Manual input */}
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 uppercase tracking-wide">Connection string</label>
              <textarea
                className="input-field min-h-[90px] resize-none leading-relaxed"
                placeholder="postgresql://user:password@host:5432/dbname"
                value={connStr}
                onChange={e => setConnStr(e.target.value)}
                spellCheck={false}
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <button
              onClick={handleConnect}
              disabled={loading || !connStr.trim()}
              className="btn-primary w-full py-3 flex items-center justify-center gap-2 text-sm"
            >
              {loading ? (
                <><Loader2 size={16} className="animate-spin" />Connecting…</>
              ) : (
                <><Database size={16} />Connect database</>
              )}
            </button>

            <p className="text-xs text-center text-slate-600">
              Your credentials never leave this machine — only schema metadata is sent to the AI.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}