export interface ConnectionResponse {
  connection_id: string
  status: string
  message?: string
}

export interface ForeignKey {
  ref_table: string
  ref_column: string
}

export interface ColumnSchema {
  name: string
  type: string
  nullable: boolean
  primary_key: boolean
  foreign_keys: ForeignKey[]
}

export interface TableSchema {
  name: string
  row_count: number
  columns: ColumnSchema[]
  indexes?: unknown[]
}

export interface FullSchemaResponse {
  tables: TableSchema[]
  total_tables: number
}

export interface RelationshipEdge {
  from_table: string
  from_col: string
  to_table: string
  to_col: string
}

export interface SchemaGraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: TableSchema
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
  type: string
  animated: boolean
  label?: string
}

export interface ColumnQuality {
  column_name: string
  null_count: number
  null_rate: number
  fill_rate: number
  unique_count: number
  unique_rate: number
  min?: string | number
  max?: string | number
  mean?: number
  sample_values?: unknown[]
}

export interface TableQuality {
  table_name: string
  row_count: number
  quality_score: number
  columns: ColumnQuality[]
  freshness_days?: number
  anomalies?: string[]
}

export interface QualityReportResponse {
  tables: TableQuality[]
  connection_id: string
}

export interface PIIColumnResult {
  table_name: string
  column_name: string
  risk_level: 'None' | 'Low' | 'High'
  reasoning: string
}

export interface PIIReportResponse {
  results: PIIColumnResult[]
  connection_id: string
}

export interface AIDictionaryEntry {
  table_name: string
  table_type: string
  row_count: number
  quality_score: number
  business_summary: string
  purpose: string
  key_questions: string[]
  recommended_joins: string[]
}

export interface AIQualityInsight {
  plain_english_summary: string
  severity: 'good' | 'warning' | 'critical'
  recommended_actions: string[]
  business_impact: string
  impossible_dates?: { count: number; purchase_col: string; delivered_col: string } | null
}

export interface AIDictionaryResponse {
  connection_id: string
  documentation: Record<string, AIDictionaryEntry>
  quality_insights: Record<string, AIQualityInsight>
  profiled_schema: Record<string, { table_type: string; row_count: number; total_columns: number; estimated_relationships: number; quality_score: number }>
  errors: string[]
  status: string
}

export interface AIQueryResponse {
  connection_id: string
  question: string
  sql: string
  explanation: string
  tables_used: string[]
  confidence: number
  errors: string[]
}

export interface SearchResult {
  table_name: string
  document: string
  relevance: number
  row_count?: number
  column_count?: number
}

export interface SearchResponse {
  tables: SearchResult[]
  columns: SearchResult[]
  total_results: number
}