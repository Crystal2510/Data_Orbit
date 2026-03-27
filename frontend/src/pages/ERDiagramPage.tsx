import { useEffect, useState } from 'react'
import { useAppStore } from '../store/useAppStore'
import { getSchemaGraph } from '../api/schemaApi'
import ERDiagram from '../components/er-diagram/ERDiagram'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { BookOpen } from 'lucide-react'

export default function ERDiagramPage() {
  const { connectionId, graphData, setGraphData, dictionary, setActiveTable, activeTableName } = useAppStore()
  const [loading, setLoading] = useState(!graphData)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!connectionId || graphData) { setLoading(false); return }
    getSchemaGraph(connectionId)
      .then(setGraphData)
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [connectionId])

  const activeDoc = activeTableName ? dictionary?.documentation?.[activeTableName] : null

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center"><LoadingSpinner size="lg" className="mx-auto mb-3" /><p className="text-slate-400 text-sm">Building ER diagram…</p></div>
    </div>
  )

  if (error) return (
    <div className="flex items-center justify-center h-full">
      <p className="text-red-400 text-sm">{error}</p>
    </div>
  )

  return (
    <div className="flex h-full">
      <div className="flex-1 relative">
        <ERDiagram graphData={graphData} onNodeClick={setActiveTable} />
      </div>

      {/* Sidebar panel */}
      {activeTableName && (
        <div className="w-72 border-l border-slate-800 bg-slate-900 overflow-y-auto animate-slide-up flex-shrink-0">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-100 font-mono">{activeTableName}</p>
              <p className="text-xs text-slate-500 mt-0.5">{activeDoc?.table_type ?? 'table'}</p>
            </div>
            <button onClick={() => setActiveTable(null)} className="text-slate-600 hover:text-slate-300 text-lg leading-none">×</button>
          </div>

          <div className="p-4 space-y-4">
            {activeDoc ? (
              <>
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Summary</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{activeDoc.business_summary}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Key questions</p>
                  <ul className="space-y-1.5">
                    {activeDoc.key_questions?.map((q, i) => (
                      <li key={i} className="text-xs text-slate-400 flex items-start gap-2">
                        <span className="text-indigo-500 flex-shrink-0 mt-0.5">?</span>{q}
                      </li>
                    ))}
                  </ul>
                </div>
                {activeDoc.recommended_joins?.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">Common joins</p>
                    <div className="flex flex-wrap gap-1.5">
                      {activeDoc.recommended_joins.map(j => (
                        <span key={j} onClick={() => setActiveTable(j)} className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700 px-2 py-1 rounded font-mono cursor-pointer transition-colors">{j}</span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-8">
                <BookOpen size={24} className="text-slate-700 mx-auto mb-2" />
                <p className="text-xs text-slate-600">Run AI analysis to see documentation here</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}