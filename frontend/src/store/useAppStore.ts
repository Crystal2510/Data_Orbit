import { create } from 'zustand'
import type { FullSchemaResponse, SchemaGraphResponse, QualityReportResponse, AIDictionaryResponse, PIIReportResponse } from '../types'

interface AppState {
  connectionId: string | null
  connectionStatus: 'idle' | 'connecting' | 'connected' | 'error'
  connectionString: string
  schema: FullSchemaResponse | null
  graphData: SchemaGraphResponse | null
  qualityReport: QualityReportResponse | null
  piiReport: PIIReportResponse | null
  dictionary: AIDictionaryResponse | null
  isAnalyzing: boolean
  activeTableName: string | null
  sidebarCollapsed: boolean

  setConnectionId: (id: string | null) => void
  setConnectionStatus: (s: AppState['connectionStatus']) => void
  setConnectionString: (s: string) => void
  setSchema: (s: FullSchemaResponse | null) => void
  setGraphData: (g: SchemaGraphResponse | null) => void
  setQualityReport: (q: QualityReportResponse | null) => void
  setPIIReport: (p: PIIReportResponse | null) => void
  setDictionary: (d: AIDictionaryResponse | null) => void
  setIsAnalyzing: (b: boolean) => void
  setActiveTable: (name: string | null) => void
  setSidebarCollapsed: (b: boolean) => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  connectionId: null,
  connectionStatus: 'idle',
  connectionString: '',
  schema: null,
  graphData: null,
  qualityReport: null,
  piiReport: null,
  dictionary: null,
  isAnalyzing: false,
  activeTableName: null,
  sidebarCollapsed: false,

  setConnectionId: (id) => set({ connectionId: id }),
  setConnectionStatus: (s) => set({ connectionStatus: s }),
  setConnectionString: (s) => set({ connectionString: s }),
  setSchema: (schema) => set({ schema }),
  setGraphData: (graphData) => set({ graphData }),
  setQualityReport: (qualityReport) => set({ qualityReport }),
  setPIIReport: (piiReport) => set({ piiReport }),
  setDictionary: (dictionary) => set({ dictionary }),
  setIsAnalyzing: (isAnalyzing) => set({ isAnalyzing }),
  setActiveTable: (activeTableName) => set({ activeTableName }),
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
  reset: () => set({
    connectionId: null, connectionStatus: 'idle', schema: null,
    graphData: null, qualityReport: null, piiReport: null, dictionary: null,
    isAnalyzing: false, activeTableName: null,
  }),
}))