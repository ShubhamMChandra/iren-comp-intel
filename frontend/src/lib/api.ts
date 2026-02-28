import type {
  AdminStats,
  Competitor,
  DashboardData,
  Prospect,
  SearchResult,
  SignalStats,
} from "./types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

// --- Dashboard ---
export const getDashboard = () => fetchAPI<DashboardData>("/api/dashboard")
export const getDashboardDigest = () =>
  fetchAPI<{ digest: string | null }>("/api/dashboard/digest")

// --- Prospects ---
export const getProspects = () => fetchAPI<Prospect[]>("/api/prospects")
export const getProspect = (id: number) =>
  fetchAPI<Prospect>(`/api/prospects/${id}`)

// --- Signals ---
export const getSignalStats = (days?: number) =>
  fetchAPI<SignalStats>(
    `/api/signals/stats${days ? `?days=${days}` : ""}`,
  )

// --- Competitors ---
export const getCompetitors = () => fetchAPI<Competitor[]>("/api/competitors")
export const getCompetitor = (id: number) =>
  fetchAPI<Competitor>(`/api/competitors/${id}`)

// --- Briefs (POST) ---
export const generateBrief = (companyId: number) =>
  fetchAPI<{ brief: string }>("/api/briefs/generate", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId }),
  })
export const generateEmail = (companyId: number) =>
  fetchAPI<{ email: string }>("/api/briefs/email", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId }),
  })
export const generateBattlecard = (companyId: number) =>
  fetchAPI<{ battlecard: string }>("/api/briefs/battlecard", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId }),
  })

// --- Search ---
export const smartSearch = (query: string) =>
  fetchAPI<SearchResult[]>("/api/search", {
    method: "POST",
    body: JSON.stringify({ query }),
  })

// --- Admin ---
export const getAdminStats = () => fetchAPI<AdminStats>("/api/admin/stats")
export const seedDatabase = () =>
  fetchAPI<{ status: string }>("/api/admin/seed", { method: "POST" })
export const rescoreAll = () =>
  fetchAPI<{ status: string; count: number }>("/api/admin/rescore", {
    method: "POST",
  })
