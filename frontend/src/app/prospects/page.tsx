"use client"

import { useEffect, useState, useMemo, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { ScoreBadge } from "@/components/score-badge"
import { SignalBadge } from "@/components/signal-badge"
import { DeltaValue } from "@/components/delta-value"
import { DrillDown } from "@/components/drill-down"
import { ScoreBreakdownDetail } from "@/components/drill-downs"
import { getProspects, getProspect, generateBrief, generateEmail } from "@/lib/api"
import { cn, formatDate } from "@/lib/utils"
import type { Prospect, Tier } from "@/lib/types"
import { ArrowUpDown, ArrowUp, ArrowDown, Search, Sparkles, Mail, ExternalLink, Loader2 } from "lucide-react"

const TIER_ORDER: Record<Tier, number> = { "VERY HIGH": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "DORMANT": 4 }

const columns: ColumnDef<Prospect>[] = [
  {
    accessorKey: "name",
    header: "Company",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    enableSorting: true,
  },
  {
    accessorKey: "industry",
    header: "Industry",
    cell: ({ row }) => <span className="text-muted-foreground">{row.original.industry}</span>,
  },
  {
    id: "score",
    accessorFn: (row) => row.score?.total ?? 0,
    header: "Score",
    cell: ({ row }) => {
      const score = row.original.score
      if (!score) return <span className="text-zinc-600">—</span>
      const { total, scored_at, ...breakdown } = score
      return (
        <DrillDown
          title="Score Breakdown"
          content={<ScoreBreakdownDetail breakdown={breakdown} total={total} />}
        >
          <span className="font-mono font-medium tabular-nums">{total.toFixed(1)}</span>
        </DrillDown>
      )
    },
    enableSorting: true,
  },
  {
    accessorKey: "delta",
    header: "Delta",
    cell: ({ row }) => <DeltaValue delta={row.original.delta} />,
    enableSorting: true,
  },
  {
    id: "tier",
    accessorFn: (row) => TIER_ORDER[row.tier] ?? 5,
    header: "Tier",
    cell: ({ row }) => <ScoreBadge tier={row.original.tier} />,
    filterFn: (row, _columnId, filterValue) => {
      if (!filterValue || filterValue === "all") return true
      return row.original.tier === filterValue
    },
    enableSorting: true,
  },
  {
    accessorKey: "signals_7d",
    header: "Signals",
    cell: ({ row }) => (
      <span className="tabular-nums text-muted-foreground">{row.original.signals_7d}</span>
    ),
    enableSorting: true,
  },
  {
    id: "top_signal",
    accessorFn: (row) => row.top_signal_type,
    header: "Top Signal",
    cell: ({ row }) =>
      row.original.top_signal_type ? (
        <SignalBadge type={row.original.top_signal_type} />
      ) : (
        <span className="text-zinc-600">—</span>
      ),
    enableSorting: false,
  },
  {
    accessorKey: "hq_location",
    header: "HQ",
    cell: ({ row }) => <span className="text-xs text-muted-foreground">{row.original.hq_location}</span>,
  },
]

function ProspectsPageInner() {
  const searchParams = useSearchParams()
  const [prospects, setProspects] = useState<Prospect[]>([])
  const [loading, setLoading] = useState(true)
  const [sorting, setSorting] = useState<SortingState>([{ id: "score", desc: true }])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [globalFilter, setGlobalFilter] = useState("")

  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<Prospect | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [brief, setBrief] = useState<string | null>(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const [email, setEmail] = useState<string | null>(null)
  const [emailLoading, setEmailLoading] = useState(false)

  useEffect(() => {
    getProspects()
      .then(setProspects)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const table = useReactTable({
    data: prospects,
    columns,
    state: { sorting, columnFilters, globalFilter },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const openDetail = async (id: number) => {
    setSelectedId(id)
    setDetail(null)
    setBrief(null)
    setEmail(null)
    setDetailLoading(true)
    try {
      const d = await getProspect(id)
      setDetail(d)
    } catch {
      // ignore
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    const idParam = searchParams.get("id")
    if (idParam) openDetail(Number(idParam))
    // openDetail is stable — recreated each render but effect only re-runs when searchParams changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const handleGenerateBrief = async () => {
    if (!selectedId) return
    setBriefLoading(true)
    try {
      const res = await generateBrief(selectedId)
      setBrief(res.brief)
    } catch {
      setBrief("Failed to generate brief.")
    } finally {
      setBriefLoading(false)
    }
  }

  const handleGenerateEmail = async () => {
    if (!selectedId) return
    setEmailLoading(true)
    try {
      const res = await generateEmail(selectedId)
      setEmail(res.email)
    } catch {
      setEmail("Failed to generate email.")
    } finally {
      setEmailLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Prospects</h1>
          <p className="text-sm text-muted-foreground">{prospects.length} companies tracked</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search companies..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="pl-9 bg-card/50"
          />
        </div>
        <Select
          value={(table.getColumn("tier")?.getFilterValue() as string) || "all"}
          onValueChange={(v) => table.getColumn("tier")?.setFilterValue(v === "all" ? undefined : v)}
        >
          <SelectTrigger className="w-40 bg-card/50">
            <SelectValue placeholder="All Tiers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Tiers</SelectItem>
            <SelectItem value="VERY HIGH">Very High</SelectItem>
            <SelectItem value="HIGH">High</SelectItem>
            <SelectItem value="MEDIUM">Medium</SelectItem>
            <SelectItem value="LOW">Low</SelectItem>
            <SelectItem value="DORMANT">Dormant</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground tabular-nums">
          {table.getFilteredRowModel().rows.length} results
        </span>
      </div>

      {/* Table */}
      <Card className="bg-card/50">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="border-b border-border/50">
                    {headerGroup.headers.map((header) => (
                      <th
                        key={header.id}
                        className={cn(
                          "px-4 py-3 text-left text-[11px] font-medium uppercase tracking-wider text-muted-foreground",
                          header.column.getCanSort() && "cursor-pointer select-none hover:text-foreground"
                        )}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getCanSort() && (
                            header.column.getIsSorted() === "asc" ? (
                              <ArrowUp className="h-3 w-3" />
                            ) : header.column.getIsSorted() === "desc" ? (
                              <ArrowDown className="h-3 w-3" />
                            ) : (
                              <ArrowUpDown className="h-3 w-3 opacity-30" />
                            )
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-border/30 cursor-pointer transition-colors hover:bg-accent/50"
                    onClick={() => openDetail(row.original.id)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-2.5">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
                {table.getRowModel().rows.length === 0 && (
                  <tr>
                    <td colSpan={columns.length} className="px-4 py-12 text-center text-muted-foreground">
                      No prospects match your filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Detail Sheet */}
      <Sheet open={selectedId !== null} onOpenChange={(open) => { if (!open) setSelectedId(null) }}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          {detailLoading ? (
            <div className="space-y-4 pt-6">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-32" />
            </div>
          ) : detail ? (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-3">
                  {detail.name}
                  <ScoreBadge tier={detail.tier} />
                </SheetTitle>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{detail.industry}</span>
                  <span>·</span>
                  <span>{detail.hq_location}</span>
                  {detail.website && (
                    <>
                      <span>·</span>
                      <a href={detail.website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                        Website <ExternalLink className="h-3 w-3" />
                      </a>
                    </>
                  )}
                </div>
              </SheetHeader>

              <div className="space-y-6 pt-6">
                {detail.description && (
                  <p className="text-sm text-muted-foreground">{detail.description}</p>
                )}

                {/* Score Breakdown */}
                {detail.score && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Score Breakdown</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(detail.score).filter(([k]) => k !== "total" && k !== "scored_at").map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between rounded-md border border-border/30 px-3 py-2">
                          <span className="text-xs text-muted-foreground capitalize">{key.replace("_", " ")}</span>
                          <span className="font-mono text-sm tabular-nums">{(val as number).toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex items-center justify-between rounded-md border border-primary/30 bg-primary/5 px-3 py-2">
                      <span className="text-xs font-semibold text-primary">TOTAL</span>
                      <span className="font-mono text-lg font-bold tabular-nums">{detail.score.total.toFixed(1)}</span>
                    </div>
                  </div>
                )}

                {/* Score Story */}
                {detail.score_story && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                      <Sparkles className="h-3 w-3 text-primary" /> AI Score Story
                    </h3>
                    <p className="text-sm text-muted-foreground italic">{detail.score_story}</p>
                  </div>
                )}

                <Separator />

                {/* Recent Signals */}
                {detail.signals && detail.signals.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Recent Signals</h3>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {detail.signals.map((s) => (
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

                {/* AI Actions */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                    <Sparkles className="h-3 w-3 text-primary" /> AI Actions
                  </h3>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleGenerateBrief}
                      disabled={briefLoading}
                      className="gap-1.5"
                    >
                      {briefLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                      Generate Brief
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleGenerateEmail}
                      disabled={emailLoading}
                      className="gap-1.5"
                    >
                      {emailLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
                      Draft Email
                    </Button>
                  </div>

                  {brief && (
                    <div className="mt-3 rounded-md border border-border/30 bg-muted/30 p-3">
                      <p className="text-xs font-semibold text-muted-foreground mb-1">Sales Brief</p>
                      <p className="text-sm whitespace-pre-wrap">{brief}</p>
                    </div>
                  )}
                  {email && (
                    <div className="mt-3 rounded-md border border-border/30 bg-muted/30 p-3">
                      <p className="text-xs font-semibold text-muted-foreground mb-1">Outreach Email</p>
                      <pre className="text-sm whitespace-pre-wrap font-sans">{email}</pre>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground pt-6">Failed to load prospect details.</p>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}

export default function ProspectsPage() {
  return (
    <Suspense>
      <ProspectsPageInner />
    </Suspense>
  )
}
