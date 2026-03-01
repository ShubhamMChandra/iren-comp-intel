import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatFunding(amount: number | null): string {
  if (!amount) return "—"
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(0)}M`
  return `$${amount.toLocaleString()}`
}

export function formatDelta(delta: number): string {
  if (delta > 0.5) return `+${delta.toFixed(1)}`
  if (delta < -0.5) return delta.toFixed(1)
  return "—"
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

export const SIGNAL_LABELS: Record<string, string> = {
  fundraising: "FUNDRAISING",
  funding_completed: "FUNDED",
  hiring: "HIRING",
  ai_initiative: "AI INITIATIVE",
  cloud_spend: "CLOUD SPEND",
  outgrowing: "OUTGROWING",
}

export const SIGNAL_COLORS: Record<string, string> = {
  fundraising: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  funding_completed: "text-teal-400 bg-teal-400/10 border-teal-400/20",
  hiring: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  ai_initiative: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  cloud_spend: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  outgrowing: "text-red-400 bg-red-400/10 border-red-400/20",
}

export const TIER_COLORS: Record<string, string> = {
  "VERY HIGH": "text-emerald-400 bg-emerald-400/10 border-emerald-400/20",
  "HIGH": "text-green-300 bg-green-300/10 border-green-300/20",
  "MEDIUM": "text-amber-400 bg-amber-400/10 border-amber-400/20",
  "LOW": "text-zinc-400 bg-zinc-400/10 border-zinc-400/20",
  "DORMANT": "text-zinc-600 bg-zinc-600/10 border-zinc-600/20",
}

export const PRODUCT_FIT_LABELS: Record<string, string> = {
  ai_cloud: "AI Cloud",
  colocation: "Colo",
  build_to_suit: "Build-to-Suit",
}

export const PRODUCT_FIT_COLORS: Record<string, string> = {
  ai_cloud: "text-violet-400 bg-violet-400/10 border-violet-400/20",
  colocation: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  build_to_suit: "text-orange-400 bg-orange-400/10 border-orange-400/20",
}

export const ROLE_TYPE_COLORS: Record<string, string> = {
  technical: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  economic: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  champion: "text-green-400 bg-green-400/10 border-green-400/20",
  procurement: "text-zinc-400 bg-zinc-400/10 border-zinc-400/20",
}

export const ROLE_TYPE_LABELS: Record<string, string> = {
  technical: "Technical",
  economic: "Economic",
  champion: "Champion",
  procurement: "Procurement",
}

export const URGENCY_COLORS: Record<string, string> = {
  URGENT: "text-red-400",
  HIGH: "text-orange-400",
  MEDIUM: "text-amber-400",
  LOW: "text-zinc-400",
}

export const URGENCY_BADGE_COLORS: Record<string, string> = {
  URGENT: "text-red-400 bg-red-400/10 border-red-400/30",
  HIGH: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  MEDIUM: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  LOW: "text-zinc-500 bg-zinc-500/10 border-zinc-500/20",
}

export const SOURCE_CONFIDENCE: Record<string, { label: string; level: "high" | "medium" | "low" }> = {
  sec_filing: { label: "SEC Filing", level: "high" },
  major_news: { label: "Verified", level: "high" },
  industry_news: { label: "Industry", level: "medium" },
  blog: { label: "Blog", level: "low" },
  social_media: { label: "Social", level: "low" },
  rumor: { label: "Rumor", level: "low" },
}

export const SOURCE_LEVEL_COLORS: Record<string, string> = {
  high: "text-emerald-400/80",
  medium: "text-zinc-400/60",
  low: "text-amber-400/60",
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

/**
 * Compute a human-readable deadline range from a detected date and window string.
 * e.g. computeDeadline("2026-01-15", "30-120 days") → "Feb–May 2026"
 *      computeDeadline("2026-01-15", "3-6 months")  → "Apr–Jul 2026"
 */
export function computeDeadline(detectedAt: string, windowStr: string | null): string | null {
  if (!detectedAt || !windowStr) return null

  const base = new Date(detectedAt)
  if (isNaN(base.getTime())) return null

  const match = windowStr.match(/(\d+)\s*[-–]\s*(\d+)\s*(day|month|week)/i)
  if (!match) return null

  const lo = parseInt(match[1], 10)
  const hi = parseInt(match[2], 10)
  const unit = match[3].toLowerCase()

  const addToDate = (d: Date, amount: number): Date => {
    const result = new Date(d)
    if (unit.startsWith("day")) {
      result.setDate(result.getDate() + amount)
    } else if (unit.startsWith("week")) {
      result.setDate(result.getDate() + amount * 7)
    } else {
      result.setMonth(result.getMonth() + amount)
    }
    return result
  }

  const start = addToDate(base, lo)
  const end = addToDate(base, hi)

  const startLabel = MONTH_NAMES[start.getMonth()]
  const endLabel = MONTH_NAMES[end.getMonth()]
  const startYear = start.getFullYear()
  const endYear = end.getFullYear()

  if (startYear === endYear) {
    if (startLabel === endLabel) return `${startLabel} ${startYear}`
    return `${startLabel}–${endLabel} ${endYear}`
  }
  return `${startLabel} ${startYear}–${endLabel} ${endYear}`
}
