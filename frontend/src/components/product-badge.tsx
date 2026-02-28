import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { PRODUCT_FIT_LABELS, PRODUCT_FIT_COLORS } from "@/lib/utils"

interface ProductBadgeProps {
  productFit: string | null
  className?: string
}

export function ProductBadge({ productFit, className }: ProductBadgeProps) {
  if (!productFit) return null

  return (
    <Badge
      variant="outline"
      className={cn(
        "text-[10px] font-semibold tracking-wider border",
        PRODUCT_FIT_COLORS[productFit] ?? "text-zinc-400 bg-zinc-400/10 border-zinc-400/20",
        className
      )}
    >
      {PRODUCT_FIT_LABELS[productFit] ?? productFit}
    </Badge>
  )
}
