import apiClient from './client'
import type { QualityReportResponse, PIIReportResponse } from '../types'

export const getQualityReport = (connectionId: string): Promise<QualityReportResponse> =>
  apiClient.get(`/quality/${connectionId}`).then(r => r.data)

export const getPIIReport = (connectionId: string): Promise<PIIReportResponse> =>
  apiClient.get(`/quality/${connectionId}/pii`).then(r => r.data)