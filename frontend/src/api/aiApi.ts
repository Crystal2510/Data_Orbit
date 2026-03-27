import apiClient from './client'
import type { AIDictionaryResponse, AIQueryResponse, SearchResponse } from '../types'

export const generateDictionary = (connectionId: string): Promise<AIDictionaryResponse> =>
  apiClient.post('/ai/generate-dictionary', { connection_id: connectionId }).then(r => r.data)

export const getDictionary = (connectionId: string): Promise<AIDictionaryResponse> =>
  apiClient.get(`/ai/dictionary/${connectionId}`).then(r => r.data)

export const runQuery = (connectionId: string, question: string): Promise<AIQueryResponse> =>
  apiClient.post('/ai/query', { connection_id: connectionId, question }).then(r => r.data)

export const searchSchema = (connectionId: string, query: string): Promise<SearchResponse> =>
  apiClient.post('/ai/search', { connection_id: connectionId, query }).then(r => r.data)

export const embedSchema = (connectionId: string): Promise<{ status: string }> =>
  apiClient.post('/ai/embed', { connection_id: connectionId }).then(r => r.data)