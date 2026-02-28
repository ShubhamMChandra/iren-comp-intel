import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { SIGNAL_LABELS, SIGNAL_COLORS } from "@/lib/utils"

export function SignalBadge({ type, className }: { type: string; className?: string }) {
  const label = SIGNAL_LABELS[type] || type.toUpperCase()
  const colors = SIGNAL_COLORS[type] || "text-zinc-400 bg-zinc-400/10 border-zinc-400/20"

  return (
    <Badge variant="outline" className={cn("text-[10px] font-semibold tracking-wider border", colors, className)}>
      {label}
    </Badge>
  )
}
