"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getLandscape, getDealThreats, generateBattlecard } from "@/lib/api"
import { cn, formatDate } from "@/lib/utils"
import type { LandscapeData, ActivityFeedItem, DealThreat, DealThreatsData } from "@/lib/types"
import {
  Globe,
  Swords,
  Sparkles,
  Loader2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Activity,
  Shield,
  TrendingUp,
  ExternalLink,
  AlertTriangle,
  CheckCircle,
  MinusCircle,
  Flame,
  Target,
  BookOpen,
} from "lucide-react"

type SortKey = "capacity_mw" | "gpu_count" | "signal_count_30d" | "name" | "threat_level"
type SortDir = "asc" | "desc"

const THREAT_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 }

const SEGMENT_COLORS: Record<string, string> = {
  "Neocloud": "text-violet-400 bg-violet-400/10 border-violet-400/20",
  "Hyperscaler": "text-blue-400 bg-blue-400/10 border-blue-400/20",
  "DC REIT": "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  "Power-First": "text-orange-400 bg-orange-400/10 border-orange-400/20",
  "International": "text-pink-400 bg-pink-400/10 border-pink-400/20",
  "Miner-to-HPC": "text-amber-400 bg-amber-400/10 border-amber-400/20",
  "Data Center": "text-zinc-400 bg-zinc-400/10 border-zinc-400/20",
}

const THREAT_CONFIG: Record<string, { color: string; icon: typeof AlertTriangle; label: string }> = {
  high: { color: "text-red-400 bg-red-400/10 border-red-400/30", icon: AlertTriangle, label: "High" },
  medium: { color: "text-amber-400 bg-amber-400/10 border-amber-400/30", icon: MinusCircle, label: "Med" },
  low: { color: "text-green-400 bg-green-400/10 border-green-400/30", icon: CheckCircle, label: "Low" },
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  deal: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  expansion: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  pricing: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  talent: "text-purple-400 bg-purple-400/10 border-purple-400/30",
}

function SegmentBadge({ segment }: { segment: string }) {
  const colors = SEGMENT_COLORS[segment] ?? SEGMENT_COLORS["Data Center"]
  return (
    <Badge variant="outline" className={cn("text-[10px] font-semibold tracking-wider border", colors)}>
      {segment}
    </Badge>
  )
}

function ThreatBadge({ level }: { level: string }) {
  const cfg = THREAT_CONFIG[level] ?? THREAT_CONFIG.medium
  const Icon = cfg.icon
  return (
    <Badge variant="outline" className={cn("text-[10px] font-semibold border gap-1", cfg.color)}>
      <Icon className="h-2.5 w-2.5" />
      {cfg.label}
    </Badge>
  )
}

function CapacityBar({ mw, maxMw }: { mw: number; maxMw: number }) {
  const pct = maxMw > 0 ? Math.min(100, (mw / maxMw) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </div>
      <span className="tabular-nums">{mw.toLocaleString()}</span>
    </div>
  )
}

function SortIcon({ sortKey, currentKey, dir }: { sortKey: SortKey; currentKey: SortKey; dir: SortDir }) {
  if (sortKey !== currentKey) return <ArrowUpDown className="ml-1 inline h-3 w-3 text-muted-foreground/50" />
  return dir === "desc"
    ? <ArrowDown className="ml-1 inline h-3 w-3 text-primary" />
    : <ArrowUp className="ml-1 inline h-3 w-3 text-primary" />
}

export default function CompetePage() {
  const [data, setData] = useState<LandscapeData | null>(null)
  const [threats, setThreats] = useState<DealThreatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [battlecard, setBattlecard] = useState<string | null>(null)
  const [bcLoading, setBcLoading] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>("threat_level")
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  const [activeSegment, setActiveSegment] = useState<string | null>(null)
  const [activityFilter, setActivityFilter] = useState<string>("all")

  useEffect(() => {
    Promise.all([
      getLandscape().catch(() => null),
      getDealThreats().catch(() => null),
    ]).then(([landscape, dealThreats]) => {
      setData(landscape)
      setThreats(dealThreats)
      setLoading(false)
    })
  }, [])

  const competitors = useMemo(() => data?.competitors ?? [], [data?.competitors])
  const iren = data?.iren ?? null
  const activityFeed = useMemo(() => data?.activity_feed ?? [], [data?.activity_feed])

  const eventsThisWeek = activityFeed.filter((item) => {
    if (!item.detected_at) return false
    const d = new Date(item.detected_at)
    const week = new Date()
    week.setDate(week.getDate() - 7)
    return d >= week
  }).length

  const hottestCompetitor = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const item of activityFeed) {
      if (!item.detected_at) continue
      const d = new Date(item.detected_at)
      const week = new Date()
      week.setDate(week.getDate() - 7)
      if (d >= week) {
        counts[item.company_name] = (counts[item.company_name] || 0) + 1
      }
    }
    let top = "—"
    let topCount = 0
    for (const [name, count] of Object.entries(counts)) {
      if (count > topCount) {
        top = name
        topCount = count
      }
    }
    return { name: top, count: topCount }
  }, [activityFeed])

  const dealThreatCount = threats?.total_at_risk ?? 0

  const maxCapacity = useMemo(() => {
    const all = [...competitors.map((c) => c.capacity_mw ?? 0)]
    if (iren?.capacity_mw) all.push(iren.capacity_mw)
    return Math.max(...all, 1)
  }, [competitors, iren])

  const segmentCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const c of competitors) {
      counts[c.segment] = (counts[c.segment] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [competitors])

  const filtered = useMemo(() => {
    let list = activeSegment ? competitors.filter((c) => c.segment === activeSegment) : competitors
    list = [...list].sort((a, b) => {
      if (sortKey === "threat_level") {
        const aOrd = THREAT_ORDER[a.threat_level] ?? 1
        const bOrd = THREAT_ORDER[b.threat_level] ?? 1
        return sortDir === "asc" ? aOrd - bOrd : bOrd - aOrd
      }
      const aVal = a[sortKey] ?? (sortKey === "name" ? "" : -1)
      const bVal = b[sortKey] ?? (sortKey === "name" ? "" : -1)
      if (sortKey === "name") {
        return sortDir === "asc"
          ? String(aVal).localeCompare(String(bVal))
          : String(bVal).localeCompare(String(aVal))
      }
      return sortDir === "desc" ? Number(bVal) - Number(aVal) : Number(aVal) - Number(bVal)
    })
    return list
  }, [competitors, activeSegment, sortKey, sortDir])

  const selected = competitors.find((c) => c.id === selectedId) ?? null

  const filteredActivity = useMemo(() => {
    if (activityFilter === "all") return activityFeed
    return activityFeed.filter((item) => item.event_type === activityFilter)
  }, [activityFeed, activityFilter])

  const activityTypesWithCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const item of activityFeed) {
      const t = item.event_type || "other"
      counts[t] = (counts[t] || 0) + 1
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => ({ type, count }))
  }, [activityFeed])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"))
    } else {
      setSortKey(key)
      setSortDir(key === "name" ? "asc" : "desc")
    }
  }

  const openCompetitor = (id: number) => {
    setSelectedId(id)
    setBattlecard(null)
    setBcLoading(true)
    generateBattlecard(id)
      .then((res) => setBattlecard(res.battlecard))
      .catch(() => setBattlecard("Failed to generate battle card."))
      .finally(() => setBcLoading(false))
  }

  const handleBattlecard = async () => {
    if (!selectedId) return
    setBcLoading(true)
    try {
      const res = await generateBattlecard(selectedId)
      setBattlecard(res.battlecard)
    } catch {
      setBattlecard("Failed to generate battle card.")
    } finally {
      setBcLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Compete</h1>
        <p className="text-sm text-muted-foreground">
          Live competitive activity — what happened this week and what it means for your deals
        </p>
      </div>

      {/* Live KPI strip */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
        <Card className="border-border/50 bg-card/50">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-primary/10 p-2">
              <Activity className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-semibold tabular-nums">{eventsThisWeek}</p>
              <p className="text-[11px] text-muted-foreground">events this week</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-amber-400/10 p-2">
              <Flame className="h-5 w-5 text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold tabular-nums truncate">{hottestCompetitor.name}</p>
              <p className="text-[11px] text-muted-foreground">hottest competitor ({hottestCompetitor.count} events)</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardContent className="flex items-center gap-3 p-4">
            <div className="rounded-lg bg-red-400/10 p-2">
              <Target className="h-5 w-5 text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-semibold tabular-nums">{dealThreatCount}</p>
              <p className="text-[11px] text-muted-foreground">prospects with competing activity</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Three-tab layout: Activity (default) → Deal Threats → Directory */}
      <Tabs defaultValue="activity" className="space-y-4">
        <TabsList className="overflow-x-auto">
          <TabsTrigger value="activity" className="gap-1.5">
            <Activity className="h-3.5 w-3.5" /> Activity Feed
          </TabsTrigger>
          <TabsTrigger value="threats" className="gap-1.5">
            <Target className="h-3.5 w-3.5" /> Deal Threats
            {dealThreatCount > 0 && (
              <Badge variant="destructive" className="ml-1 h-4 px-1 text-[10px]">{dealThreatCount}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="directory" className="gap-1.5">
            <BookOpen className="h-3.5 w-3.5" /> Directory
          </TabsTrigger>
        </TabsList>

        {/* ===== TAB 1: ACTIVITY FEED (default) ===== */}
        <TabsContent value="activity" className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant={activityFilter === "all" ? "default" : "outline"} className="h-7 text-xs" onClick={() => setActivityFilter("all")}>
              All{activityFeed.length > 0 ? ` (${activityFeed.length})` : ""}
            </Button>
            {activityTypesWithCounts.map(({ type, count }) => (
              <Button key={type} size="sm" variant={activityFilter === type ? "default" : "outline"} className="h-7 text-xs capitalize" onClick={() => setActivityFilter(type)}>
                {type.replace(/_/g, " ")} ({count})
              </Button>
            ))}
          </div>

          {filteredActivity.length > 0 ? (
            <div className="space-y-2">
              {filteredActivity.map((item, i) => (
                <ActivityItem key={`${item.type}-${item.title}-${i}`} item={item} />
              ))}
            </div>
          ) : (
            <Card className="border-border/50">
              <CardContent className="py-16 text-center text-muted-foreground">
                <Activity className="h-8 w-8 mx-auto mb-3 text-muted-foreground/50" />
                <p>No competitive activity found</p>
                <p className="text-xs mt-1">Run collectors to populate this feed</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ===== TAB 2: DEAL THREATS ===== */}
        <TabsContent value="threats" className="space-y-4">
          {threats && threats.threats.length > 0 ? (
            <div className="space-y-3">
              {threats.threats.map((t) => (
                <DealThreatCard key={t.prospect_id} threat={t} />
              ))}
            </div>
          ) : (
            <Card className="border-border/50">
              <CardContent className="py-16 text-center text-muted-foreground">
                <Target className="h-8 w-8 mx-auto mb-3 text-muted-foreground/50" />
                <p>No deal threats detected</p>
                <p className="text-xs mt-1">Threats appear when competitor activity overlaps with high-scoring prospects</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ===== TAB 3: DIRECTORY ===== */}
        <TabsContent value="directory" className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={activeSegment === null ? "default" : "outline"}
              className="h-7 text-xs"
              onClick={() => setActiveSegment(null)}
            >
              All ({competitors.length})
            </Button>
            {segmentCounts.map(([seg, count]) => (
              <Button
                key={seg}
                size="sm"
                variant={activeSegment === seg ? "default" : "outline"}
                className="h-7 text-xs"
                onClick={() => setActiveSegment(activeSegment === seg ? null : seg)}
              >
                {seg}
                <span className="ml-1 text-muted-foreground">{count}</span>
              </Button>
            ))}
          </div>

          <Card className="border-border/50 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="cursor-pointer select-none text-xs" onClick={() => toggleSort("name")}>
                    Company <SortIcon sortKey="name" currentKey={sortKey} dir={sortDir} />
                  </TableHead>
                  <TableHead className="text-xs">Segment</TableHead>
                  <TableHead className="cursor-pointer select-none text-xs" onClick={() => toggleSort("threat_level")}>
                    Threat <SortIcon sortKey="threat_level" currentKey={sortKey} dir={sortDir} />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none text-xs hidden md:table-cell" onClick={() => toggleSort("capacity_mw")}>
                    MW <SortIcon sortKey="capacity_mw" currentKey={sortKey} dir={sortDir} />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none text-xs text-right hidden md:table-cell" onClick={() => toggleSort("signal_count_30d")}>
                    Activity <SortIcon sortKey="signal_count_30d" currentKey={sortKey} dir={sortDir} />
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {iren && (
                  <TableRow className="border-[#22c55e]/20 bg-[#22c55e]/4 hover:bg-[#22c55e]/7">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-[#22c55e]">{iren.name}</span>
                        <Badge variant="outline" className="text-[10px] font-mono border-[#22c55e]/30 text-[#22c55e]">
                          {iren.ticker}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell><SegmentBadge segment={iren.segment} /></TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] text-[#22c55e] border-[#22c55e]/30">YOU</Badge>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {iren.capacity_mw ? <CapacityBar mw={iren.capacity_mw} maxMw={maxCapacity} /> : "—"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground hidden md:table-cell">—</TableCell>
                  </TableRow>
                )}

                {filtered.map((c) => (
                  <TableRow key={c.id} className="cursor-pointer" onClick={() => openCompetitor(c.id)}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{c.name}</span>
                        {c.is_public && c.ticker && (
                          <Badge variant="outline" className="text-[10px] font-mono">{c.ticker}</Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground">{c.hq_location}</p>
                    </TableCell>
                    <TableCell><SegmentBadge segment={c.segment} /></TableCell>
                    <TableCell><ThreatBadge level={c.threat_level} /></TableCell>
                    <TableCell className="hidden md:table-cell">
                      {c.capacity_mw ? <CapacityBar mw={c.capacity_mw} maxMw={maxCapacity} /> : <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="text-right tabular-nums hidden md:table-cell">
                      {c.signal_count_30d > 0 ? (
                        <span className="inline-flex items-center gap-1">
                          <Activity className="h-3 w-3 text-[#22c55e]" />
                          {c.signal_count_30d}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">0</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}

                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-12 text-center text-muted-foreground">
                      No competitors match this filter.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Detail Sheet with comparison built in */}
      <Sheet open={selectedId !== null} onOpenChange={(open) => { if (!open) setSelectedId(null) }}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          {selected ? (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  <Swords className="h-5 w-5 text-primary" />
                  {selected.name}
                </SheetTitle>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <SegmentBadge segment={selected.segment} />
                  <ThreatBadge level={selected.threat_level} />
                  {selected.website && (
                    <a href={selected.website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                      <Globe className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </SheetHeader>

              <div className="space-y-6 pt-6">
                {/* vs Iren quick comparison */}
                {iren && (
                  <Card className="border-[#22c55e]/20 bg-[#22c55e]/4">
                    <CardContent className="p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-[#22c55e] mb-2">vs Iren</p>
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div>
                          <p className="text-[10px] text-muted-foreground">MW</p>
                          <p className="text-xs font-medium">{selected.capacity_mw?.toLocaleString() ?? "—"}</p>
                          <p className="text-[10px] text-[#22c55e]">{iren.capacity_mw?.toLocaleString() ?? "—"}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted-foreground">GPUs</p>
                          <p className="text-xs font-medium">{selected.gpu_count?.toLocaleString() ?? "—"}</p>
                          <p className="text-[10px] text-[#22c55e]">{iren.gpu_count?.toLocaleString() ?? "—"}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-muted-foreground">Activity</p>
                          <p className="text-xs font-medium">{selected.signal_count_30d}</p>
                          <p className="text-[10px] text-[#22c55e]">—</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {selected.description && (
                  <p className="text-sm text-muted-foreground">{selected.description}</p>
                )}

                <div className="grid grid-cols-2 gap-2">
                  {selected.capacity_mw && (
                    <StatCard label="Capacity" value={`${selected.capacity_mw.toLocaleString()} MW`} />
                  )}
                  {selected.gpu_count && (
                    <StatCard label="GPUs" value={selected.gpu_count.toLocaleString()} />
                  )}
                  {selected.is_public && selected.ticker && (
                    <StatCard label="Ticker" value={selected.ticker} mono />
                  )}
                  <StatCard label="Signals (30d)" value={String(selected.signal_count_30d)} />
                </div>

                {selected.known_pricing && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Pricing Intel</h3>
                      <p className="text-sm text-muted-foreground">{selected.known_pricing}</p>
                    </div>
                  </>
                )}

                {selected.key_customers.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Key Customers</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {selected.key_customers.map((c) => (
                        <Badge key={c} variant="outline" className="text-[10px]">{c}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {(selected.strengths.length > 0 || selected.weaknesses.length > 0) && (
                  <>
                    <Separator />
                    <div className="grid grid-cols-2 gap-4">
                      {selected.strengths.length > 0 && (
                        <div>
                          <h3 className="text-xs font-semibold uppercase tracking-wider text-green-400 mb-2">Strengths</h3>
                          <ul className="space-y-1">
                            {selected.strengths.map((s, i) => (
                              <li key={i} className="text-[11px] text-muted-foreground flex items-start gap-1.5">
                                <TrendingUp className="h-3 w-3 text-green-400 mt-0.5 shrink-0" />
                                {s}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {selected.weaknesses.length > 0 && (
                        <div>
                          <h3 className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-2">Weaknesses</h3>
                          <ul className="space-y-1">
                            {selected.weaknesses.map((w, i) => (
                              <li key={i} className="text-[11px] text-muted-foreground flex items-start gap-1.5">
                                <Shield className="h-3 w-3 text-red-400 mt-0.5 shrink-0" />
                                {w}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </>
                )}

                <Separator />

                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                    <Sparkles className="h-3 w-3 text-primary" /> AI Battle Card
                  </h3>
                  <Button size="sm" variant="outline" onClick={handleBattlecard} disabled={bcLoading} className="gap-1.5">
                    {bcLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Swords className="h-3 w-3" />}
                    {battlecard ? "Regenerate Battle Card" : bcLoading ? "Generating…" : "Generate Battle Card"}
                  </Button>
                  {bcLoading && !battlecard && (
                    <div className="mt-3 rounded-md border border-border/30 bg-muted/30 p-3 space-y-2">
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-5/6" />
                      <Skeleton className="h-3 w-4/6" />
                    </div>
                  )}
                  {battlecard && (
                    <div className="mt-3 rounded-md border border-border/30 bg-muted/30 p-3">
                      <pre className="text-sm whitespace-pre-wrap font-sans">{battlecard}</pre>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground pt-6">Select a competitor to view details.</p>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}

function StatCard({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-md border border-border/30 px-3 py-2">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className={cn("text-sm font-medium tabular-nums", mono && "font-mono")}>{value}</p>
    </div>
  )
}

function DealThreatCard({ threat }: { threat: DealThreat }) {
  return (
    <Card className="border-red-400/20">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Target className="h-4 w-4 text-red-400" />
            <span className="font-medium">{threat.prospect_name}</span>
            <Badge variant="outline" className="text-[10px]">{threat.tier}</Badge>
          </div>
          <span className="text-sm font-semibold tabular-nums">{threat.score}</span>
        </div>
        <div className="flex flex-wrap gap-1.5 mb-3">
          {threat.competing_segments.map((seg) => (
            <SegmentBadge key={seg} segment={seg} />
          ))}
        </div>
        {threat.recent_competitor_moves.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Recent competitor moves</p>
            {threat.recent_competitor_moves.map((move, i) => (
              <div key={i} className="flex items-start gap-2">
                <Badge variant="outline" className={cn("text-[10px] capitalize border shrink-0", EVENT_TYPE_COLORS[move.event_type] ?? "")}>
                  {move.event_type}
                </Badge>
                <div className="min-w-0">
                  <span className="text-xs font-medium">{move.company_name}</span>
                  <p className="text-[11px] text-muted-foreground truncate">{move.title}</p>
                  <p className="text-[10px] text-muted-foreground/60">{formatDate(move.detected_at)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ActivityItem({ item }: { item: ActivityFeedItem }) {
  const colors = EVENT_TYPE_COLORS[item.event_type] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/30"
  return (
    <Card className="border-border/30">
      <CardContent className="flex items-start gap-3 p-3">
        <div className="shrink-0 mt-0.5">
          <Badge variant="outline" className={cn("text-[10px] capitalize border", colors)}>
            {item.event_type}
          </Badge>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-medium">{item.company_name}</span>
            <span className="text-[10px] text-muted-foreground">{formatDate(item.detected_at)}</span>
          </div>
          {item.source_url ? (
            <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground truncate block hover:text-primary hover:underline">
              {item.title}
            </a>
          ) : (
            <p className="text-xs text-muted-foreground truncate">{item.title}</p>
          )}
          {item.description && <p className="text-[11px] text-muted-foreground/70 mt-0.5 line-clamp-2">{item.description}</p>}
        </div>
        {item.source_url && (
          <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="shrink-0 mt-0.5">
            <ExternalLink className="h-3.5 w-3.5 text-muted-foreground hover:text-primary" />
          </a>
        )}
      </CardContent>
    </Card>
  )
}
