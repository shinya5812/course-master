"use client"

import { Area, AreaChart, ResponsiveContainer, YAxis, XAxis } from "recharts"
import { ChevronRight } from "lucide-react"
import { performance, returnTrend } from "@/lib/data"

export function PerformanceSection() {
  return (
    <section className="mx-auto max-w-[1180px] px-5 py-6">
      <div className="rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8">
        <div className="flex items-baseline gap-3">
          <h2 className="font-serif text-xl font-semibold">累計パフォーマンス</h2>
          <span className="text-xs text-muted-foreground">（公開予測ベース）</span>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr_0.7fr]">
          {/* Stats */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-7 sm:grid-cols-4">
            {performance.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-xs text-muted-foreground">
                  {stat.mark && <span className="text-gold">{stat.mark}</span>}
                  {stat.label}
                </p>
                <p className="mt-2 font-serif text-3xl font-bold text-gold-gradient">
                  {stat.value}
                  <span className="text-base">{stat.unit}</span>
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">{stat.sub}</p>
              </div>
            ))}
          </div>

          {/* Chart */}
          <div className="lg:border-l lg:border-gold-faint lg:pl-6">
            <p className="text-xs text-muted-foreground">回収率の推移</p>
            <div className="mt-2 h-28 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={returnTrend} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="goldFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="oklch(0.8 0.13 85)" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="oklch(0.8 0.13 85)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" hide />
                  <YAxis domain={[-60, 60]} hide />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="oklch(0.8 0.13 85)"
                    strokeWidth={2}
                    fill="url(#goldFill)"
                    dot={{ r: 2, fill: "oklch(0.8 0.13 85)" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
              <span>1月</span>
              <span>2月</span>
              <span>3月</span>
              <span>4月</span>
              <span>5月</span>
            </div>
          </div>

          {/* Recent 20R */}
          <div className="lg:border-l lg:border-gold-faint lg:pl-6">
            <p className="text-xs text-muted-foreground">直近20R</p>
            <div className="mt-3 space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-foreground/80">的中率</span>
                <span className="font-serif text-2xl font-bold text-gold-gradient">35.0%</span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-foreground/80">単勝回収率</span>
                <span className="font-serif text-2xl font-bold text-gold-gradient">162.3%</span>
              </div>
              <a
                href="#"
                className="flex items-center justify-between border-t border-gold-faint pt-3 text-xs text-foreground/80 transition-colors hover:text-gold"
              >
                詳細を表示
                <ChevronRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
