import { memo } from 'react'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react'

export const RelationshipEdge = memo(({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, selected,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: selected ? '#818cf8' : '#475569',
          strokeWidth: selected ? 2 : 1.5,
          strokeDasharray: '5 3',
          animation: 'dashdraw 0.8s linear infinite',
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)` }}
          className="absolute pointer-events-none"
        >
          <span className="text-xs bg-slate-800 text-slate-500 border border-slate-700 px-1.5 py-0.5 rounded font-mono">
            FK
          </span>
        </div>
      </EdgeLabelRenderer>
      <style>{`@keyframes dashdraw { to { stroke-dashoffset: -16; } }`}</style>
    </>
  )
})

RelationshipEdge.displayName = 'RelationshipEdge'