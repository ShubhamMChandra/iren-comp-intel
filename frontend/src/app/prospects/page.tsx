"use client"

import { useEffect, useState, Suspense } from "react"
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
import { Badge } from "@/components/ui/badge"
import { ScoreBadge } from "@/components/score-badge"
import { SignalBadge } from "@/components/signal-badge"
import { ProductBadge } from "@/components/product-badge"
import { DeltaValue } from "@/components/delta-value"
import { getProspects, getProspect, generateBrief, generateEmail, getCompetitiveContext } from "@/lib/api"
import { cn, formatDate, computeDeadline, ROLE_TYPE_COLORS, ROLE_TYPE_LABELS, URGENCY_BADGE_COLORS } from "@/lib/utils"
import type { CompetitiveContext, Prospect, Tier } from "@/lib/types"
import { SourceBadge } from "@/components/source-badge"
import { ArrowUpDown, ArrowUp, ArrowDown, Search, Sparkles, Mail, ExternalLink, Loader2, Users, Zap, Clock } from "lucide-react"
import ReactMarkdown from "react-markdown"

const TIER_ORDER: Record<Tier, number> = { "VERY HIGH": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "DORMANT": 4 }

// --- Brief formatting ---

function FormattedBrief({ text }: { text: string }) {
  return (
    <div className="text-foreground/90">
      <ReactMarkdown
        components={{
          p: ({ children }) => (
            <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>
          ),
          strong: ({ children }) => {
            const str = String(children)
            const isSectionHeader = /^(THESIS|URGENCY|LEAD WITH|DECISION MAKERS|COMPETITIVE CONTEXT)$/i.test(str.trim())
            return isSectionHeader ? (
              <span className="block text-[11px] font-bold uppercase tracking-wider text-foreground/70 mt-3 mb-0.5 first:mt-0">
                {str}
              </span>
            ) : (
              <strong className="font-semibold text-foreground">{children}</strong>
            )
          },
          ul: ({ children }) => (
            <ul className="space-y-1 my-1.5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="space-y-1 my-1.5 list-decimal list-inside">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-sm leading-relaxed flex gap-1.5">
              <span className="text-foreground/50 shrink-0 mt-0.5">–</span>
              <span>{children}</span>
            </li>
          ),
          h1: ({ children }) => (
            <p className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mt-3 mb-0.5 first:mt-0">{children}</p>
          ),
          h2: ({ children }) => (
            <p className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mt-3 mb-0.5 first:mt-0">{children}</p>
          ),
          h3: ({ children }) => (
            <p className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mt-3 mb-0.5 first:mt-0">{children}</p>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}

// --- Table columns ---

const columns: ColumnDef<Prospect>[] = [
  {
    accessorKey: "name",
    header: "Company",
    cell: ({ row }) => (
      <div className="flex items-center gap-2 min-w-[160px]">
        <span className="font-medium whitespace-nowrap">{row.original.name}</span>
        <ProductBadge productFit={row.original.product_fit} />
      </div>
    ),
    enableSorting: true,
  },
  {
    accessorKey: "industry",
    header: "Industry",
    meta: { hideOnMobile: true },
    cell: ({ row }) => <span className="text-muted-foreground">{row.original.industry}</span>,
  },
  {
    id: "score",
    accessorFn: (row) => row.score?.total ?? 0,
    header: "Score",
    meta: { align: "right" as const },
    cell: ({ row }) => {
      const score = row.original.score
      if (!score) return <span className="text-zinc-600">—</span>
      return <span className="font-mono font-medium tabular-nums">{score.total.toFixed(1)}</span>
    },
    enableSorting: true,
  },
  {
    accessorKey: "delta",
    header: "Delta",
    meta: { align: "right" as const },
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
    meta: { align: "right" as const },
    cell: ({ row }) => (
      <span className="font-mono tabular-nums text-muted-foreground">{row.original.signals_7d}</span>
    ),
    enableSorting: true,
  },
  {
    id: "top_signal",
    accessorFn: (row) => row.top_signal_type,
    header: "Top Signal",
    meta: { hideOnMobile: true },
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
    meta: { hideOnMobile: true },
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
  const [detailError, setDetailError] = useState(false)
  const [brief, setBrief] = useState<string | null>(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const [email, setEmail] = useState<string | null>(null)
  const [emailLoading, setEmailLoading] = useState(false)
  const [compContext, setCompContext] = useState<CompetitiveContext | null>(null)

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
    setDetailError(false)
    setBrief(null)
    setEmail(null)
    setCompContext(null)
    setDetailLoading(true)
    setBriefLoading(true)
    try {
      const d = await getProspect(id)
      setDetail(d)
      getCompetitiveContext(id).then(setCompContext).catch(() => {})
      generateBrief(id)
        .then((res) => setBrief(res.brief))
        .catch(() => setBrief("Failed to generate brief."))
        .finally(() => setBriefLoading(false))
    } catch (err) {
      console.error("Failed to load prospect detail:", err)
      setDetailError(true)
      setBriefLoading(false)
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    const idParam = searchParams.get("id")
    if (idParam) openDetail(Number(idParam))
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
      <div className="flex flex-wrap items-center gap-3">
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
                    {headerGroup.headers.map((header) => {
                      const meta = header.column.columnDef.meta as { align?: string; hideOnMobile?: boolean } | undefined
                      const isRight = meta?.align === "right"
                      const hideOnMobile = meta?.hideOnMobile
                      return (
                        <th
                          key={header.id}
                          className={cn(
                            "px-3 py-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground",
                            isRight ? "text-right" : "text-left",
                            header.column.getCanSort() && "cursor-pointer select-none transition-colors hover:bg-muted/30 hover:text-foreground rounded",
                            hideOnMobile && "hidden md:table-cell"
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <div className={cn("flex items-center gap-1", isRight && "justify-end")}>
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
                      )
                    })}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                    <tr
                    key={row.id}
                    className="border-b border-border/30 cursor-pointer transition-colors hover:bg-muted/20"
                    onClick={() => openDetail(row.original.id)}
                  >
                    {row.getVisibleCells().map((cell) => {
                      const meta = cell.column.columnDef.meta as { align?: string; hideOnMobile?: boolean } | undefined
                      const isRight = meta?.align === "right"
                      const hideOnMobile = meta?.hideOnMobile
                      return (
                        <td key={cell.id} className={cn("px-3 py-2", isRight && "text-right", hideOnMobile && "hidden md:table-cell")}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      )
                    })}
                  </tr>
                ))}
                {table.getRowModel().rows.length === 0 && (
                  <tr>
                    <td colSpan={columns.length} className="px-3 py-12 text-center text-muted-foreground">
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
          {!detail && (
            <SheetTitle className="sr-only">Prospect details</SheetTitle>
          )}
          {detailLoading ? (
            <div className="space-y-4 pt-6">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-32" />
            </div>
          ) : detailError ? (
            <p className="text-sm text-red-400 pt-6">Failed to load prospect details.</p>
          ) : detail ? (
            <>
              {/* 1. Header */}
              <SheetHeader>
                <SheetTitle className="flex items-center gap-3">
                  {detail.name}
                  <ScoreBadge tier={detail.tier} />
                  <ProductBadge productFit={detail.product_fit} />
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
                {/* 2. AI Actions — prominent, at top */}
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
                      className="gap-1.5 transition-transform active:scale-[0.97]"
                    >
                      {briefLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                      {brief ? "Regenerate Brief" : briefLoading ? "Generating…" : "Generate Brief"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleGenerateEmail}
                      disabled={emailLoading}
                      className="gap-1.5 transition-transform active:scale-[0.97]"
                    >
                      {emailLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
                      Draft Email
                    </Button>
                  </div>

                  {/* 3. Brief/Email output inline */}
                  {briefLoading && !brief && (
                    <div className="mt-3 rounded-md border border-border/50 bg-muted/20 p-4 space-y-2">
                      <p className="text-xs font-semibold text-foreground/80 mb-2">Sales Brief</p>
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-5/6" />
                      <Skeleton className="h-3 w-4/6" />
                    </div>
                  )}
                  {brief && (
                    <div className="mt-3 rounded-md border border-border/50 bg-muted/20 p-4">
                      <p className="text-xs font-semibold text-foreground/80 mb-2">Sales Brief</p>
                      <FormattedBrief text={brief} />
                    </div>
                  )}
                  {email && (
                    <div className="mt-3 rounded-md border border-border/50 bg-muted/20 p-4">
                      <p className="text-xs font-semibold text-foreground/80 mb-1">Outreach Email</p>
                      <pre className="text-sm whitespace-pre-wrap font-sans text-foreground/90">{email}</pre>
                    </div>
                  )}
                </div>

                <Separator />

                {/* 3.5 Engagement Windows */}
                {detail.engagement_windows && detail.engagement_windows.length > 0 && (
                  <>
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                        <Clock className="h-3 w-3" /> Engagement Windows
                      </h3>
                      <div className="space-y-3">
                        {detail.engagement_windows.map((ew, i) => (
                          <div key={i} className="rounded-md border border-border/50 px-3 py-2.5">
                            <div className="grid grid-cols-[minmax(7rem,auto)_1fr_auto] gap-x-3 gap-y-1.5 items-baseline">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <SignalBadge type={ew.signal_type} />
                                <Badge
                                  variant="outline"
                                  className={cn("text-[10px] font-semibold border shrink-0", URGENCY_BADGE_COLORS[ew.urgency] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/20")}
                                >
                                  {ew.urgency}
                                </Badge>
                              </div>
                              <span className="col-start-3 text-xs font-medium tabular-nums text-foreground/80 shrink-0">{ew.window}</span>
                              <p className="col-span-3 text-[13px] leading-relaxed text-foreground/85 mt-0.5">{ew.insight}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <Separator />
                  </>
                )}

                {/* 4. Signals — structured reasoning chain */}
                {detail.signals && detail.signals.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                      <Zap className="h-3 w-3" /> Recent Signals
                    </h3>
                    <div className="space-y-2 max-h-80 overflow-y-auto">
                      {detail.signals.map((s) => {
                        const deadline = computeDeadline(s.detected_at ?? "", s.action_window)
                        const [soWhat, doThis] = (s.action_insight ?? "").split(" → ")
                        return (
                          <div key={s.id} className="rounded-md border border-border/30 px-3 py-2.5">
                            <div className="flex items-center justify-between gap-2 mb-1.5">
                              <div className="flex items-center gap-1.5 shrink-0">
                                <SignalBadge type={s.signal_type} />
                                {s.urgency && s.urgency !== "LOW" && (
                                  <Badge
                                    variant="outline"
                                    className={cn("text-[10px] font-semibold border", URGENCY_BADGE_COLORS[s.urgency] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/20")}
                                  >
                                    {s.urgency}
                                  </Badge>
                                )}
                                <SourceBadge sourceType={s.source_type} />
                              </div>
                              <span className="text-[11px] text-muted-foreground/60 shrink-0">{formatDate(s.detected_at)}</span>
                            </div>
                            <p className="text-xs leading-relaxed">{s.title}</p>
                            {soWhat && (
                              <>
                                <div className="border-t border-border/20 my-2" />
                                <p className="text-xs text-muted-foreground">
                                  <span className="font-medium text-muted-foreground/50">So what: </span>{soWhat}
                                </p>
                                {doThis && (
                                  <p className="text-xs mt-0.5 text-[#22c55e]">
                                    → {doThis}
                                  </p>
                                )}
                              </>
                            )}
                            {(deadline || s.source_url) && (
                              <div className="flex items-center justify-end gap-2 mt-2">
                                {deadline && (
                                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-md border border-amber-400/20 bg-amber-400/8 text-amber-400/80">
                                    Act by {deadline}
                                  </span>
                                )}
                                {s.source_url && (
                                  <a
                                    href={s.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-muted-foreground/40 hover:text-[#22c55e] transition-colors"
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                <Separator />

                {/* 5. Key Stakeholders — compact list */}
                {detail.contacts && detail.contacts.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                      <Users className="h-3 w-3" /> Key Stakeholders
                    </h3>
                    <div className="divide-y divide-border/30">
                      {detail.contacts.map((contact) => (
                        <div key={contact.id} className="py-2 first:pt-0 last:pb-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">{contact.title}</span>
                            <span className="text-muted-foreground/40">·</span>
                            <span className="text-sm font-medium">{contact.name}</span>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[10px] font-semibold tracking-wider border",
                                ROLE_TYPE_COLORS[contact.role_type] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/20"
                              )}
                            >
                              {ROLE_TYPE_LABELS[contact.role_type] ?? contact.role_type}
                            </Badge>
                          </div>
                          {contact.recommended_approach && (
                            <p className="text-[11px] text-muted-foreground/60 mt-0.5 ml-0">{contact.recommended_approach}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Competitive Context */}
                {compContext && compContext.likely_competitors.length > 0 && (
                  <>
                    <Separator />
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Competitive Context</h3>
                      {compContext.iren_edge && (
                        <p className="text-xs text-[#22c55e] mb-3 italic">{compContext.iren_edge}</p>
                      )}
                      <div className="space-y-1.5">
                        {compContext.likely_competitors.slice(0, 5).map((lc) => (
                          <div key={lc.id} className="flex items-center justify-between rounded-md border border-border/30 px-3 py-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium">{lc.name}</span>
                              <Badge variant="outline" className="text-[8px]">{lc.segment}</Badge>
                            </div>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[9px]",
                                lc.threat_level === "high" && "text-red-400 border-red-400/30",
                                lc.threat_level === "medium" && "text-amber-400 border-amber-400/30",
                                lc.threat_level === "low" && "text-green-400 border-green-400/30",
                              )}
                            >
                              {lc.threat_level}
                            </Badge>
                          </div>
                        ))}
                      </div>
                      {compContext.recent_moves.length > 0 && (
                        <div className="mt-3">
                          <p className="text-[10px] font-semibold uppercase text-muted-foreground mb-1.5">Recent Competitor Moves</p>
                          {compContext.recent_moves.map((m, i) => (
                            <div key={i} className="flex items-center gap-2 py-1">
                              <Badge variant="outline" className="text-[8px] capitalize">{m.event_type}</Badge>
                              <span className="text-[11px] text-muted-foreground flex-1 truncate">{m.company_name}: {m.title}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}

                <Separator />

                {/* 6. Score Breakdown — compact grid */}
                {detail.score && (
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Score Breakdown</h3>
                    {detail.score_story && (
                      <p className="text-sm text-muted-foreground italic mb-3">{detail.score_story}</p>
                    )}
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(detail.score).filter(([k]) => k !== "total" && k !== "scored_at").map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between rounded-md border border-border/30 px-3 py-1.5">
                          <span className="text-xs text-muted-foreground capitalize">{key.replace("_", " ")}</span>
                          <span className="font-mono text-sm tabular-nums">{(val as number).toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex items-center justify-between rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5">
                      <span className="text-xs font-semibold text-primary">TOTAL</span>
                      <span className="font-mono text-lg font-bold tabular-nums">{detail.score.total.toFixed(1)}</span>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground pt-6">No prospect selected.</p>
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
