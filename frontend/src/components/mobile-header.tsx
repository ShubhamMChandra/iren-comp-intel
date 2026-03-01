"use client"

import { SidebarTrigger } from "@/components/ui/sidebar"

export function MobileHeader() {
  return (
    <div className="sticky top-0 z-30 flex h-12 items-center border-b border-border/50 bg-[#09090b]/80 backdrop-blur px-4 md:hidden">
      <SidebarTrigger />
      <span className="ml-2 text-sm font-bold tracking-tight">IREN</span>
    </div>
  )
}
