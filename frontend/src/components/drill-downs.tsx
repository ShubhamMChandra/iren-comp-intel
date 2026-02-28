import Link from "next/link"
import { cn } from "@/lib/utils"
import { SIGNAL_LABELS, SIGNAL_COLORS, TIER_COLORS } from "@/lib/utils"
import type { CallListEntry, HotProspect, ScoreBreakdown, Tier, SignalType } from "@/lib/types"
import { Badge } from "@/components/ui/badge"

const SCORE_CAPS: Record<string, number> = {
  fundraising: 20,
  funding_completed: 15,
  hiring: 25,
  ai_initiative: 15,
  cloud_spend: 15,
  outgrowing: 10,
}

const CATEGORY_LABELS: Record<string, string> = {
  fundraising: "Fundraising",
  funding_completed: "Funding Completed",
  hiring: "Hiring",
  ai_initiative: "AI Initiative",
  cloud_spend: "Cloud Spend",
  outgrowing: "Outgrowing",
}

// --- Pipeline Heat ---

export function PipelineHeatDetail({ prospects }: { prospects: HotProspect[] }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Prospects scoring in the <span className="text-foreground font-medium">top 30%</span> of your pipeline (HIGH or VERY HIGH tier).
      </p>
      {prospects.length > 0 ? (
        <div className="max-h-48 overflow-y-auto space-y-1">
          {prospects.map((p) => (
            <Link
              key={p.id}
              href={`/prospects?id=${p.id}`}
              className="flex items-center justify-between rounded px-2 py-1.5 text-xs hover:bg-accent/50 transition-colors"
            >
              <span className="font-medium">{p.name}</span>
              <div className="flex items-center gap-2">
                <span className="tabular-nums text-muted-foreground">{p.score.toFixed(1)}</span>
                <Badge
                  variant="outline"
                  className={cn("text-[9px] font-semibold tracking-wider border", TIER_COLORS[p.tier])}
                >
                  {p.tier}
                </Badge>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">No hot prospects currently.</p>
      )}
    </div>
  )
}

// --- Signal Breakdown ---

export function SignalBreakdownDetail({ breakdown }: { breakdown: Record<string, number> }) {
  const sorted = Object.entries(breakdown).sort((a, b) => b[1] - a[1])
  const max = sorted.length > 0 ? sorted[0][1] : 1

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Actionable signals this week by type. Excludes noise/irrelevant. <span className="text-foreground font-medium">WoW</span> = compared to same period last week.
      </p>
      <div className="space-y-1.5">
        {sorted.map(([type, count]) => (
          <div key={type} className="space-y-0.5">
            <div className="flex items-center justify-between text-xs">
              <span className={cn("font-medium", SIGNAL_COLORS[type]?.split(" ")[0])}>
                {SIGNAL_LABELS[type] || type}
              </span>
              <span className="tabular-nums text-muted-foreground">{count}</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full", SIGNAL_COLORS[type]?.split(" ")[1] || "bg-zinc-500")}
                style={{ width: `${(count / max) * 100}%`, opacity: 0.8 }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="border-t border-border/50 pt-2">
        <Link
          href="/prospects"
          className="text-xs font-medium text-primary hover:underline"
        >
          View all prospects →
        </Link>
      </div>
    </div>
  )
}

// --- Score Breakdown ---

export function ScoreBreakdownDetail({ breakdown, total }: { breakdown: ScoreBreakdown; total: number }) {
  const entries = Object.entries(breakdown).filter(([k]) => k in SCORE_CAPS)

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Score = sum of 6 signal categories, each with a cap. Recent signals from credible sources score higher.
      </p>
      <div className="space-y-1.5">
        {entries.map(([cat, val]) => {
          const cap = SCORE_CAPS[cat] || 25
          const pct = Math.min(100, (val / cap) * 100)
          return (
            <div key={cat} className="space-y-0.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{CATEGORY_LABELS[cat] || cat}</span>
                <span className="tabular-nums font-mono">
                  {val.toFixed(1)}<span className="text-muted-foreground/60">/{cap}</span>
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
              </div>
            </div>
          )
        })}
      </div>
      <div className="flex items-center justify-between border-t border-border/50 pt-2 text-xs">
        <span className="font-semibold text-primary">TOTAL</span>
        <span className="font-mono font-bold tabular-nums">{total.toFixed(1)}<span className="text-muted-foreground/60">/100</span></span>
      </div>
    </div>
  )
}

// --- Tier Explainer ---

const TIER_DEFS: { tier: Tier; label: string; rule: string }[] = [
  { tier: "VERY HIGH", label: "Very High", rule: "90th percentile and above" },
  { tier: "HIGH", label: "High", rule: "70th–89th percentile" },
  { tier: "MEDIUM", label: "Medium", rule: "40th–69th percentile" },
  { tier: "LOW", label: "Low", rule: "10th–39th percentile" },
  { tier: "DORMANT", label: "Dormant", rule: "Below 10th percentile or zero" },
]

export function TierExplainer({ activeTier }: { activeTier: Tier }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Tiers rank prospects relative to each other based on their total score.
      </p>
      <div className="space-y-1">
        {TIER_DEFS.map((t) => (
          <div
            key={t.tier}
            className={cn(
              "flex items-center justify-between rounded px-2 py-1 text-xs",
              t.tier === activeTier && "bg-accent/50",
            )}
          >
            <Badge
              variant="outline"
              className={cn(
                "text-[9px] font-semibold tracking-wider border",
                TIER_COLORS[t.tier],
                t.tier === activeTier && "ring-1 ring-primary/30",
              )}
            >
              {t.tier}
            </Badge>
            <span className="text-muted-foreground">{t.rule}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// --- Delta Explainer ---

export function DeltaExplainer({ score, delta }: { score: number; delta: number }) {
  const previous = score - delta

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Change between the two most recent scoring runs.
      </p>
      <div className="flex items-center gap-3 text-sm">
        <div className="text-center">
          <p className="text-[10px] text-muted-foreground">Previous</p>
          <p className="font-mono tabular-nums">{previous.toFixed(1)}</p>
        </div>
        <span className="text-muted-foreground">→</span>
        <div className="text-center">
          <p className="text-[10px] text-muted-foreground">Current</p>
          <p className="font-mono tabular-nums font-medium">{score.toFixed(1)}</p>
        </div>
        <span className="text-muted-foreground">=</span>
        <div className="text-center">
          <p className="text-[10px] text-muted-foreground">Delta</p>
          <p className={cn("font-mono tabular-nums font-semibold", delta > 0 ? "text-emerald-400" : "text-red-400")}>
            {delta > 0 ? "+" : ""}{delta.toFixed(1)}
          </p>
        </div>
      </div>
    </div>
  )
}

// --- Hottest Mover Detail ---

export function HottestMoverDetail({ id, name, score, delta, signalType }: {
  id: number
  name: string
  score: number
  delta: number
  signalType: SignalType | null
}) {
  const previous = score - delta

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Prospect with the largest absolute score change this week.
      </p>
      <div className="rounded border border-border/30 p-2.5">
        <p className="font-medium text-sm">{name}</p>
        <div className="mt-1 flex items-center gap-3 text-xs">
          <span className="tabular-nums text-muted-foreground">{previous.toFixed(1)} → {score.toFixed(1)}</span>
          <span className={cn("font-mono font-semibold tabular-nums", delta > 0 ? "text-emerald-400" : "text-red-400")}>
            {delta > 0 ? "+" : ""}{delta.toFixed(1)}
          </span>
        </div>
        {signalType && (
          <div className="mt-1.5">
            <Badge variant="outline" className={cn("text-[9px] tracking-wider border", SIGNAL_COLORS[signalType])}>
              {SIGNAL_LABELS[signalType] || signalType}
            </Badge>
          </div>
        )}
      </div>
      <div className="border-t border-border/50 pt-2">
        <Link
          href={`/prospects?id=${id}`}
          className="text-xs font-medium text-primary hover:underline"
        >
          View profile →
        </Link>
      </div>
    </div>
  )
}

// --- Heating Up Explainer ---

export function HeatingUpDetail({ prospects }: { prospects: CallListEntry[] }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        <span className="text-foreground font-medium">{prospects.length}</span> prospects gained score since the last scoring run — new signals were detected that increased their score.
      </p>
      {prospects.length > 0 ? (
        <div className="max-h-48 overflow-y-auto space-y-1">
          {prospects.map((p) => (
            <Link
              key={p.id}
              href={`/prospects?id=${p.id}`}
              className="flex items-center justify-between rounded px-2 py-1.5 text-xs hover:bg-accent/50 transition-colors"
            >
              <div>
                <span className="font-medium">{p.name}</span>
                <span className="ml-2 text-muted-foreground">{p.industry}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="tabular-nums text-muted-foreground">{p.score.toFixed(1)}</span>
                <Badge
                  variant="outline"
                  className={cn("text-[9px] font-semibold tracking-wider border", TIER_COLORS[p.tier])}
                >
                  {p.tier}
                </Badge>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">No prospects heating up this cycle.</p>
      )}
    </div>
  )
}
