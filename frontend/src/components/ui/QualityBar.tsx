interface Props { score: number; showLabel?: boolean }

export default function QualityBar({ score, showLabel = true }: Props) {
  const color = score >= 90 ? '#10b981' : score >= 70 ? '#f59e0b' : '#ef4444'
  const label = score >= 90 ? 'Good' : score >= 70 ? 'Warning' : 'Critical'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.min(score, 100)}%`, backgroundColor: color }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-mono w-8 text-right" style={{ color }}>{Math.round(score)}</span>
      )}
    </div>
  )
}