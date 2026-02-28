import { SOURCE_CONFIDENCE, SOURCE_LEVEL_COLORS } from "@/lib/utils"

export function SourceBadge({ sourceType }: { sourceType: string }) {
  const info = SOURCE_CONFIDENCE[sourceType]
  if (!info || info.level === "medium") return null
  const color = SOURCE_LEVEL_COLORS[info.level]
  return (
    <span className={`text-[9px] font-medium uppercase tracking-wider ${color}`}>
      {info.label}
    </span>
  )
}
