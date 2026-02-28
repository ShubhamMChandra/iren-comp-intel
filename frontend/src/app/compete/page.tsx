"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { SignalBadge } from "@/components/signal-badge"
import { getLandscape, generateBattlecard } from "@/lib/api"
import { cn, formatDate } from "@/lib/utils"
import type { LandscapeData, Competitor, ActivityFeedItem } from "@/lib/types"
import {
  Globe,
  Swords,
  Sparkles,
  Loader2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Activity,
  LayoutGrid,
  Shield,
  TrendingUp,
  Zap,
  ChevronRight,
  ExternalLink,
  AlertTriangle,
  CheckCircle,
  MinusCircle,
} from "lucide-react"

type SortKey = "capacity_mw" | "gpu_count" | "signal_count_30d" | "name" | "threat_level"
type SortDir = "asc" | "desc"

const SEGMENT_COLORS: Record<string, string> = {
  "Neocloud": "text-violet-400 bg-violet-400/10 border-violet-400/20",
  "Hyperscaler": "text-blue-400 bg-blue-400/10 border-blue-400/20",
  "DC REIT": "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  "Power-First": "text-orange-400 bg-orange-400/10 border-orange-400/20",
  "International": "text-pink-400 bg-pink-400/10 border-pink-400/20",
  "Data Center": "text-zinc-400 bg-zinc-400/10 border-zinc-400/20",
}

const THREAT_CONFIG: Record<string, { color: string; icon: typeof AlertTriangle; label: string }> = {
  high: { color: "text-red-400 bg-red-400/10 border-red-400/30", icon: AlertTriangle, label: "High Threat" },
  medium: { color: "text-amber-400 bg-amber-400/10 border-amber-400/30", icon: MinusCircle, label: "Medium" },
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
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [battlecard, setBattlecard] = useState<string | null>(null)
  const [bcLoading, setBcLoading] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>("capacity_mw")
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  const [activeSegment, setActiveSegment] = useState<string | null>(null)
  const [compareA, setCompareA] = useState<string>("")
  const [compareB, setCompareB] = useState<string>("")
  const [activityFilter, setActivityFilter] = useState<string>("all")

  useEffect(() => {
    getLandscape()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const competitors = useMemo(() => data?.competitors ?? [], [data?.competitors])
  const iren = data?.iren ?? null
  const segments = data?.segments ?? []
  const activityFeed = data?.activity_feed ?? []

  const segmentCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const c of competitors) {
      counts[c.segment] = (counts[c.segment] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [competitors])

  const maxCapacity = useMemo(() => {
    const all = [...competitors.map((c) => c.capacity_mw ?? 0)]
    if (iren?.capacity_mw) all.push(iren.capacity_mw)
    return Math.max(...all, 1)
  }, [competitors, iren])

  const highThreatCount = useMemo(() => competitors.filter((c) => c.threat_level === "high").length, [competitors])
  const totalSignals30d = useMemo(() => competitors.reduce((sum, c) => sum + c.signal_count_30d, 0), [competitors])

  const threatOrder: Record<string, number> = { high: 0, medium: 1, low: 2 }

  const filtered = useMemo(() => {
    let list = activeSegment ? competitors.filter((c) => c.segment === activeSegment) : competitors
    list = [...list].sort((a, b) => {
      if (sortKey === "threat_level") {
        const aOrd = threatOrder[a.threat_level] ?? 1
        const bOrd = threatOrder[b.threat_level] ?? 1
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

  const compA = useMemo(() => {
    if (compareA === "iren") return null
    return competitors.find((c) => String(c.id) === compareA) ?? null
  }, [competitors, compareA])
  const compB = useMemo(() => competitors.find((c) => String(c.id) === compareB) ?? null, [competitors, compareB])

  const filteredActivity = useMemo(() => {
    if (activityFilter === "all") return activityFeed
    return activityFeed.filter((item) => item.event_type === activityFilter)
  }, [activityFeed, activityFilter])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"))
    } else {
      setSortKey(key)
      setSortDir(key === "name" ? "asc" : "desc")
    }
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
        <div className="grid gap-4 grid-cols-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
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
          GTM competitive intelligence — positioning, threats, and market activity
        </p>
      </div>

      {/* Summary KPIs */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-4">
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Competitors Tracked
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-semibold tabular-nums">{competitors.length}</span>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {segmentCounts.map(([seg, count]) => (
                <span key={seg} className="text-[10px] text-muted-foreground">{count} {seg}</span>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              High Threat
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-semibold tabular-nums text-red-400">{highThreatCount}</span>
            <p className="mt-0.5 text-xs text-muted-foreground">competitors rated high threat to Iren</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Activity (30d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-semibold tabular-nums">{totalSignals30d}</span>
            <p className="mt-0.5 text-xs text-muted-foreground">competitor signals tracked</p>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Segments
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-semibold tabular-nums">{segments.length}</span>
            <p className="mt-0.5 text-xs text-muted-foreground">market segments profiled</p>
          </CardContent>
        </Card>
      </div>

      {/* Three-tab layout */}
      <Tabs defaultValue="landscape" className="space-y-4">
        <TabsList>
          <TabsTrigger value="landscape" className="gap-1.5">
            <LayoutGrid className="h-3.5 w-3.5" /> Market Landscape
          </TabsTrigger>
          <TabsTrigger value="headtohead" className="gap-1.5">
            <Swords className="h-3.5 w-3.5" /> Head-to-Head
          </TabsTrigger>
          <TabsTrigger value="activity" className="gap-1.5">
            <Activity className="h-3.5 w-3.5" /> Activity Feed
          </TabsTrigger>
        </TabsList>

        {/* ===== TAB 1: MARKET LANDSCAPE ===== */}
        <TabsContent value="landscape" className="space-y-4">
          {/* Segment overview cards */}
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {segments.map((seg) => (
              <Card
                key={seg.name}
                className={cn(
                  "border-border/50 cursor-pointer transition-colors",
                  activeSegment === seg.name ? "border-primary/50 bg-primary/5" : "hover:border-border",
                )}
                onClick={() => setActiveSegment(activeSegment === seg.name ? null : seg.name)}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <SegmentBadge segment={seg.name} />
                    <span className="text-lg font-semibold tabular-nums">{seg.competitor_count}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">{seg.iren_positioning}</p>
                  <div className="mt-2 flex items-center gap-1">
                    <Zap className="h-3 w-3 text-amber-400" />
                    <span className="text-[10px] text-muted-foreground">{seg.key_battleground}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Segment filter pills */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant={activeSegment === null ? "default" : "outline"}
              className="h-7 text-xs"
              onClick={() => setActiveSegment(null)}
            >
              <LayoutGrid className="mr-1 h-3 w-3" /> All
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

          {/* Competitor Table */}
          <Card className="border-border/50">
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
                  <TableHead className="cursor-pointer select-none text-xs text-right" onClick={() => toggleSort("capacity_mw")}>
                    Capacity (MW) <SortIcon sortKey="capacity_mw" currentKey={sortKey} dir={sortDir} />
                  </TableHead>
                  <TableHead className="cursor-pointer select-none text-xs text-right" onClick={() => toggleSort("gpu_count")}>
                    GPUs <SortIcon sortKey="gpu_count" currentKey={sortKey} dir={sortDir} />
                  </TableHead>
                  <TableHead className="text-xs">Key Customers</TableHead>
                  <TableHead className="cursor-pointer select-none text-xs text-right" onClick={() => toggleSort("signal_count_30d")}>
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
                      <p className="text-[11px] text-muted-foreground">{iren.hq_location}</p>
                    </TableCell>
                    <TableCell><SegmentBadge segment={iren.segment} /></TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] text-[#22c55e] border-[#22c55e]/30">YOU</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {iren.capacity_mw ? <CapacityBar mw={iren.capacity_mw} maxMw={maxCapacity} /> : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {iren.gpu_count ? iren.gpu_count.toLocaleString() : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[150px] truncate">
                      {iren.key_customers?.join(", ") || "—"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">—</TableCell>
                  </TableRow>
                )}

                {filtered.map((c) => (
                  <TableRow key={c.id} className="cursor-pointer" onClick={() => { setSelectedId(c.id); setBattlecard(null) }}>
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
                    <TableCell className="text-right">
                      {c.capacity_mw ? <CapacityBar mw={c.capacity_mw} maxMw={maxCapacity} /> : <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {c.gpu_count ? c.gpu_count.toLocaleString() : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[150px] truncate">
                      {c.key_customers.length > 0 ? c.key_customers.slice(0, 3).join(", ") : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
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
                    <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">
                      No competitors match this filter.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* ===== TAB 2: HEAD-TO-HEAD ===== */}
        <TabsContent value="headtohead" className="space-y-4">
          <div className="flex items-center gap-3">
            <Select value={compareA} onValueChange={setCompareA}>
              <SelectTrigger className="w-[220px]">
                <SelectValue placeholder="Select first..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="iren">Iren (You)</SelectItem>
                {competitors.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="text-muted-foreground font-medium">vs</span>
            <Select value={compareB} onValueChange={setCompareB}>
              <SelectTrigger className="w-[220px]">
                <SelectValue placeholder="Select second..." />
              </SelectTrigger>
              <SelectContent>
                {competitors.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {(compareA || compareB) ? (
            <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
              {/* Side A */}
              <ComparisonCard
                title={compareA === "iren" ? "Iren" : compA?.name ?? "Select a competitor"}
                isIren={compareA === "iren"}
                competitor={compA}
                iren={iren}
              />
              {/* Side B */}
              <ComparisonCard
                title={compB?.name ?? "Select a competitor"}
                isIren={false}
                competitor={compB}
                iren={iren}
              />
            </div>
          ) : (
            <Card className="border-border/50">
              <CardContent className="py-16 text-center text-muted-foreground">
                <Swords className="h-8 w-8 mx-auto mb-3 text-muted-foreground/50" />
                <p>Select two competitors to compare side-by-side</p>
                <p className="text-xs mt-1">You can also compare Iren against any competitor</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ===== TAB 3: ACTIVITY FEED ===== */}
        <TabsContent value="activity" className="space-y-4">
          <div className="flex items-center gap-2">
            <Button size="sm" variant={activityFilter === "all" ? "default" : "outline"} className="h-7 text-xs" onClick={() => setActivityFilter("all")}>
              All
            </Button>
            {["deal", "expansion", "pricing", "talent"].map((type) => (
              <Button key={type} size="sm" variant={activityFilter === type ? "default" : "outline"} className="h-7 text-xs capitalize" onClick={() => setActivityFilter(type)}>
                {type}
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
                <p className="text-xs mt-1">Run the competitive intel collector to populate this feed</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Detail Sheet */}
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
                    Generate Battle Card
                  </Button>
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

function ComparisonCard({
  title,
  isIren,
  competitor,
  iren,
}: {
  title: string
  isIren: boolean
  competitor: Competitor | null
  iren: LandscapeData["iren"] | null
}) {
  if (isIren && iren) {
    return (
      <Card className="border-[#22c55e]/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg text-[#22c55e]">{iren.name}</CardTitle>
          <p className="text-xs text-muted-foreground">{iren.industry}</p>
        </CardHeader>
        <CardContent className="space-y-3">
          <Row label="Capacity" value={iren.capacity_mw ? `${iren.capacity_mw.toLocaleString()} MW` : "—"} />
          <Row label="GPUs" value={iren.gpu_count ? iren.gpu_count.toLocaleString() : "—"} />
          <Row label="Pricing" value={iren.known_pricing || "—"} />
          <Row label="Customers" value={iren.key_customers?.join(", ") || "—"} />
          <Separator />
          {iren.strengths && iren.strengths.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase text-green-400 mb-1">Strengths</p>
              <ul className="space-y-0.5">
                {iren.strengths.map((s, i) => <li key={i} className="text-[11px] text-muted-foreground">+ {s}</li>)}
              </ul>
            </div>
          )}
          {iren.weaknesses && iren.weaknesses.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase text-red-400 mb-1">Weaknesses</p>
              <ul className="space-y-0.5">
                {iren.weaknesses.map((w, i) => <li key={i} className="text-[11px] text-muted-foreground">- {w}</li>)}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  if (!competitor) {
    return (
      <Card className="border-border/50">
        <CardContent className="py-16 text-center text-muted-foreground text-sm">
          {title}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg">{competitor.name}</CardTitle>
          <ThreatBadge level={competitor.threat_level} />
        </div>
        <div className="flex items-center gap-2">
          <SegmentBadge segment={competitor.segment} />
          <span className="text-xs text-muted-foreground">{competitor.hq_location}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Row label="Capacity" value={competitor.capacity_mw ? `${competitor.capacity_mw.toLocaleString()} MW` : "—"} />
        <Row label="GPUs" value={competitor.gpu_count ? competitor.gpu_count.toLocaleString() : "—"} />
        <Row label="Pricing" value={competitor.known_pricing || "—"} />
        <Row label="Customers" value={competitor.key_customers.length > 0 ? competitor.key_customers.join(", ") : "—"} />
        <Separator />
        {competitor.strengths.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase text-green-400 mb-1">Strengths</p>
            <ul className="space-y-0.5">
              {competitor.strengths.map((s, i) => <li key={i} className="text-[11px] text-muted-foreground">+ {s}</li>)}
            </ul>
          </div>
        )}
        {competitor.weaknesses.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase text-red-400 mb-1">Weaknesses</p>
            <ul className="space-y-0.5">
              {competitor.weaknesses.map((w, i) => <li key={i} className="text-[11px] text-muted-foreground">- {w}</li>)}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-[11px] text-muted-foreground shrink-0">{label}</span>
      <span className="text-[11px] text-right">{value}</span>
    </div>
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
          <p className="text-xs text-muted-foreground truncate">{item.title}</p>
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
