"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { SignalBadge } from "@/components/signal-badge"
import { getCompetitors, generateBattlecard } from "@/lib/api"
import { formatDate } from "@/lib/utils"
import type { Competitor } from "@/lib/types"
import { Building2, MapPin, Users, Swords, Sparkles, Loader2, Globe } from "lucide-react"

export default function CompetePage() {
  const [competitors, setCompetitors] = useState<Competitor[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [battlecard, setBattlecard] = useState<string | null>(null)
  const [bcLoading, setBcLoading] = useState(false)

  useEffect(() => {
    getCompetitors()
      .then(setCompetitors)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const selected = competitors.find((c) => c.id === selectedId) || null

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
        <Skeleton className="h-8 w-32" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-64" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Compete</h1>
        <p className="text-sm text-muted-foreground">
          {competitors.length} competitors tracked — market landscape for Iren
        </p>
      </div>

      {/* Competitor Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {competitors.map((c) => (
          <Card
            key={c.id}
            className="bg-card/50 cursor-pointer transition-all hover:border-primary/30 hover:bg-card/70"
            onClick={() => { setSelectedId(c.id); setBattlecard(null) }}
          >
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base">{c.name}</CardTitle>
                  <p className="text-xs text-muted-foreground mt-0.5">{c.industry}</p>
                </div>
                {c.is_public && c.ticker && (
                  <Badge variant="outline" className="text-[10px] font-mono">{c.ticker}</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {c.description && (
                <p className="text-xs text-muted-foreground line-clamp-2">{c.description}</p>
              )}

              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                {c.hq_location && (
                  <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{c.hq_location}</span>
                )}
                {c.employee_count && (
                  <span className="inline-flex items-center gap-1"><Users className="h-3 w-3" />{c.employee_count.toLocaleString()}</span>
                )}
                {c.capacity_mw && (
                  <span className="inline-flex items-center gap-1"><Building2 className="h-3 w-3" />{c.capacity_mw} MW</span>
                )}
              </div>

              {c.events.length > 0 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Recent Events</p>
                  {c.events.slice(0, 2).map((e) => (
                    <div key={e.id} className="flex items-center gap-2 text-xs">
                      <Badge variant="outline" className="text-[9px] shrink-0">{e.event_type}</Badge>
                      <span className="truncate text-muted-foreground">{e.title}</span>
                    </div>
                  ))}
                </div>
              )}

              {c.signals.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {c.signals.slice(0, 3).map((s) => (
                    <SignalBadge key={s.id} type={s.signal_type} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {competitors.length === 0 && (
          <div className="col-span-full py-12 text-center text-muted-foreground">
            No competitors tracked yet.
          </div>
        )}
      </div>

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
                  <span>{selected.industry}</span>
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
                      <p className="text-sm font-medium tabular-nums">{selected.capacity_mw} MW</p>
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
