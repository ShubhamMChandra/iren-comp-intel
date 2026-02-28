import type {
  AdminStats,
  CompetePageData,
  Competitor,
  DashboardData,
  Prospect,
  SearchResult,
  Signal,
  SignalStats,
} from "./types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const VERBOSE_API_LOG =
  typeof process !== "undefined" &&
  (process.env.NODE_ENV === "development" || process.env.NEXT_PUBLIC_VERBOSE_API_LOG === "1")

function logApi(message: string, data?: Record<string, unknown>) {
  if (VERBOSE_API_LOG) {
    if (data && Object.keys(data).length > 0) {
      console.log(`[api] ${message}`, data)
    } else {
      console.log(`[api] ${message}`)
    }
  }
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method ?? "GET"
  const url = `${API_BASE}${path}`
  const start = performance.now()
  logApi("request", { method, path })
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })
    const duration = Math.round(performance.now() - start)
    if (!res.ok) {
      logApi("error", { path, status: res.status, statusText: res.statusText, durationMs: duration })
      throw new Error(`API error: ${res.status} ${res.statusText}`)
    }
    const data = (await res.json()) as T
    logApi("ok", { path, status: res.status, durationMs: duration })
    return data
  } catch (err) {
    const duration = Math.round(performance.now() - start)
    logApi("error", {
      path,
      durationMs: duration,
      message: err instanceof Error ? err.message : String(err),
    })
    throw err
  }
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
export const getSignals = (opts?: { signal_type?: string; days?: number; limit?: number }) => {
  const params = new URLSearchParams()
  if (opts?.signal_type) params.set("signal_type", opts.signal_type)
  if (opts?.days) params.set("days", String(opts.days))
  if (opts?.limit) params.set("limit", String(opts.limit))
  const qs = params.toString()
  return fetchAPI<Signal[]>(`/api/signals${qs ? `?${qs}` : ""}`)
}

export const getSignalStats = (days?: number) =>
  fetchAPI<SignalStats>(
    `/api/signals/stats${days ? `?days=${days}` : ""}`,
  )

// --- Competitors ---
export const getCompetitors = () => fetchAPI<CompetePageData>("/api/competitors")
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
