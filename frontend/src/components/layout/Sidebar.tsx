import { NavLink, useNavigate } from 'react-router-dom'
import {
  Database, GitBranch, BookOpen, BarChart3,
  MessageSquareCode, LayoutDashboard, LogOut, ChevronLeft, ChevronRight
} from 'lucide-react'
import { useAppStore } from '../../store/useAppStore'
import clsx from 'clsx'

const NAV = [
  { to: '/dashboard',  icon: LayoutDashboard,    label: 'Dashboard' },
  { to: '/er-diagram', icon: GitBranch,           label: 'ER Diagram' },
  { to: '/dictionary', icon: BookOpen,            label: 'Dictionary' },
  { to: '/quality',    icon: BarChart3,           label: 'Quality' },
  { to: '/query',      icon: MessageSquareCode,   label: 'AI Query' },
]

export default function Sidebar() {
  const { connectionId, connectionStatus, sidebarCollapsed, setSidebarCollapsed, reset } = useAppStore()
  const navigate = useNavigate()

  const handleDisconnect = () => {
    reset()
    navigate('/')
  }

  return (
    <aside className={clsx(
      'flex flex-col h-screen bg-slate-900 border-r border-slate-800 transition-all duration-300 flex-shrink-0',
      sidebarCollapsed ? 'w-16' : 'w-56'
    )}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-800">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
          <Database size={16} className="text-white" />
        </div>
        {!sidebarCollapsed && (
          <div className="overflow-hidden">
            <p className="text-sm font-semibold text-slate-100 truncate">DataDict</p>
            <p className="text-xs text-slate-500 truncate">Agent v1.0</p>
          </div>
        )}
      </div>

      {/* Connection status */}
      {!sidebarCollapsed && (
        <div className="mx-3 mt-3 px-3 py-2 bg-slate-800/60 rounded-lg border border-slate-700/50">
          <div className="flex items-center gap-2">
            <span className={clsx(
              'w-2 h-2 rounded-full flex-shrink-0',
              connectionStatus === 'connected' ? 'bg-emerald-500' : 'bg-slate-600'
            )} />
            <span className="text-xs text-slate-400 truncate">
              {connectionStatus === 'connected' ? 'Connected' : 'No connection'}
            </span>
          </div>
          {connectionId && (
            <p className="text-xs text-slate-600 mt-1 truncate font-mono">{connectionId.slice(0, 16)}…</p>
          )}
        </div>
      )}

      {/* Nav links */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 text-sm font-medium group',
              isActive
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                : 'text-slate-500 hover:text-slate-200 hover:bg-slate-800',
              sidebarCollapsed && 'justify-center'
            )}
          >
            <Icon size={17} className="flex-shrink-0" />
            {!sidebarCollapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Bottom controls */}
      <div className="px-2 pb-4 space-y-1 border-t border-slate-800 pt-3">
        <button
          onClick={handleDisconnect}
          className={clsx(
            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all duration-150',
            sidebarCollapsed && 'justify-center'
          )}
        >
          <LogOut size={17} className="flex-shrink-0" />
          {!sidebarCollapsed && 'Disconnect'}
        </button>
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="w-full flex items-center justify-center p-2 rounded-lg text-slate-600 hover:text-slate-300 hover:bg-slate-800 transition-all"
        >
          {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  )
}