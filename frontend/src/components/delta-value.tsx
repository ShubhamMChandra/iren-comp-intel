import { cn } from "@/lib/utils"

export function DeltaValue({ delta, className }: { delta: number; className?: string }) {
  if (Math.abs(delta) < 0.5) {
    return <span className={cn("text-zinc-600 tabular-nums", className)}>—</span>
  }
  return (
    <span className={cn(
      "tabular-nums font-medium",
      delta > 0 ? "text-emerald-400" : "text-red-400",
      className
    )}>
      {delta > 0 ? "+" : ""}{delta.toFixed(1)}
    </span>
  )
}
