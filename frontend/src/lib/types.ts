export interface ProspectScore {
  total: number
  fundraising: number
  funding_completed: number
  hiring: number
  ai_initiative: number
  cloud_spend: number
  outgrowing: number
  scored_at: string | null
}

export type Tier = "VERY HIGH" | "HIGH" | "MEDIUM" | "LOW" | "DORMANT"

export type SignalType =
  | "fundraising"
  | "funding_completed"
  | "hiring"
  | "ai_initiative"
  | "cloud_spend"
  | "outgrowing"

export interface Prospect {
  id: number
  name: string
  company_type: string
  industry: string
  website: string
  description: string
  hq_location: string
  employee_count: number | null
  founded_year: number | null
  is_public: boolean
  ticker: string | null
  capacity_mw: number | null
  gpu_count: number | null
  known_pricing: string | null
  total_funding: number | null
  last_funding_amount: number | null
  score: ProspectScore | null
  delta: number
  tier: Tier
  signals_7d: number
  top_signal_type: SignalType | null
  signals?: Signal[]
  score_story?: string | null
}

export interface Signal {
  id: number
  company_id: number
  signal_type: string
  title: string
  summary: string
  source_url: string
  source_type: string
  magnitude: number
  detected_at: string | null
}

export interface CompetitorEvent {
  id: number
  company_id: number
  event_type: string
  title: string
  description: string
  source_url: string
  detected_at: string | null
}

export interface Competitor {
  id: number
  name: string
  company_type: string
  industry: string
  website: string
  description: string
  hq_location: string
  employee_count: number | null
  is_public: boolean
  ticker: string | null
  capacity_mw: number | null
  gpu_count: number | null
  known_pricing: string | null
  total_funding: number | null
  score: ProspectScore | null
  delta: number
  signals: Signal[]
  events: CompetitorEvent[]
}

export type ScoreBreakdown = Record<string, number>

export interface HotProspect {
  id: number
  name: string
  score: number
  tier: Tier
}

export interface DashboardKPIs {
  active_prospects: number
  pipeline_hot: number
  hot_prospects: HotProspect[]
  signals_7d: number
  signals_delta: number
  signal_breakdown: Record<string, number>
  hottest_mover: {
    name: string
    id: number
    delta: number
    score: number
    top_signal_type: SignalType | null
  } | null
}

export interface CallListEntry {
  id: number
  name: string
  industry: string
  score: number
  tier: Tier
  delta: number
  top_signal_type: SignalType | null
  headline: string | null
  score_breakdown: ScoreBreakdown
}

export interface DashboardProspect {
  id: number
  name: string
  industry: string
  score: number
  tier: Tier
  delta: number
  top_signal_type: SignalType | null
  score_breakdown: ScoreBreakdown
}

export interface DashboardAlert {
  company_name: string
  event_type: string
  title: string
  detected_at: string | null
}

export interface DashboardData {
  kpis: DashboardKPIs
  call_list: CallListEntry[]
  cooling: DashboardProspect[]
  top_ranked: DashboardProspect[]
  alerts: DashboardAlert[]
}

export interface SignalStats {
  period_days: number
  total: number
  by_type: Record<string, number>
}

export interface AdminStats {
  companies: number
  signals: number
  scores: number
  briefs: number
  signal_distribution: Record<string, number>
  weights: Record<
    string,
    { max_points: number; base_points: number; halflife: number }
  >
}

export interface SearchResult {
  id: number
  name: string
  reason: string
  score: number
  tier?: Tier
}
