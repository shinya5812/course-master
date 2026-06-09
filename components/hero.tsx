import Image from "next/image"
import { ChevronRight } from "lucide-react"
import type { LatestData } from "@/app/page"

type Props = {
  latestData: LatestData | null
}

function gradeFromRaceName(name: string): string {
  if (name.includes("G1")) return "G1"
  if (name.includes("G2")) return "G2"
  if (name.includes("G3")) return "G3"
  const m = name.match(/(G[123])/i)
  return m ? m[1].toUpperCase() : "重賞"
}

function formatEdge(edge: number): string {
  const pct = (edge * 100).toFixed(1)
  return edge >= 0 ? `+${pct}%` : `${pct}%`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export function Hero({ latestData }: Props) {
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto grid max-w-[1180px] grid-cols-1 gap-10 px-5 pb-14 pt-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-6">
        {/* Left: copy */}
        <div className="relative z-10 flex flex-col justify-center">
          <h1 className="font-serif text-5xl font-bold leading-tight tracking-tight text-balance text-gold-gradient sm:text-6xl">
            市場の歪みを読み、
            <br />
            期待値で勝つ。
          </h1>
          <p className="mt-6 max-w-md text-pretty leading-relaxed text-foreground/85">
            12軸スコア × 4チーム合議制で導き出す、
            <br className="hidden sm:block" />
            JRAレースのエッジと荒れ指数。
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <a
              href="/weekly"
              className="bg-gold-gradient inline-flex items-center gap-3 rounded-md px-7 py-3.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-gold/20 transition-transform hover:-translate-y-0.5"
            >
              今週の予測を見る
              <ChevronRight className="h-4 w-4" />
            </a>
            <a
              href="/results"
              className="inline-flex items-center gap-2 rounded-md border border-gold-faint px-7 py-3.5 text-sm font-medium text-foreground/90 transition-colors hover:border-gold hover:text-gold"
            >
              的中実績を見る
            </a>
          </div>
        </div>

        {/* Right: hero image + latest result card */}
        <div className="relative">
          <div className="relative h-72 overflow-hidden rounded-xl border border-gold-faint sm:h-96 lg:h-full">
            <Image
              src="/images/hero-horse.png"
              alt="疾走する競走馬と騎手"
              fill
              className="object-cover"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-r from-background via-background/40 to-transparent" />
          </div>

          <div className="mt-6 rounded-xl border border-gold-faint bg-card/90 p-5 shadow-xl lg:absolute lg:right-0 lg:top-0 lg:mt-0 lg:w-72">
            <p className="text-xs font-medium tracking-wide text-gold">最新レース予測</p>
            {latestData ? (
              <>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="font-serif text-base font-semibold">{latestData.race_name}</span>
                  <span className="rounded bg-gold/15 px-1.5 py-0.5 text-[10px] font-bold text-gold">
                    {gradeFromRaceName(latestData.race_name)}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {formatDate(latestData.race_date)} {latestData.venue} {latestData.surface}{latestData.distance}m
                </p>
                <p className="mt-3 text-sm">
                  <span className="text-gold">◎</span> {latestData.horse_name}
                  <span className="ml-2 text-muted-foreground text-xs">{latestData.popularity}番人気</span>
                </p>
                <p className="font-serif text-2xl font-bold text-gold-gradient mt-1">{latestData.verdict}</p>
                <div className="mt-3 flex items-center justify-between border-t border-gold-faint pt-3 text-xs">
                  <span className="text-muted-foreground">
                    単勝 <span className="text-foreground">{latestData.odds}倍</span>
                  </span>
                  <span className="text-muted-foreground">
                    エッジ{" "}
                    <span className={latestData.edge >= 0 ? "text-positive" : "text-danger"}>
                      {formatEdge(latestData.edge)}
                    </span>
                  </span>
                </div>
              </>
            ) : (
              <>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="font-serif text-base font-semibold text-muted-foreground">データ準備中</span>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">次回予測データを更新後に表示されます</p>
              </>
            )}
            <a
              href="/results"
              className="mt-4 flex items-center justify-center gap-2 rounded-md border border-gold-faint py-2.5 text-xs text-foreground/90 transition-colors hover:border-gold hover:text-gold"
            >
              レース結果一覧へ
              <ChevronRight className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
