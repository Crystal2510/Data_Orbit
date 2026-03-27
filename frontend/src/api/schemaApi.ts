import apiClient from './client'
import type { ConnectionResponse, FullSchemaResponse, SchemaGraphResponse } from '../types'

export const connectDatabase = (connectionString: string): Promise<ConnectionResponse> =>
  apiClient.post('/connect', { connection_string: connectionString }).then(r => r.data)

export const getDefaultConnection = (): Promise<{ connection_id: string | null }> =>
  apiClient.get('/default-connection').then(r => r.data)

export const getSchema = (connectionId: string): Promise<FullSchemaResponse> =>
  apiClient.get(`/schema/${connectionId}`).then(r => r.data)

export const getSchemaGraph = (connectionId: string): Promise<SchemaGraphResponse> =>
  apiClient.get(`/schema/${connectionId}/graph`).then(r => r.data)