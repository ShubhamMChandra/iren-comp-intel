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
