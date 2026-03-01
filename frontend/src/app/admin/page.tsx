"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { getAdminStats, seedDatabase, rescoreAll } from "@/lib/api"
import type { AdminStats } from "@/lib/types"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
import { Database, RefreshCw, Loader2, CheckCircle2, AlertCircle, Settings } from "lucide-react"

const SIGNAL_LABELS: Record<string, string> = {
  fundraising: "Fundraising",
  funding_completed: "Funded",
  hiring: "Hiring",
  ai_initiative: "AI Initiative",
  cloud_spend: "Cloud Spend",
  outgrowing: "Outgrowing",
}

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [seedStatus, setSeedStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [rescoreStatus, setRescoreStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [rescoreCount, setRescoreCount] = useState(0)

  const loadStats = () => {
    setLoading(true)
    getAdminStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    const t = setTimeout(loadStats, 0)
    return () => clearTimeout(t)
  }, [])

  const handleSeed = async () => {
    setSeedStatus("loading")
    try {
      await seedDatabase()
      setSeedStatus("success")
      loadStats()
    } catch {
      setSeedStatus("error")
    }
  }

  const handleRescore = async () => {
    setRescoreStatus("loading")
    try {
      const res = await rescoreAll()
      setRescoreCount(res.count)
      setRescoreStatus("success")
      loadStats()
    } catch {
      setRescoreStatus("error")
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-32" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  const chartData = stats
    ? Object.entries(stats.signal_distribution).map(([type, count]) => ({
        name: SIGNAL_LABELS[type] || type,
        count,
        type,
      }))
    : []

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Settings className="h-5 w-5 text-muted-foreground" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
          <p className="text-sm text-muted-foreground">System management & configuration</p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Card className="bg-card/50">
            <CardContent className="p-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Companies</p>
              <p className="text-2xl font-semibold tabular-nums mt-1">{stats.companies}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50">
            <CardContent className="p-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Active Signals</p>
              <p className="text-2xl font-semibold tabular-nums mt-1">{stats.signals}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50">
            <CardContent className="p-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Score Records</p>
              <p className="text-2xl font-semibold tabular-nums mt-1">{stats.scores}</p>
            </CardContent>
          </Card>
          <Card className="bg-card/50">
            <CardContent className="p-4">
              <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">AI Briefs</p>
              <p className="text-2xl font-semibold tabular-nums mt-1">{stats.briefs}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Signal Distribution Chart */}
        <Card className="bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Signal Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((_entry, index) => (
                    <Cell key={index} fill="#22c55e" fillOpacity={0.8 - index * 0.08} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Scoring Weights */}
        <Card className="bg-card/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Scoring Weights</CardTitle>
          </CardHeader>
          <CardContent className="p-0 overflow-x-auto">
            {stats && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50">
                    <th className="px-4 py-2 text-left text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Signal Type</th>
                    <th className="px-4 py-2 text-right text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Max Pts</th>
                    <th className="px-4 py-2 text-right text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Base Pts</th>
                    <th className="px-4 py-2 text-right text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Halflife</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(stats.weights).map(([type, w]) => (
                    <tr key={type} className="border-b border-border/30">
                      <td className="px-4 py-2 capitalize">{type.replace("_", " ")}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">{w.max_points}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">{w.base_points}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">{w.halflife}d</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Actions */}
      <div>
        <h2 className="text-sm font-semibold mb-4">Actions</h2>
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleSeed} disabled={seedStatus === "loading"} className="gap-1.5">
              {seedStatus === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
              Seed Database
            </Button>
            {seedStatus === "success" && <span className="inline-flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 className="h-3 w-3" /> Done</span>}
            {seedStatus === "error" && <span className="inline-flex items-center gap-1 text-xs text-red-400"><AlertCircle className="h-3 w-3" /> Failed</span>}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleRescore} disabled={rescoreStatus === "loading"} className="gap-1.5">
              {rescoreStatus === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Rescore All
            </Button>
            {rescoreStatus === "success" && <span className="inline-flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 className="h-3 w-3" /> {rescoreCount} scored</span>}
            {rescoreStatus === "error" && <span className="inline-flex items-center gap-1 text-xs text-red-400"><AlertCircle className="h-3 w-3" /> Failed</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
