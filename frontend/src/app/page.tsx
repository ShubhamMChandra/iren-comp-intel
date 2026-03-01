"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { getDashboard, getDashboardDigest, getSignals } from "@/lib/api"
import type { DashboardData, Signal } from "@/lib/types"
import { cn, TIER_COLORS } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { DeltaValue } from "@/components/delta-value"
import { SignalBadge } from "@/components/signal-badge"
import { ProductBadge } from "@/components/product-badge"
import { DrillDown } from "@/components/drill-down"
import {
  PipelineHeatDetail,
  SignalBreakdownDetail,
  ScoreBreakdownDetail,
  TierExplainer,
  DeltaExplainer,
  HottestMoverDetail,
  HeatingUpDetail,
} from "@/components/drill-downs"
import {
  Sparkles,
  Phone,
  TrendingDown,
  ArrowRight,
  Trophy,
  AlertTriangle,
  DollarSign,
  ExternalLink,
} from "lucide-react"
import ReactMarkdown from "react-markdown"

function DashboardSkeleton() {
  return (
    <div className="space-y-8 p-6 md:p-8">
      <Skeleton className="h-9 w-24" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-20" />
      <Skeleton className="h-64" />
    </div>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const [data, setData] = useState<DashboardData | null>(null)
  const [digest, setDigest] = useState<string | null>(null)
  const [digestPeriod, setDigestPeriod] = useState<string>(() =>
    new Date().getHours() < 14 ? "morning" : "afternoon"
  )
  const [digestLoading, setDigestLoading] = useState(true)
  const [fundingSignals, setFundingSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const period = new Date().getHours() < 14 ? "morning" : "afternoon"

    getDashboard()
      .then((d) => { if (!cancelled) setData(d) })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load") })
      .finally(() => { if (!cancelled) setLoading(false) })

    getDashboardDigest(period as "morning" | "afternoon")
      .then((r) => { if (!cancelled) { setDigest(r.digest); setDigestPeriod(r.period) } })
      .catch(() => {})
      .finally(() => { if (!cancelled) setDigestLoading(false) })

    Promise.all([
      getSignals({ signal_type: "fundraising", days: 60, limit: 40, dedup: true }),
      getSignals({ signal_type: "funding_completed", days: 60, limit: 40, dedup: true }),
    ])
      .then(([raising, completed]) => {
        if (cancelled) return
        const sorted = [...raising, ...completed]
          .sort((a, b) => (b.detected_at ?? "").localeCompare(a.detected_at ?? ""))
        // Embedding dedup handles near-identical headlines; cap handles
        // different-angle articles about the same event from one company.
        const seen = new Map<string, number>()
        const diverse: typeof sorted = []
        for (const s of sorted) {
          const key = s.company_name || String(s.company_id)
          if ((seen.get(key) ?? 0) >= 1) continue
          seen.set(key, (seen.get(key) ?? 0) + 1)
          diverse.push(s)
          if (diverse.length >= 12) break
        }
        setFundingSignals(diverse)
      })
      .catch(() => {})

    return () => { cancelled = true }
  }, [])

  if (loading) return <div className="min-h-screen bg-[#09090b]"><DashboardSkeleton /></div>

  if (error || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#09090b] p-8">
        <Card className="max-w-md border-red-500/30 bg-red-500/5">
          <CardHeader><CardTitle className="text-red-400">Error loading dashboard</CardTitle></CardHeader>
          <CardContent><p className="text-sm text-muted-foreground">{error || "No data"}</p></CardContent>
        </Card>
      </div>
    )
  }

  const { kpis, call_list, cooling, top_ranked, alerts, competitive_pulse } = data
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  })

  return (
    <div className="min-h-screen bg-[#09090b] p-6 md:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Today</h1>
        <p className="mt-1 text-sm text-muted-foreground">{today}</p>
      </header>

      {/* KPI Cards — every number is drillable */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {/* Pipeline Heat */}
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Pipeline Heat
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DrillDown
              title="Pipeline Heat"
              content={<PipelineHeatDetail prospects={kpis.hot_prospects} />}
              align="start"
            >
              <span className="text-2xl font-semibold tabular-nums text-[#22c55e]">{kpis.pipeline_hot}</span>
              <span className="ml-2 text-sm text-muted-foreground">/ {kpis.active_prospects}</span>
            </DrillDown>
            <p className="mt-0.5 text-xs text-muted-foreground">High + Very High tier</p>
          </CardContent>
        </Card>

        {/* New Signals */}
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              New Signals
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DrillDown
              title="Signal Breakdown"
              content={<SignalBreakdownDetail breakdown={kpis.signal_breakdown} />}
            >
              <span className="text-2xl font-semibold tabular-nums">{kpis.signals_7d}</span>
              <span className={cn(
                "ml-2 text-sm font-medium tabular-nums",
                kpis.signals_delta >= 0 ? "text-[#22c55e]" : "text-red-400"
              )}>
                {kpis.signals_delta >= 0 ? "+" : ""}{kpis.signals_delta} WoW
              </span>
            </DrillDown>
            <p className="mt-0.5 text-xs text-muted-foreground">Actionable signals this week</p>
          </CardContent>
        </Card>

        {/* Heating Up */}
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Heating Up
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DrillDown
              title="Heating Up"
              content={<HeatingUpDetail prospects={call_list} />}
            >
              <span className="text-2xl font-semibold tabular-nums text-[#22c55e]">{call_list.length}</span>
            </DrillDown>
            <p className="mt-0.5 text-xs text-muted-foreground">Prospects with rising scores</p>
          </CardContent>
        </Card>

        {/* Hottest Mover */}
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Hottest Mover
            </CardTitle>
          </CardHeader>
          <CardContent>
            {kpis.hottest_mover ? (
              <DrillDown
                title="Hottest Mover"
                content={
                  <HottestMoverDetail
                    id={kpis.hottest_mover.id}
                    name={kpis.hottest_mover.name}
                    score={kpis.hottest_mover.score}
                    delta={kpis.hottest_mover.delta}
                    signalType={kpis.hottest_mover.top_signal_type}
                  />
                }
                align="end"
              >
                <div className="text-left">
                  <p className="text-lg font-semibold">{kpis.hottest_mover.name}</p>
                  <DeltaValue delta={kpis.hottest_mover.delta} className="text-sm" />
                </div>
              </DrillDown>
            ) : (
              <p className="text-muted-foreground">—</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* AI Digest */}
      <Card className="mb-8 border-[#22c55e]/20 bg-[#22c55e]/[0.03]">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[#22c55e]" />
            <CardTitle className="text-sm font-medium">{digestPeriod === "afternoon" ? "Afternoon" : "Morning"} Digest</CardTitle>
            <Badge variant="outline" className="text-[10px] border-[#22c55e]/30 text-[#22c55e]">AI</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {digestLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : digest ? (
            <div className="text-[13px] leading-[1.6] text-foreground/85 space-y-3">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p>{children}</p>,
                  strong: ({ children }) => (
                    <strong className="font-semibold text-foreground">{children}</strong>
                  ),
                  ul: ({ children }) => <ul className="space-y-1 ml-3">{children}</ul>,
                  ol: ({ children }) => <ol className="space-y-1 ml-3 list-decimal">{children}</ol>,
                  li: ({ children }) => (
                    <li className="flex gap-2">
                      <span className="shrink-0 text-foreground/40 select-none">·</span>
                      <span>{children}</span>
                    </li>
                  ),
                  h1: ({ children }) => (
                    <div className="pt-2 first:pt-0">
                      <p className="text-[11px] font-bold uppercase tracking-widest text-foreground/50 mb-1">{children}</p>
                      <div className="border-t border-border/40" />
                    </div>
                  ),
                  h2: ({ children }) => (
                    <div className="pt-2 first:pt-0">
                      <p className="text-[11px] font-bold uppercase tracking-widest text-foreground/50 mb-1">{children}</p>
                      <div className="border-t border-border/40" />
                    </div>
                  ),
                  h3: ({ children }) => (
                    <p className="font-semibold text-foreground/70 text-xs uppercase tracking-wide mt-2">{children}</p>
                  ),
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-2">
                      <table className="w-full text-[12px] border-collapse">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="text-left text-[10px] font-semibold uppercase tracking-wider text-foreground/50 pb-1 pr-4 border-b border-border/40">{children}</th>
                  ),
                  td: ({ children }) => (
                    <td className="py-1 pr-4 align-top text-foreground/80">{children}</td>
                  ),
                }}
              >
                {digest}
              </ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground/60">
              Digest unavailable — configure your AI API key to generate daily intelligence briefs.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="mb-8 grid gap-6 lg:grid-cols-3">
        {/* Call List */}
        <Card className="border-border/50 lg:col-span-2" id="call-list">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-[#22c55e]" />
              <CardTitle className="text-sm font-medium">Call List — Score Rising</CardTitle>
            </div>
            <p className="text-xs text-muted-foreground">
              Prospects with positive score movement. Something changed — timing matters.
            </p>
          </CardHeader>
          <CardContent>
            {call_list.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/50 text-muted-foreground">
                      <th className="pb-2 pl-3 pr-4 text-left text-xs font-medium">Company</th>
                      <th className="pb-2 pr-4 text-left text-xs font-medium">Score</th>
                      <th className="pb-2 pr-4 text-right text-xs font-medium">Change</th>
                      <th className="pb-2 pr-4 text-left text-xs font-medium hidden md:table-cell">Why Now</th>
                      <th className="pb-2 text-xs font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {call_list.map((p) => {
                      const soWhat = p.action_insight?.split(" → ")[0] ?? null
                      return (
                        <tr
                          key={p.id}
                          onClick={() => router.push(`/prospects?id=${p.id}`)}
                          className={cn(
                            "border-b border-border/30 last:border-0 transition-colors hover:bg-muted/20 cursor-pointer",
                            p.urgency === "URGENT" && "border-l-2 border-l-red-400",
                            p.urgency === "HIGH" && "border-l-2 border-l-orange-400",
                            p.urgency === "MEDIUM" && "border-l-2 border-l-amber-400/50",
                          )}
                        >
                          <td className="py-2.5 pl-3 pr-4">
                            <div className="flex items-center gap-2">
                              <span className="font-medium hover:text-[#22c55e] transition-colors">{p.name}</span>
                              <ProductBadge productFit={p.product_fit} />
                            </div>
                            <p className="text-xs text-muted-foreground">{p.industry}</p>
                          </td>
                          <td className="py-2.5 pr-4">
                            <div className="flex items-center gap-2">
                              <DrillDown
                                title="Score Breakdown"
                                content={<ScoreBreakdownDetail breakdown={p.score_breakdown} total={p.score} />}
                              >
                                <span className="tabular-nums">{p.score.toFixed(1)}</span>
                              </DrillDown>
                              <DrillDown
                                title="Tier Definition"
                                content={<TierExplainer activeTier={p.tier} />}
                              >
                                <Badge
                                  variant="outline"
                                  className={cn(
                                    "text-[10px] font-semibold tracking-wider border",
                                    TIER_COLORS[p.tier] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/20"
                                  )}
                                >
                                  {p.tier}
                                </Badge>
                              </DrillDown>
                            </div>
                          </td>
                          <td className="py-2.5 pr-4 text-right">
                            <DrillDown
                              title="Score Change"
                              content={<DeltaExplainer score={p.score} delta={p.delta} />}
                            >
                              <DeltaValue delta={p.delta} />
                            </DrillDown>
                          </td>
                          <td className="py-2.5 pr-4 hidden md:table-cell max-w-xs">
                            {soWhat ? (
                              <div>
                                {p.urgency && p.urgency !== "LOW" && (
                                  <span className={cn(
                                    "text-[10px] font-bold mr-1.5",
                                    p.urgency === "URGENT" ? "text-red-400" : p.urgency === "HIGH" ? "text-orange-400" : "text-amber-400"
                                  )}>
                                    {p.urgency}
                                  </span>
                                )}
                                <span className="text-xs text-muted-foreground line-clamp-2">{soWhat}</span>
                              </div>
                            ) : p.headline ? (
                              <span className="text-xs text-muted-foreground line-clamp-2">{p.headline}</span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </td>
                          <td className="py-2.5">
                            <Link
                              href={`/prospects?id=${p.id}`}
                              className="inline-flex items-center gap-1 text-xs font-medium text-[#22c55e] hover:underline"
                            >
                              <span className="hidden sm:inline">Prep</span> <ArrowRight className="h-3 w-3" />
                            </Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No prospects heating up this cycle. Pipeline is steady.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Right column */}
        <div className="space-y-6">
          {/* Cooling Off */}
          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-red-400" />
                <CardTitle className="text-sm font-medium">Cooling Off</CardTitle>
              </div>
              <p className="text-xs text-muted-foreground">Losing signal momentum — check timing</p>
            </CardHeader>
            <CardContent>
              {cooling.length > 0 ? (
                <div className="space-y-2">
                  {cooling.map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-md border border-border/30 px-3 py-2 transition-colors hover:border-border/60 hover:bg-muted/20"
                    >
                      <Link href={`/prospects?id=${p.id}`} className="hover:text-[#22c55e]">
                        <span className="text-sm font-medium">{p.name}</span>
                        <p className="text-xs text-muted-foreground">{p.industry}</p>
                      </Link>
                      <DrillDown
                        title="Score Change"
                        content={<DeltaExplainer score={p.score} delta={p.delta} />}
                        align="end"
                      >
                        <DeltaValue delta={p.delta} className="text-sm" />
                      </DrillDown>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-4 text-center text-sm text-muted-foreground">Nothing cooling. Good sign.</p>
              )}
            </CardContent>
          </Card>

          {/* Funding Tracker */}
          {fundingSignals.length > 0 && (
            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-emerald-400" />
                  <CardTitle className="text-sm font-medium">Funding Tracker</CardTitle>
                </div>
                <p className="text-xs text-muted-foreground">Fundraising & closes — last 30 days</p>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {fundingSignals.map((s) => (
                    <div key={s.id} className="rounded-md border border-border/30 px-3 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold truncate">{s.company_name || "Unknown"}</span>
                        <SignalBadge type={s.signal_type} />
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{s.title}</p>
                      {s.action_insight && (
                        <p className="mt-0.5 text-[11px] text-muted-foreground/50 line-clamp-1">
                          {s.action_insight.split(" → ")[0]}
                        </p>
                      )}
                      <div className="mt-1 flex items-center justify-between">
                        <span className="text-[11px] text-muted-foreground/60">
                          {s.detected_at ? new Date(s.detected_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—"}
                        </span>
                        {s.source_url && (
                          <a
                            href={s.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-0.5 text-[11px] text-muted-foreground/60 hover:text-[#22c55e]"
                          >
                            Source <ExternalLink className="h-2.5 w-2.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Competitive Pulse */}
          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  <CardTitle className="text-sm font-medium">Competitive Pulse</CardTitle>
                </div>
                <Link href="/compete" className="text-xs font-medium text-[#22c55e] hover:underline">
                  Full intel →
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {competitive_pulse ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-2">
                    <div className="rounded-md border border-border/30 px-3 py-2 text-center">
                      <p className="text-lg font-semibold tabular-nums">{competitive_pulse.events_7d}</p>
                      <p className="text-[10px] text-muted-foreground">Events (7d)</p>
                    </div>
                    <div className="rounded-md border border-border/30 px-3 py-2 text-center">
                      <p className="text-lg font-semibold tabular-nums">{competitive_pulse.signals_7d}</p>
                      <p className="text-[10px] text-muted-foreground">Signals (7d)</p>
                    </div>
                    <div className="rounded-md border border-red-400/20 px-3 py-2 text-center">
                      <p className="text-lg font-semibold tabular-nums text-red-400">{competitive_pulse.high_threat_count}</p>
                      <p className="text-[10px] text-muted-foreground">High Threat</p>
                    </div>
                  </div>
                  {competitive_pulse.most_active !== "None" && (
                    <div className="rounded-md border border-amber-400/20 bg-amber-400/5 px-3 py-2">
                      <p className="text-xs">
                        <span className="font-semibold text-amber-400">{competitive_pulse.most_active}</span>
                        {" "}is most active with {competitive_pulse.most_active_count} events this week
                      </p>
                    </div>
                  )}
                  {alerts.length > 0 && (
                    <div className="space-y-1.5">
                      {alerts.slice(0, 3).map((a, i) => (
                        <div key={i} className="rounded-md border border-border/30 px-3 py-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold">{a.company_name}</span>
                            <Badge variant="outline" className="text-[10px]">{a.event_type}</Badge>
                          </div>
                          <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">{a.title}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-4 text-center">No competitor activity detected</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Pipeline Leaderboard */}
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Trophy className="h-4 w-4 text-amber-400" />
              <CardTitle className="text-sm font-medium">Pipeline Leaderboard</CardTitle>
            </div>
            <Link href="/prospects" className="text-xs font-medium text-[#22c55e] hover:underline">
              View all →
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50 text-left text-muted-foreground">
                  <th className="pb-2 pr-4 text-xs font-medium w-8">#</th>
                  <th className="pb-2 pr-4 text-xs font-medium">Company</th>
                  <th className="pb-2 pr-4 text-xs font-medium">Score</th>
                  <th className="pb-2 pr-4 text-xs font-medium">Tier</th>
                  <th className="pb-2 pr-4 text-xs font-medium">Delta</th>
                  <th className="pb-2 text-xs font-medium hidden sm:table-cell">Signal</th>
                </tr>
              </thead>
              <tbody>
                {top_ranked.map((p, i) => (
                  <tr key={p.id} className="border-b border-border/30 last:border-0 transition-colors hover:bg-muted/20">
                    <td className="py-2 pr-4 tabular-nums text-muted-foreground">{i + 1}</td>
                    <td className="py-2 pr-4">
                      <Link href={`/prospects?id=${p.id}`} className="font-medium hover:text-[#22c55e]">
                        {p.name}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                          <div className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out" style={{ width: `${Math.min(100, p.score)}%` }} />
                        </div>
                        <DrillDown
                          title="Score Breakdown"
                          content={<ScoreBreakdownDetail breakdown={p.score_breakdown} total={p.score} />}
                        >
                          <span className="tabular-nums">{p.score.toFixed(1)}</span>
                        </DrillDown>
                      </div>
                    </td>
                    <td className="py-2 pr-4">
                      <DrillDown
                        title="Tier Definition"
                        content={<TierExplainer activeTier={p.tier} />}
                      >
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px] font-semibold tracking-wider border",
                            TIER_COLORS[p.tier] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/20"
                          )}
                        >
                          {p.tier}
                        </Badge>
                      </DrillDown>
                    </td>
                    <td className="py-2 pr-4">
                      {Math.abs(p.delta) >= 0.5 ? (
                        <DrillDown
                          title="Score Change"
                          content={<DeltaExplainer score={p.score} delta={p.delta} />}
                        >
                          <DeltaValue delta={p.delta} />
                        </DrillDown>
                      ) : (
                        <DeltaValue delta={p.delta} />
                      )}
                    </td>
                    <td className="py-2 hidden sm:table-cell">
                      {p.top_signal_type ? <SignalBadge type={p.top_signal_type} /> : <span className="text-muted-foreground">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
