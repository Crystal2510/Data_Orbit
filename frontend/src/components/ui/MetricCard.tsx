import type { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  icon: LucideIcon
  sub?: string
  accent?: string
}

export default function MetricCard({ label, value, icon: Icon, sub, accent = '#6366f1' }: Props) {
  return (
    <div className="stat-card animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-semibold text-slate-100 mt-1.5">{value}</p>
          {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
        </div>
        <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${accent}20` }}>
          <Icon size={18} style={{ color: accent }} />
        </div>
      </div>
    </div>
  )
}