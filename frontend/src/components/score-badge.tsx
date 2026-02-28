import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { Tier } from "@/lib/types"

const TIER_STYLES: Record<Tier, string> = {
  "VERY HIGH": "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  "HIGH": "border-green-400/30 bg-green-400/10 text-green-300",
  "MEDIUM": "border-amber-500/30 bg-amber-500/10 text-amber-400",
  "LOW": "border-zinc-500/30 bg-zinc-500/10 text-zinc-400",
  "DORMANT": "border-zinc-700/30 bg-zinc-700/10 text-zinc-600",
}

export function ScoreBadge({ tier, className }: { tier: Tier; className?: string }) {
  return (
    <Badge variant="outline" className={cn("text-[10px] font-semibold tracking-wider", TIER_STYLES[tier], className)}>
      {tier}
    </Badge>
  )
}
