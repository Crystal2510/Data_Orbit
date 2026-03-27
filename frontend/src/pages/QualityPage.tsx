import { useEffect, useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import { getQualityReport, getPIIReport } from '../api/qualityApi'
import QualityBar from '../components/ui/QualityBar'
import Badge from '../components/ui/Badge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { AlertTriangle, ShieldAlert, ShieldCheck, ShieldOff } from 'lucide-react'

export default function QualityPage() {
  const { connectionId, qualityReport, piiReport, setQualityReport, setPIIReport } = useAppStore()
  const [loading, setLoading] = useState(!qualityReport)
  const [sortKey, setSortKey] = useState<'quality_score' | 'row_count'>('quality_score')
  const [hoveredPII, setHoveredPII] = useState<{ table: string; col: string; reasoning: string } | null>(null)

  useEffect(() => {
    if (!connectionId) return
    if (qualityReport && piiReport) { setLoading(false); return }
    Promise.all([
      qualityReport ? null : getQualityReport(connectionId).then(setQualityReport),
      piiReport ? null : getPIIReport(connectionId).then(setPIIReport),
    ]).catch(console.error).finally(() => setLoading(false))
  }, [connectionId])

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <LoadingSpinner size="lg" className="mx-auto" />
    </div>
  )

  const sorted = [...(qualityReport?.tables ?? [])].sort((a, b) =>
    sortKey === 'quality_score' ? a.quality_score - b.quality_score : b.row_count - a.row_count
  )

  // Build PII heatmap: table → column → risk
  const piiMap: Record<string, Record<string, { risk: string; reasoning: string }>> = {}
  for (const item of piiReport?.results ?? []) {
    if (!piiMap[item.table_name]) piiMap[item.table_name] = {}
    piiMap[item.table_name][item.column_name] = { risk: item.risk_level, reasoning: item.reasoning }
  }
  const piiTables = Object.keys(piiMap)

  const riskColor = (r: string) =>
    r === 'High' ? 'bg-red-500/20 border-red-500/40 text-red-400' :
    r === 'Low'  ? 'bg-amber-500/20 border-amber-500/40 text-amber-400' :
                  'bg-slate-800 border-slate-700/50 text-slate-600'

  const riskIcon = (r: string) =>
    r === 'High' ? <ShieldAlert size={11} /> : r === 'Low' ? <ShieldOff size={11} /> : <ShieldCheck size={11} />

  return (
    <div className="p-6 space-y-6 max-w-7xl animate-fade-in">
      {/* Quality scorecard */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Quality scorecard</h2>
          <select
            value={sortKey}
            onChange={e => setSortKey(e.target.value as typeof sortKey)}
            className="text-xs bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-400 focus:outline-none"
          >
            <option value="quality_score">Sort by score ↑</option>
            <option value="row_count">Sort by rows ↓</option>
          </select>
        </div>
        <div className="divide-y divide-slate-800/50">
          {sorted.map(t => (
            <div key={t.table_name} className="px-5 py-3.5 grid grid-cols-12 gap-4 items-center hover:bg-slate-800/30 transition-colors">
              <div className="col-span-3">
                <span className="text-sm font-mono text-slate-200">{t.table_name}</span>
                {t.anomalies?.length ? (
                  <div className="flex items-center gap-1 mt-0.5">
                    <AlertTriangle size={11} className="text-amber-400" />
                    <span className="text-xs text-amber-400">{t.anomalies.length} anomaly</span>
                  </div>
                ) : null}
              </div>
              <div className="col-span-2 text-xs text-slate-500 font-mono">{t.row_count?.toLocaleString()} rows</div>
              <div className="col-span-4"><QualityBar score={t.quality_score} /></div>
              <div className="col-span-2 text-xs text-slate-500">{t.freshness_days != null ? `${t.freshness_days}d ago` : '—'}</div>
              <div className="col-span-1">
                <Badge variant={t.quality_score >= 90 ? 'success' : t.quality_score >= 70 ? 'warning' : 'danger'}>
                  {t.quality_score >= 90 ? 'Good' : t.quality_score >= 70 ? 'Warn' : 'Crit'}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* PII heatmap */}
      {piiTables.length > 0 && (
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-slate-200">PII risk heatmap</h2>
            <p className="text-xs text-slate-500 mt-1">Hover any cell for AI reasoning</p>
          </div>
          <div className="p-5 overflow-x-auto">
            <div className="flex gap-4 mb-3 text-xs text-slate-500">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-red-500/20 border border-red-500/40 inline-block" />High risk</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-amber-500/20 border border-amber-500/40 inline-block" />Low risk</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-slate-800 border border-slate-700/50 inline-block" />No risk</span>
            </div>
            <div className="space-y-3">
              {piiTables.map(tableName => (
                <div key={tableName}>
                  <p className="text-xs text-slate-500 font-mono mb-1.5">{tableName}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(piiMap[tableName]).map(([colName, info]) => (
                      <div
                        key={colName}
                        onMouseEnter={() => setHoveredPII({ table: tableName, col: colName, reasoning: info.reasoning })}
                        onMouseLeave={() => setHoveredPII(null)}
                        className={`flex items-center gap-1 px-2 py-1 rounded border text-xs cursor-default transition-all ${riskColor(info.risk)}`}
                      >
                        {riskIcon(info.risk)}
                        <span className="font-mono">{colName}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {hoveredPII && (
              <div className="mt-4 p-3 bg-slate-800 rounded-lg border border-slate-700 text-xs">
                <p className="font-medium text-slate-300 font-mono">{hoveredPII.table}.{hoveredPII.col}</p>
                <p className="text-slate-400 mt-1 leading-relaxed">{hoveredPII.reasoning}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}