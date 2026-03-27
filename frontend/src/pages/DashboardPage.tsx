import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Database, BarChart3, ShieldAlert, Layers, Zap, ArrowRight, Loader2, RefreshCw } from 'lucide-react'
import { useAppStore } from '../store/useAppStore'
import { getSchema, getSchemaGraph } from '../api/schemaApi'
import { getQualityReport } from '../api/qualityApi'
import { generateDictionary } from '../api/aiApi'
import MetricCard from '../components/ui/MetricCard'
import QualityBar from '../components/ui/QualityBar'
import Badge from '../components/ui/Badge'
import LoadingSpinner from '../components/ui/LoadingSpinner'

export default function DashboardPage() {
  const { connectionId, schema, qualityReport, dictionary, graphData, setSchema, setQualityReport, setDictionary, setGraphData, setIsAnalyzing, isAnalyzing } = useAppStore()
  const [loading, setLoading] = useState(!schema)
  const [loadingMsg, setLoadingMsg] = useState('Loading schema…')
  const [analysisError, setAnalysisError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    if (!connectionId) return
    if (schema && qualityReport) { setLoading(false); return }
    setLoadingMsg('Fetching schema…')
    Promise.all([
      schema ? Promise.resolve(schema) : getSchema(connectionId).then(s => { setSchema(s); return s }),
      qualityReport ? Promise.resolve(qualityReport) : getQualityReport(connectionId).then(q => { setQualityReport(q); return q }),
      // Pre-fetch ER graph so it’s instant when user navigates there
      graphData ? Promise.resolve(graphData) : getSchemaGraph(connectionId).then(g => { setGraphData(g); return g }),
    ])
      .then(() => setLoadingMsg('Ready!'))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [connectionId])

  const runAnalysis = async () => {
    if (!connectionId) return
    setIsAnalyzing(true)
    setAnalysisError('')
    try {
      const result = await generateDictionary(connectionId)
      setDictionary(result)
    } catch (e: unknown) {
      setAnalysisError((e as Error).message)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const avgQuality = qualityReport
    ? Math.round(qualityReport.tables.reduce((a, t) => a + t.quality_score, 0) / qualityReport.tables.length)
    : 0

  const totalCols = schema?.tables.reduce((a, t) => a + t.columns.length, 0) ?? 0
  const totalRows = qualityReport?.tables.reduce((a, t) => a + t.row_count, 0) ?? 0

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mx-auto mb-4" />
          <p className="text-slate-400">{loadingMsg}</p>
          <p className="text-slate-600 text-xs mt-1">Fetching schema, quality & ER diagram in parallel…</p>
        </div>
      </div>
    )
  }

  const qualityColor = avgQuality >= 90 ? '#10b981' : avgQuality >= 70 ? '#f59e0b' : '#ef4444'

  return (
    <div className="p-6 space-y-6 animate-fade-in max-w-7xl">
      {/* Metrics row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Tables" value={schema?.tables.length ?? 0} icon={Database} accent="#6366f1" sub="in schema" />
        <MetricCard label="Total columns" value={totalCols.toLocaleString()} icon={Layers} accent="#3b82f6" />
        <MetricCard label="Avg quality" value={`${avgQuality}%`} icon={BarChart3} accent={qualityColor} />
        <MetricCard label="Total rows" value={totalRows >= 1000 ? `${(totalRows/1000).toFixed(0)}K` : totalRows} icon={ShieldAlert} accent="#8b5cf6" sub="across all tables" />
      </div>

      {/* AI Analysis CTA */}
      {!dictionary ? (
        <div className="glass-card p-6 flex items-center justify-between">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
              <Zap size={18} className="text-indigo-400" />
            </div>
            <div>
              <p className="font-medium text-slate-100">Run AI analysis</p>
              <p className="text-sm text-slate-500 mt-1">
                Generate business documentation, quality insights, and embed schema for NL-to-SQL queries.
                Takes ~30–60 seconds.
              </p>
              {analysisError && <p className="text-xs text-red-400 mt-2">{analysisError}</p>}
            </div>
          </div>
          <button onClick={runAnalysis} disabled={isAnalyzing} className="btn-primary flex items-center gap-2 ml-6 flex-shrink-0">
            {isAnalyzing ? <><Loader2 size={14} className="animate-spin" />Analyzing…</> : <><Zap size={14} />Analyze</>}
          </button>
        </div>
      ) : (
        <div className="glass-card p-4 flex items-center gap-3 border-emerald-500/20 bg-emerald-500/5">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <p className="text-sm text-emerald-400">AI analysis complete — dictionary and insights ready</p>
          <button onClick={runAnalysis} disabled={isAnalyzing} className="ml-auto text-xs text-slate-500 hover:text-slate-300">
            Re-run
          </button>
        </div>
      )}

      {/* Tables list */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Tables</h2>
          <button onClick={() => navigate('/er-diagram')} className="btn-ghost flex items-center gap-1.5 text-xs">
            View ER diagram <ArrowRight size={13} />
          </button>
        </div>
        <div className="divide-y divide-slate-800/70">
          {schema?.tables.map(table => {
            const q = qualityReport?.tables.find(t => t.table_name === table.name)
            const doc = dictionary?.documentation?.[table.name]
            return (
              <div
                key={table.name}
                onClick={() => { useAppStore.getState().setActiveTable(table.name); navigate('/dictionary') }}
                className="flex items-center gap-4 px-5 py-3.5 hover:bg-slate-800/40 cursor-pointer group transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200 font-mono">{table.name}</span>
                    <Badge variant="default">{table.columns.length} cols</Badge>
                  </div>
                  {doc && <p className="text-xs text-slate-500 mt-0.5 truncate">{doc.business_summary?.slice(0, 90)}…</p>}
                </div>
                <div className="flex items-center gap-4 flex-shrink-0">
                  <span className="text-xs text-slate-500 font-mono">{table.row_count?.toLocaleString() ?? '?'} rows</span>
                  {q && (
                    <div className="w-28">
                      <QualityBar score={q.quality_score} />
                    </div>
                  )}
                  <ArrowRight size={14} className="text-slate-700 group-hover:text-slate-400 transition-colors" />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}