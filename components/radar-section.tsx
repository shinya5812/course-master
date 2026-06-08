"use client"

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts"
import { ChevronRight } from "lucide-react"
import { radarData } from "@/lib/data"

export function RadarSection() {
  return (
    <div className="rounded-xl border border-gold-faint bg-card/60 p-6">
      <h2 className="font-serif text-xl font-semibold">
        荒れ指数（ADI）・偏り指数（FRI）
      </h2>

      <div className="mt-2 h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData} outerRadius="70%">
            <PolarGrid stroke="oklch(0.4 0.02 90 / 30%)" />
            <PolarAngleAxis
              dataKey="axis"
              tick={{ fill: "oklch(0.66 0.012 90)", fontSize: 11 }}
            />
            <PolarRadiusAxis
              type="number"
              domain={[0, 100]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name="ADI"
              dataKey="adi"
              stroke="oklch(0.62 0.19 25)"
              fill="oklch(0.62 0.19 25)"
              fillOpacity={0.25}
              strokeWidth={2}
            />
            <Radar
              name="FRI"
              dataKey="fri"
              stroke="oklch(0.6 0.13 250)"
              fill="oklch(0.6 0.13 250)"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex items-center justify-center gap-6 text-xs">
        <span className="flex items-center gap-2">
          <span className="h-0.5 w-4 rounded bg-danger" />
          ADI（荒れ指数）
          <span className="font-serif text-lg font-bold text-danger">72</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="h-0.5 w-4 rounded bg-chart-3" />
          FRI（偏り指数）
          <span className="font-serif text-lg font-bold text-chart-3">31</span>
        </span>
      </div>

      <a
        href="#"
        className="mx-auto mt-5 flex w-fit items-center gap-2 rounded-md border border-gold-faint px-6 py-2.5 text-xs text-foreground/90 transition-colors hover:border-gold hover:text-gold"
      >
        指数について詳しく見る
        <ChevronRight className="h-3.5 w-3.5" />
      </a>
    </div>
  )
}
