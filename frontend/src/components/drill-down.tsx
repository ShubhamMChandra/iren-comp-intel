"use client"

import type { ReactNode } from "react"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"

interface DrillDownProps {
  children: ReactNode
  content: ReactNode
  title?: string
  className?: string
  align?: "start" | "center" | "end"
}

export function DrillDown({ children, content, title, className, align = "center" }: DrillDownProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "cursor-pointer decoration-dashed underline-offset-4 hover:underline decoration-muted-foreground/40 transition-colors inline-flex items-baseline",
            className,
          )}
        >
          {children}
        </button>
      </PopoverTrigger>
      <PopoverContent align={align} className="w-80 p-0">
        {title && (
          <div className="border-b border-border/50 px-4 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</p>
          </div>
        )}
        <div className="px-4 py-3 text-sm">{content}</div>
      </PopoverContent>
    </Popover>
  )
}
