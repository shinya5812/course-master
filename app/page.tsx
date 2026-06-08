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

export type LatestData = {
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
}

function loadLatestData(): LatestData | null {
  try {
    const filePath = path.join(process.cwd(), "output", "latest_data.json")
    const raw = fs.readFileSync(filePath, "utf-8")
    return JSON.parse(raw) as LatestData
  } catch {
    return null
  }
}

export default function Page() {
  const latestData = loadLatestData()
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <main>
        <Hero latestData={latestData} />
        <PerformanceSection />
        <WeeklyRaces />
        <section className="mx-auto grid max-w-[1180px] grid-cols-1 gap-6 px-5 py-8 lg:grid-cols-[1.5fr_1fr]">
          <RankingTable />
          <RadarSection />
        </section>
        <FeaturesNews />
      </main>
      <SiteFooter />
    </div>
  )
}
