import { useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import { Search, BookOpen, Zap, ChevronRight, Download } from 'lucide-react'
import Badge from '../components/ui/Badge'
import QualityBar from '../components/ui/QualityBar'
import { exportDictionaryPDF } from '../utils/exportPDF'

export default function DictionaryPage() {
  const { schema, dictionary, qualityReport, activeTableName, setActiveTable } = useAppStore()
  const [search, setSearch] = useState('')

  const tables = schema?.tables ?? []
  const filtered = tables.filter(t => t.name.toLowerCase().includes(search.toLowerCase()))
  const selected = activeTableName ?? filtered[0]?.name ?? null

  const doc = selected ? dictionary?.documentation?.[selected] : null
  const insight = selected ? dictionary?.quality_insights?.[selected] : null
  const quality = selected ? qualityReport?.tables.find(t => t.table_name === selected) : null
  const tableSchema = selected ? tables.find(t => t.name === selected) : null

  const severityVariant = (s?: string) =>
    s === 'good' ? 'success' : s === 'warning' ? 'warning' : s === 'critical' ? 'danger' : 'default'

  const handleExport = () => {
    exportDictionaryPDF({
      connectionId: 'data-dictionary',
      tables: tables.map(t => ({
        name: t.name,
        row_count: t.row_count,
        columns: t.columns,
        doc: dictionary?.documentation?.[t.name] as never,
        quality: qualityReport?.tables.find(q => q.table_name === t.name) as never,
      })),
    })
  }

  return (
    <div className="flex h-full">
      {/* Left — table list */}
      <div className="w-60 flex-shrink-0 border-r border-slate-800 flex flex-col bg-slate-900">
        <div className="p-3 border-b border-slate-800 space-y-2">
          <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-2">
            <Search size={13} className="text-slate-500" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search tables…"
              className="bg-transparent text-xs text-slate-300 placeholder-slate-600 focus:outline-none flex-1"
            />
          </div>
          <button
            onClick={handleExport}
            className="w-full flex items-center justify-center gap-1.5 text-xs text-slate-400 hover:text-indigo-400 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg py-1.5 transition-colors"
          >
            <Download size={12} /> Export PDF
          </button>
        </div>
        <div className="overflow-y-auto flex-1">
          {filtered.map(t => {
            const q = qualityReport?.tables.find(x => x.table_name === t.name)
            const isActive = selected === t.name
            return (
              <button
                key={t.name}
                onClick={() => setActiveTable(t.name)}
                className={`w-full text-left px-4 py-3 border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors ${isActive ? 'bg-indigo-600/10 border-l-2 border-l-indigo-500' : ''}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-xs font-mono font-medium truncate ${isActive ? 'text-indigo-300' : 'text-slate-300'}`}>{t.name}</span>
                  {q && <span className={`text-xs flex-shrink-0 font-mono ${q.quality_score >= 90 ? 'text-emerald-500' : q.quality_score >= 70 ? 'text-amber-500' : 'text-red-500'}`}>{Math.round(q.quality_score)}</span>}
                </div>
                <p className="text-xs text-slate-600 mt-0.5">{t.columns.length} cols · {t.row_count?.toLocaleString()} rows</p>
              </button>
            )
          })}
        </div>
      </div>

      {/* Right — detail */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {!selected ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center"><BookOpen size={32} className="text-slate-700 mx-auto mb-3" /><p className="text-slate-500">Select a table</p></div>
          </div>
        ) : (
          <div className="max-w-3xl animate-fade-in">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 mb-6">
              <div>
                <h2 className="text-xl font-semibold text-slate-100 font-mono">{selected}</h2>
                <div className="flex items-center gap-2 mt-2">
                  {doc?.table_type && <Badge variant="purple">{doc.table_type}</Badge>}
                  {tableSchema && <Badge variant="default">{tableSchema.columns.length} columns</Badge>}
                  {quality && <Badge variant="default">{quality.row_count?.toLocaleString()} rows</Badge>}
                  {insight && <Badge variant={severityVariant(insight.severity)}>{insight.severity}</Badge>}
                </div>
              </div>
              {quality && <div className="w-36"><QualityBar score={quality.quality_score} /></div>}
            </div>

            {!doc ? (
              <div className="glass-card p-5 flex items-center gap-4">
                <Zap size={18} className="text-indigo-400" />
                <p className="text-sm text-slate-400">Run AI analysis from the Dashboard to generate documentation for this table.</p>
              </div>
            ) : (
              <>
                {/* Summary */}
                <div className="glass-card p-5 mb-4">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">Business summary</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{doc.business_summary}</p>
                  <p className="text-xs text-slate-500 mt-3 border-t border-slate-800 pt-3">{doc.purpose}</p>
                </div>

                {/* Key questions */}
                <div className="glass-card p-5 mb-4">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">Key questions this table answers</p>
                  <ul className="space-y-2">
                    {doc.key_questions?.map((q, i) => (
                      <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
                        <ChevronRight size={15} className="text-indigo-500 flex-shrink-0 mt-0.5" />{q}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Quality insight */}
                {insight && (
                  <div className="glass-card p-5 mb-4">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">Quality insight</p>
                    <p className="text-sm text-slate-300 leading-relaxed mb-3">{insight.plain_english_summary}</p>
                    {insight.recommended_actions?.length > 0 && (
                      <ul className="space-y-1.5">
                        {insight.recommended_actions.map((a, i) => (
                          <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                            <span className="text-amber-500 flex-shrink-0">→</span>{a}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Columns table */}
            {tableSchema && (
              <div className="glass-card overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-800">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">Columns</p>
                </div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/50">
                      {['Column', 'Type', 'Nullable', 'Flags', 'Fill rate'].map(h => (
                        <th key={h} className="text-left px-4 py-2.5 text-slate-500 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {tableSchema.columns.map(col => {
                      const cq = quality?.columns.find(c => c.column_name === col.name)
                      return (
                        <tr key={col.name} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-4 py-2.5 font-mono text-slate-200">{col.name}</td>
                          <td className="px-4 py-2.5 font-mono text-slate-500">{col.type}</td>
                          <td className="px-4 py-2.5 text-slate-500">{col.nullable ? 'yes' : 'no'}</td>
                          <td className="px-4 py-2.5">
                            <div className="flex gap-1">
                              {col.primary_key && <Badge variant="warning">PK</Badge>}
                              {col.foreign_keys?.length > 0 && <Badge variant="info">FK</Badge>}
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            {cq ? <span className={cq.fill_rate >= 95 ? 'text-emerald-400' : cq.fill_rate >= 80 ? 'text-amber-400' : 'text-red-400'}>{cq.fill_rate.toFixed(1)}%</span> : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}