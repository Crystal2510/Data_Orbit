import { useLocation } from 'react-router-dom'
import { useAppStore } from '../../store/useAppStore'
import { Wifi } from 'lucide-react'

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/dashboard':  { title: 'Dashboard',    subtitle: 'Overview of your database' },
  '/er-diagram': { title: 'ER Diagram',   subtitle: 'Interactive entity-relationship map' },
  '/dictionary': { title: 'Dictionary',   subtitle: 'AI-generated data documentation' },
  '/quality':    { title: 'Data Quality', subtitle: 'Quality scores and PII risk analysis' },
  '/query':      { title: 'AI Query',     subtitle: 'Natural language to SQL' },
}

export default function TopBar() {
  const location = useLocation()
  const { connectionId, connectionStatus, schema } = useAppStore()
  const page = PAGE_TITLES[location.pathname] ?? { title: 'Data Dictionary Agent', subtitle: '' }

  return (
    <header className="h-14 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 flex items-center justify-between px-6 flex-shrink-0">
      <div>
        <h1 className="text-sm font-semibold text-slate-100">{page.title}</h1>
        <p className="text-xs text-slate-500">{page.subtitle}</p>
      </div>

      <div className="flex items-center gap-3">
        {schema && (
          <span className="text-xs text-slate-500 bg-slate-800 px-2.5 py-1 rounded-full">
            {schema.tables.length} tables
          </span>
        )}
        <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors ${
          connectionStatus === 'connected'
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : 'bg-slate-800 text-slate-500 border-slate-700'
        }`}>
          <Wifi size={12} />
          {connectionStatus === 'connected' ? 'Connected' : 'Disconnected'}
        </div>
      </div>
    </header>
  )
}