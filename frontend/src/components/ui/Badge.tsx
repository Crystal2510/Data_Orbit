import clsx from 'clsx'

type Variant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'

interface Props { children: React.ReactNode; variant?: Variant; className?: string }

const styles: Record<Variant, string> = {
  default: 'bg-slate-800 text-slate-400 border-slate-700',
  success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  danger:  'bg-red-500/10 text-red-400 border-red-500/20',
  info:    'bg-blue-500/10 text-blue-400 border-blue-500/20',
  purple:  'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
}

export default function Badge({ children, variant = 'default', className }: Props) {
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border', styles[variant], className)}>
      {children}
    </span>
  )
}