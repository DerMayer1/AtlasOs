// ── Input ──────────────────────────────────────────────────────────────────

export interface CompanyInput {
  company_name: string
  website_url: string
  description: string
  target_market?: string
  known_competitors?: string[]
  analysis_depth?: 'quick' | 'standard' | 'deep'
}

// ── Pipeline output types ──────────────────────────────────────────────────

export interface Category {
  label: string
  definition: string
}

export type CompetitorType = 'direct' | 'indirect' | 'substitute' | 'adjacent' | 'future'
export type ThreatLevel = 'low' | 'medium' | 'high'

export interface Competitor {
  name: string
  website: string | null
  type: CompetitorType
  threat_level: ThreatLevel
  summary: string
  positioning: string
}

export interface PositioningAxis {
  label: string
  low: string
  high: string
}

export interface PositioningEntity {
  name: string
  x: number
  y: number
  is_subject: boolean
}

export interface PositioningMap {
  x_axis: PositioningAxis
  y_axis: PositioningAxis
  entities: PositioningEntity[]
}

export interface Gap {
  description: string
  addressability: string
  risk: string
}

export interface Recommendation {
  type: string
  description: string
  impact: string
  risk: string
}

export interface MarketMap {
  category: Category
  competitors: Competitor[]
  positioning_map: PositioningMap | null
  gaps: Gap[]
  recommendations: Recommendation[]
  generated_at: string
}

// ── Analysis record ───────────────────────────────────────────────────────

export type AnalysisStatus = 'pending' | 'running' | 'complete' | 'failed'

export interface Analysis {
  id: string
  status: AnalysisStatus
  depth: string
  input: CompanyInput
  result: MarketMap | null
  error: string | null
  duration_ms: number | null
  created_at: string
  completed_at: string | null
  stream_url?: string
}

export interface AnalysisListItem {
  id: string
  status: AnalysisStatus
  company_name: string
  created_at: string
}

export interface PaginatedAnalyses {
  total: number
  limit: number
  offset: number
  items: AnalysisListItem[]
}

// ── Memo ──────────────────────────────────────────────────────────────────

export interface Memo {
  id: string
  analysis_id: string
  content_md: string
  export_count: number
  created_at: string
}

// ── SSE Events ────────────────────────────────────────────────────────────

export type SSEEventType =
  | 'pipeline_start'
  | 'stage_start'
  | 'stage_complete'
  | 'analysis_complete'
  | 'analysis_failed'

export interface SSEEvent {
  event: SSEEventType
  data: Record<string, unknown>
}

// ── API errors ────────────────────────────────────────────────────────────

export interface APIError {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}
