import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import { Key, Link, Minus } from 'lucide-react'
import type { TableSchema } from '../../types'

interface Props { data: TableSchema; selected: boolean }

export const TableNode = memo(({ data, selected }: Props) => {
  const pks = data.columns.filter(c => c.primary_key)
  const fks = data.columns.filter(c => c.foreign_keys?.length > 0)
  const regular = data.columns.filter(c => !c.primary_key && !(c.foreign_keys?.length > 0))

  return (
    <div className={`
      bg-slate-900 rounded-xl overflow-hidden w-52 transition-all duration-150
      ${selected ? 'ring-2 ring-indigo-500 shadow-lg shadow-indigo-500/20' : 'ring-1 ring-slate-700 hover:ring-slate-600'}
    `}>
      <Handle type="target" position={Position.Left} className="!bg-slate-600 !border-slate-500 !w-2 !h-2" />

      {/* Table header */}
      <div className="px-3 py-2.5 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-slate-100 truncate">{data.name}</span>
          <span className="text-xs text-slate-500 font-mono flex-shrink-0">
            {data.row_count?.toLocaleString() ?? '?'}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5">{data.columns.length} cols</p>
      </div>

      {/* Columns */}
      <div className="py-1 max-h-52 overflow-y-auto">
        {pks.map(col => (
          <div key={col.name} className="flex items-center gap-2 px-3 py-1 hover:bg-slate-800/50">
            <Key size={11} className="text-amber-400 flex-shrink-0" />
            <span className="text-xs text-amber-300 font-medium truncate">{col.name}</span>
            <span className="text-xs text-slate-600 ml-auto font-mono flex-shrink-0">{col.type.slice(0,8)}</span>
          </div>
        ))}
        {fks.map(col => (
          <div key={col.name} className="flex items-center gap-2 px-3 py-1 hover:bg-slate-800/50">
            <Link size={11} className="text-blue-400 flex-shrink-0" />
            <span className="text-xs text-blue-300 truncate">{col.name}</span>
            <span className="text-xs text-slate-600 ml-auto font-mono flex-shrink-0">{col.type.slice(0,8)}</span>
          </div>
        ))}
        {regular.slice(0, 6).map(col => (
          <div key={col.name} className="flex items-center gap-2 px-3 py-1 hover:bg-slate-800/50">
            <Minus size={11} className="text-slate-600 flex-shrink-0" />
            <span className="text-xs text-slate-400 truncate">{col.name}</span>
            <span className="text-xs text-slate-600 ml-auto font-mono flex-shrink-0">{col.type.slice(0,8)}</span>
          </div>
        ))}
        {regular.length > 6 && (
          <p className="text-xs text-slate-600 px-3 py-1">+{regular.length - 6} more</p>
        )}
      </div>

      <Handle type="source" position={Position.Right} className="!bg-indigo-500 !border-indigo-400 !w-2 !h-2" />
    </div>
  )
})

TableNode.displayName = 'TableNode'