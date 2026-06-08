"use client"

import { Area, AreaChart, ResponsiveContainer, YAxis, XAxis } from "recharts"
import { ChevronRight } from "lucide-react"
import { returnTrend } from "@/lib/data"
import type { StatsData } from "@/app/page"

type Props = {
  stats: StatsData | null
}

function weeksSince(dateStr: string): number {
  if (!dateStr) return 0
  const start = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - start.getTime()
  return Math.max(1, Math.floor(diff / (7 * 24 * 60 * 60 * 1000)))
}

function formatPct(rate: number): string {
  return (rate * 100).toFixed(1)
}

export function PerformanceSection({ stats }: Props) {
  const isAccumulating = !stats || stats.total_races < 10
  const weeks = stats ? weeksSince(stats.public_start_date) : 0

  const statCards = stats
    ? [
        {
          label: "的中率",
          mark: "◎",
          value: formatPct(stats.honmei_win_rate),
          unit: "%",
          sub: `${stats.honmei_wins}/${stats.total_races}R`,
        },
        {
          label: "複勝率",
          mark: "",
          value: formatPct(stats.honmei_place_rate),
          unit: "%",
          sub: "3着以内",
        },
        {
          label: "検証R数",
          mark: "",
          value: String(stats.total_races),
          unit: "R",
          sub: "実績記録済み",
        },
        {
          label: "公開開始",
          mark: "",
          value: stats.public_start_date.slice(5).replace("-", "/"),
          unit: "",
          sub: `${weeks}週経過`,
        },
      ]
    : []

  return (
    <section className="mx-auto max-w-[1180px] px-5 py-6">
      <div className="rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8">
        {/* ヘッダー */}
        <div className="flex flex-wrap items-baseline gap-3">
          <h2 className="font-serif text-xl font-semibold">累計パフォーマンス</h2>
          <span className="text-xs text-muted-foreground">（公開予測ベース）</span>
          {isAccumulating && (
            <span className="rounded bg-warn/15 px-2 py-0.5 text-[10px] font-medium text-warn border border-warn/30">
              ※公開後{weeks}週間・サンプル蓄積中
            </span>
          )}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr_0.7fr]">
          {/* 統計グリッド */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-7 sm:grid-cols-4">
            {statCards.length > 0 ? (
              statCards.map((stat) => (
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
              ))
            ) : (
              <div className="col-span-4 py-4 text-center text-sm text-muted-foreground">
                データを読み込み中...
              </div>
            )}
          </div>

          {/* チャート（プレースホルダー） */}
          <div className="lg:border-l lg:border-gold-faint lg:pl-6">
            <p className="text-xs text-muted-foreground">
              回収率の推移
              {isAccumulating && (
                <span className="ml-1 text-[10px] text-muted-foreground/60">（イメージ）</span>
              )}
            </p>
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

          {/* 右カラム */}
          <div className="lg:border-l lg:border-gold-faint lg:pl-6">
            {isAccumulating ? (
              <div className="flex flex-col gap-3">
                <p className="text-xs text-muted-foreground">データ蓄積中</p>
                <p className="text-sm text-foreground/80 leading-relaxed">
                  現在{" "}
                  <span className="font-bold text-gold">{stats?.total_races ?? 0}R</span>{" "}
                  検証済み。
                  <br />
                  30R 以上で統計的評価が可能になります。
                </p>
                {stats && (
                  <p className="text-[11px] text-muted-foreground">{stats.note}</p>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">直近成績</p>
                <div className="flex items-baseline justify-between">
                  <span className="text-sm text-foreground/80">的中率</span>
                  <span className="font-serif text-2xl font-bold text-gold-gradient">
                    {stats ? `${formatPct(stats.honmei_win_rate)}%` : "-"}
                  </span>
                </div>
                {stats?.tansho_roi != null && (
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm text-foreground/80">単勝回収率</span>
                    <span className="font-serif text-2xl font-bold text-gold-gradient">
                      {stats.tansho_roi.toFixed(1)}%
                    </span>
                  </div>
                )}
                <a
                  href="#"
                  className="flex items-center justify-between border-t border-gold-faint pt-3 text-xs text-foreground/80 transition-colors hover:text-gold"
                >
                  詳細を表示
                  <ChevronRight className="h-3.5 w-3.5" />
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
