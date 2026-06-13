import fs from "fs"
import path from "path"
import { SiteHeader } from "@/components/site-header"
import { Hero } from "@/components/hero"
import { PerformanceSection } from "@/components/performance-section"
import { WeeklyRaces } from "@/components/weekly-races"
import { RankingTable } from "@/components/ranking-table"
import { RadarSection } from "@/components/radar-section"
import { FeaturesNews } from "@/components/features-news"
import { SiteFooter } from "@/components/site-footer"

export const dynamic = 'force-dynamic'

// ── 型定義 ──────────────────────────────────────────────

export type HonmeiHorse = {
  horse_no: number
  horse_name: string
  popularity: number
  odds: number
  edge: number
}

export type ActualResult = {
  honmei_finish: number
  verdict_result?: string
  edge_accuracy_note?: string
  result?: Array<{
    finish: number
    horse_no: number
    horse_name: string
    popularity: number
    tansho_odds: number
    engine_mark: string
    engine_edge: number
    note?: string
  }>
  pnl?: { invested: number; returned: number; net: number }
}

export type RaceEntry = {
  race_name: string
  race_date: string
  venue: string
  surface: string
  distance: number
  grade: string
  heads: number
  track_cond: string
  adi: number
  adi_label: string
  anaba_flag: boolean
  verdict: string
  verdict_detail: string
  prediction: {
    honmei: HonmeiHorse
    renpuku: HonmeiHorse[]
    santen: HonmeiHorse[]
  }
  actual_result?: ActualResult
}

export type StatsData = {
  total_races: number
  honmei_wins: number
  honmei_win_rate: number
  honmei_place_rate: number
  tansho_roi: number | null
  public_start_date: string
  last_updated: string
  note: string
}

export type EdgeRankEntry = {
  rank: number
  horse_no: number
  horse_name: string
  race_name: string
  race_date: string
  mark: string
  popularity: number
  odds: number
  edge: number
  est_win_prob: string
  mkt_win_prob: string
}

export type LatestData = {
  // 後方互換フィールド（Hero コンポーネント用）
  race_name: string
  race_date: string
  venue: string
  surface: string
  distance: number
  horse_name: string
  popularity: number
  odds: number
  edge: number
  verdict: string
  adi: number
  adi_label: string
  // 拡張セクション
  races?: RaceEntry[]
  stats?: StatsData
  edge_ranking?: EdgeRankEntry[]
}

// ── データ読み込み ────────────────────────────────────────

function loadLatestData(): LatestData | null {
  try {
    const filePath = path.join(process.cwd(), "output", "latest_data.json")
    const raw = fs.readFileSync(filePath, "utf-8")
    return JSON.parse(raw) as LatestData
  } catch {
    return null
  }
}

// ── ページ ───────────────────────────────────────────────

export default function Page() {
  const data = loadLatestData()
  const sortedRaces = [...(data?.races ?? [])].sort(
    (a, b) => new Date(b.race_date).getTime() - new Date(a.race_date).getTime(),
  )
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main>
        <Hero latestData={data} />
        <PerformanceSection stats={data?.stats ?? null} />
        <WeeklyRaces races={sortedRaces} />
        <section className="mx-auto grid max-w-[1180px] grid-cols-1 gap-6 px-5 py-8 lg:grid-cols-[1.5fr_1fr]">
          <RankingTable ranking={data?.edge_ranking ?? []} />
          <RadarSection />
        </section>
        <FeaturesNews />
      </main>
      <SiteFooter />
    </div>
  )
}
