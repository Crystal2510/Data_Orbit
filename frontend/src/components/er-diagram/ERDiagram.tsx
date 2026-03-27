import { useCallback, useEffect, useState } from 'react'
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, type Node, type Edge,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { TableNode } from './TableNode'
import { RelationshipEdge } from './RelationshipEdge'
import type { SchemaGraphResponse, TableSchema } from '../../types'
import { Search } from 'lucide-react'

const nodeTypes = { tableNode: TableNode }
const edgeTypes  = { relationshipEdge: RelationshipEdge }

function autoLayout(tables: TableSchema[]): Record<string, { x: number; y: number }> {
  const COLS = 3
  const X_GAP = 280, Y_GAP = 420
  const positions: Record<string, { x: number; y: number }> = {}
  tables.forEach((t, i) => {
    positions[t.name] = { x: (i % COLS) * X_GAP + 60, y: Math.floor(i / COLS) * Y_GAP + 60 }
  })
  return positions
}

interface Props {
  graphData: SchemaGraphResponse | null
  onNodeClick?: (tableName: string) => void
}

export default function ERDiagram({ graphData, onNodeClick }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!graphData) return

    const positions = graphData.nodes.length > 0
      ? Object.fromEntries(graphData.nodes.map(n => [n.id, n.position]))
      : autoLayout(graphData.nodes.map(n => n.data as TableSchema))

    const builtNodes: Node[] = graphData.nodes.map(n => ({
      id: n.id,
      type: 'tableNode',
      position: positions[n.id] ?? { x: 0, y: 0 },
      data: n.data,
    }))

    const builtEdges: Edge[] = graphData.edges.map(e => ({
      ...e,
      type: 'relationshipEdge',
      animated: false,
    }))

    setNodes(builtNodes)
    setEdges(builtEdges)
  }, [graphData])

  useEffect(() => {
    if (!search.trim()) {
      setNodes(ns => ns.map(n => ({ ...n, hidden: false })))
      return
    }
    const q = search.toLowerCase()
    setNodes(ns => ns.map(n => ({ ...n, hidden: !n.id.toLowerCase().includes(q) })))
  }, [search])

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    onNodeClick?.(node.id)
  }, [onNodeClick])

  return (
    <div className="relative w-full h-full">
      <div className="absolute top-4 left-4 z-10">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2">
          <Search size={14} className="text-slate-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Filter tables…"
            className="bg-transparent text-sm text-slate-200 placeholder-slate-600 focus:outline-none w-36"
          />
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
        maxZoom={2}
        className="bg-slate-950"
      >
        <Background variant={BackgroundVariant.Dots} color="#1e293b" gap={24} size={1} />
        <Controls />
        <MiniMap
          nodeColor="#1e293b"
          maskColor="rgba(2, 6, 23, 0.7)"
          style={{ bottom: 20, right: 20 }}
        />
      </ReactFlow>
    </div>
  )
}