"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { SignalBadge } from "@/components/signal-badge"
import { getCompetitors, generateBattlecard } from "@/lib/api"
import { cn, formatDate } from "@/lib/utils"
import type { CompetePageData } from "@/lib/types"
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
} from "lucide-react"

type SortKey = "capacity_mw" | "gpu_count" | "signal_count_30d" | "name"
type SortDir = "asc" | "desc"

const SEGMENT_COLORS: Record<string, string> = {
  "Neocloud": "text-violet-400 bg-violet-400/10 border-violet-400/20",
  "Hyperscaler": "text-blue-400 bg-blue-400/10 border-blue-400/20",
  "DC REIT": "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  "Power-First": "text-orange-400 bg-orange-400/10 border-orange-400/20",
  "International": "text-pink-400 bg-pink-400/10 border-pink-400/20",
  "Data Center": "text-zinc-400 bg-zinc-400/10 border-zinc-400/20",
}

function SegmentBadge({ segment }: { segment: string }) {
  const colors = SEGMENT_COLORS[segment] ?? SEGMENT_COLORS["Data Center"]
  return (
    <Badge variant="outline" className={cn("text-[10px] font-semibold tracking-wider border", colors)}>
      {segment}
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
  const [data, setData] = useState<CompetePageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [battlecard, setBattlecard] = useState<string | null>(null)
  const [bcLoading, setBcLoading] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>("capacity_mw")
  const [sortDir, setSortDir] = useState<SortDir>("desc")
  const [activeSegment, setActiveSegment] = useState<string | null>(null)

  useEffect(() => {
    getCompetitors()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const competitors = useMemo(() => data?.competitors ?? [], [data?.competitors])
  const iren = data?.iren ?? null

  const segments = useMemo(() => {
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

  const irenRank = useMemo(() => {
    if (!iren?.capacity_mw) return null
    const withCapacity = competitors.filter((c) => c.capacity_mw != null)
    const rank = withCapacity.filter((c) => (c.capacity_mw ?? 0) > iren.capacity_mw!).length + 1
    return { rank, of: withCapacity.length + 1 }
  }, [competitors, iren])

  const totalSignals30d = useMemo(
    () => competitors.reduce((sum, c) => sum + c.signal_count_30d, 0),
    [competitors],
  )

  const filtered = useMemo(() => {
    let list = activeSegment ? competitors.filter((c) => c.segment === activeSegment) : competitors
    list = [...list].sort((a, b) => {
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
        <div className="grid gap-4 grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}
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
          Competitive landscape — how Iren stacks up
        </p>
      </div>

      {/* Summary Strip */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Competitors Tracked
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-semibold tabular-nums">{competitors.length}</span>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {segments.map(([seg, count]) => (
                <span key={seg} className="text-[10px] text-muted-foreground">
                  {count} {seg}{segments.indexOf([seg, count]) < segments.length - 1 ? "" : ""}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Iren Capacity Rank
            </CardTitle>
          </CardHeader>
          <CardContent>
            {irenRank ? (
              <>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-semibold tabular-nums text-[#22c55e]">
                    #{irenRank.rank}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    of {irenRank.of}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {iren?.capacity_mw?.toLocaleString()} MW capacity
                </p>
              </>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Competitor Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-semibold tabular-nums">{totalSignals30d}</span>
            <p className="mt-0.5 text-xs text-muted-foreground">signals in last 30 days</p>
          </CardContent>
        </Card>
      </div>

      {/* Segment Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant={activeSegment === null ? "default" : "outline"}
          className="h-7 text-xs"
          onClick={() => setActiveSegment(null)}
        >
          <LayoutGrid className="mr-1 h-3 w-3" /> All
        </Button>
        {segments.map(([seg, count]) => (
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
              <TableHead
                className="cursor-pointer select-none text-xs"
                onClick={() => toggleSort("name")}
              >
                Company <SortIcon sortKey="name" currentKey={sortKey} dir={sortDir} />
              </TableHead>
              <TableHead className="text-xs">Segment</TableHead>
              <TableHead
                className="cursor-pointer select-none text-xs text-right"
                onClick={() => toggleSort("capacity_mw")}
              >
                Capacity (MW) <SortIcon sortKey="capacity_mw" currentKey={sortKey} dir={sortDir} />
              </TableHead>
              <TableHead
                className="cursor-pointer select-none text-xs text-right"
                onClick={() => toggleSort("gpu_count")}
              >
                GPUs <SortIcon sortKey="gpu_count" currentKey={sortKey} dir={sortDir} />
              </TableHead>
              <TableHead
                className="cursor-pointer select-none text-xs text-right"
                onClick={() => toggleSort("signal_count_30d")}
              >
                Signals (30d) <SortIcon sortKey="signal_count_30d" currentKey={sortKey} dir={sortDir} />
              </TableHead>
              <TableHead className="text-xs">Latest Signal</TableHead>
              <TableHead className="text-xs">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Iren benchmark row — always pinned at top */}
            {iren && (
              <TableRow className="border-[#22c55e]/20 bg-[#22c55e]/[0.04] hover:bg-[#22c55e]/[0.07]">
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
                <TableCell className="text-right">
                  {iren.capacity_mw ? (
                    <CapacityBar mw={iren.capacity_mw} maxMw={maxCapacity} />
                  ) : <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {iren.gpu_count ? iren.gpu_count.toLocaleString() : "—"}
                </TableCell>
                <TableCell className="text-right text-muted-foreground">—</TableCell>
                <TableCell className="text-muted-foreground">—</TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-[10px] text-[#22c55e] border-[#22c55e]/30">
                    YOU
                  </Badge>
                </TableCell>
              </TableRow>
            )}

            {/* Competitor rows */}
            {filtered.map((c) => {
              const latestSignal = c.signals[0] ?? null
              return (
                <TableRow
                  key={c.id}
                  className="cursor-pointer"
                  onClick={() => { setSelectedId(c.id); setBattlecard(null) }}
                >
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
                  <TableCell className="text-right">
                    {c.capacity_mw ? (
                      <CapacityBar mw={c.capacity_mw} maxMw={maxCapacity} />
                    ) : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {c.gpu_count ? c.gpu_count.toLocaleString() : "—"}
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
                  <TableCell>
                    {latestSignal ? (
                      <div className="flex items-center gap-1.5 max-w-[200px]">
                        <SignalBadge type={latestSignal.signal_type} />
                        <span className="text-xs text-muted-foreground truncate">{latestSignal.title}</span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">
                      {c.is_public ? "Public" : "Private"}
                    </Badge>
                  </TableCell>
                </TableRow>
              )
            })}

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
                  {selected.hq_location && <><span>·</span><span>{selected.hq_location}</span></>}
                  {selected.website && (
                    <>
                      <span>·</span>
                      <a href={selected.website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                        <Globe className="h-3 w-3" />
                      </a>
                    </>
                  )}
                </div>
              </SheetHeader>

              <div className="space-y-6 pt-6">
                {selected.description && (
                  <p className="text-sm text-muted-foreground">{selected.description}</p>
                )}

                <div className="grid grid-cols-2 gap-2">
                  {selected.employee_count && (
                    <div className="rounded-md border border-border/30 px-3 py-2">
                      <p className="text-[10px] text-muted-foreground">Employees</p>
                      <p className="text-sm font-medium tabular-nums">{selected.employee_count.toLocaleString()}</p>
                    </div>
                  )}
                  {selected.capacity_mw && (
                    <div className="rounded-md border border-border/30 px-3 py-2">
                      <p className="text-[10px] text-muted-foreground">Capacity</p>
                      <p className="text-sm font-medium tabular-nums">{selected.capacity_mw.toLocaleString()} MW</p>
                    </div>
                  )}
                  {selected.gpu_count && (
                    <div className="rounded-md border border-border/30 px-3 py-2">
                      <p className="text-[10px] text-muted-foreground">GPUs</p>
                      <p className="text-sm font-medium tabular-nums">{selected.gpu_count.toLocaleString()}</p>
                    </div>
                  )}
                  {selected.is_public && selected.ticker && (
                    <div className="rounded-md border border-border/30 px-3 py-2">
                      <p className="text-[10px] text-muted-foreground">Ticker</p>
                      <p className="text-sm font-mono font-medium">{selected.ticker}</p>
                    </div>
                  )}
                  <div className="rounded-md border border-border/30 px-3 py-2">
                    <p className="text-[10px] text-muted-foreground">Signals (30d)</p>
                    <p className="text-sm font-medium tabular-nums">{selected.signal_count_30d}</p>
                  </div>
                </div>

                <Separator />

                {/* Events */}
                {selected.events.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Events</h3>
                    <div className="space-y-2">
                      {selected.events.map((e) => (
                        <div key={e.id} className="rounded-md border border-border/30 p-2.5">
                          <div className="flex items-center justify-between mb-1">
                            <Badge variant="outline" className="text-[10px]">{e.event_type}</Badge>
                            <span className="text-[10px] text-muted-foreground">{formatDate(e.detected_at)}</span>
                          </div>
                          <p className="text-xs font-medium">{e.title}</p>
                          {e.description && <p className="text-xs text-muted-foreground mt-0.5">{e.description}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Signals */}
                {selected.signals.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Signals</h3>
                    <div className="space-y-2">
                      {selected.signals.map((s) => (
                        <div key={s.id} className="flex items-start gap-2 rounded-md border border-border/30 p-2.5">
                          <SignalBadge type={s.signal_type} />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium truncate">{s.title}</p>
                            <p className="text-[11px] text-muted-foreground">{formatDate(s.detected_at)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <Separator />

                {/* Battle Card */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                    <Sparkles className="h-3 w-3 text-primary" /> AI Battle Card
                  </h3>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleBattlecard}
                    disabled={bcLoading}
                    className="gap-1.5"
                  >
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
