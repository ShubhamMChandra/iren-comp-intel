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

export type ProductFit = "ai_cloud" | "colocation" | "build_to_suit"

export interface Contact {
  id: number
  title: string
  role_type: "technical" | "economic" | "champion" | "procurement"
  seniority: string
  recommended_approach: string
  name: string
  last_contacted: string | null
}

export interface EngagementWindow {
  signal_type: string
  window: string
  insight: string
  urgency: string
  detected_at: string | null
}

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
  product_fit: ProductFit | null
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
  contacts?: Contact[]
  engagement_windows?: EngagementWindow[]
  score_story?: string | null
}

export interface Signal {
  id: number
  company_id: number
  company_name?: string
  signal_type: string
  title: string
  summary: string
  source_url: string
  source_type: string
  magnitude: number
  detected_at: string | null
  action_window: string | null
  action_insight: string | null
  urgency: string | null
  timing_insight: string | null
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
  segment: string
  signal_count_30d: number
  key_customers: string[]
  strengths: string[]
  weaknesses: string[]
  threat_level: "high" | "medium" | "low"
  signals: Signal[]
  events: CompetitorEvent[]
}

export interface IrenBenchmark {
  name: string
  industry: string
  capacity_mw: number | null
  gpu_count: number | null
  is_public: boolean
  ticker: string
  hq_location: string
  website: string
  segment: string
  key_customers?: string[]
  known_pricing?: string
  strengths?: string[]
  weaknesses?: string[]
  expansion_plans?: string
}

export interface SegmentProfile {
  name: string
  description: string
  iren_positioning: string
  key_battleground: string
  competitor_count: number
  total_capacity_mw: number
}

export interface ActivityFeedItem {
  type: "event" | "signal"
  event_type: string
  company_name: string
  company_id: number
  title: string
  description: string
  source_url: string
  detected_at: string | null
}

export interface LandscapeData {
  iren: IrenBenchmark
  competitors: Competitor[]
  segments: SegmentProfile[]
  activity_feed: ActivityFeedItem[]
}

export interface CompetePageData {
  iren: IrenBenchmark
  competitors: Competitor[]
}

export interface CompetitiveContext {
  prospect_name: string
  product_fit: string
  likely_competitors: {
    id: number
    name: string
    segment: string
    threat_level: string
    capacity_mw: number | null
    key_customers: string[]
    known_pricing: string | null
  }[]
  recent_moves: {
    company_name: string
    event_type: string
    title: string
    detected_at: string | null
  }[]
  iren_edge: string
}

export interface DealThreat {
  prospect_id: number
  prospect_name: string
  product_fit: string
  score: number
  tier: Tier
  competing_segments: string[]
  recent_competitor_moves: {
    company_name: string
    event_type: string
    title: string
    detected_at: string | null
  }[]
}

export interface DealThreatsData {
  threats: DealThreat[]
  total_at_risk: number
}

export interface CompetitivePulse {
  events_7d: number
  signals_7d: number
  most_active: string
  most_active_count: number
  high_threat_count: number
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
  product_fit: ProductFit | null
  score: number
  tier: Tier
  delta: number
  top_signal_type: SignalType | null
  headline: string | null
  action_insight: string | null
  urgency: string | null
  primary_contact: Contact | null
  score_breakdown: ScoreBreakdown
}

export interface DashboardProspect {
  id: number
  name: string
  industry: string
  product_fit: ProductFit | null
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
  competitive_pulse: CompetitivePulse
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
