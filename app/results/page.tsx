import fs from "fs"
import path from "path"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { ChevronLeft } from "lucide-react"
import type { RaceEntry, StatsData } from "@/app/page"

// ── データ読み込み ─────────────────────────────────────────

function loadData(): { races: RaceEntry[]; stats: StatsData | null } {
  try {
    const filePath = path.join(process.cwd(), "output", "latest_data.json")
    const raw = fs.readFileSync(filePath, "utf-8")
    const json = JSON.parse(raw)
    return {
      races: (json.races ?? []) as RaceEntry[],
      stats: (json.stats ?? null) as StatsData | null,
    }
  } catch {
    return { races: [], stats: null }
  }
}

// ── ユーティリティ ─────────────────────────────────────────

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const dow = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()]
  return `${d.getMonth() + 1}/${d.getDate()}（${dow}）`
}

function formatEdge(edge: number): string {
  const sign = edge >= 0 ? "+" : ""
  return `${sign}${(edge * 100).toFixed(1)}%`
}

function gradeBadgeClass(grade: string): string {
  if (grade === "G1") return "bg-danger/15 text-danger border border-danger/40"
  if (grade === "G2") return "bg-warn/15 text-warn border border-warn/40"
  return "bg-[oklch(0.6_0.13_250/15%)] text-chart-3 border border-[oklch(0.6_0.13_250/40%)]"
}

function verdictClass(verdict: string): string {
  if (verdict.includes("強推奨")) return "bg-positive/20 text-positive border border-positive/50"
  if (verdict.includes("推奨")) return "bg-positive/15 text-positive border border-positive/30"
  if (verdict.includes("保留")) return "bg-warn/20 text-warn border border-warn/40"
  if (verdict.includes("様子見")) return "bg-warn/15 text-warn border border-warn/30"
  return "bg-danger/15 text-danger border border-danger/30"
}

function edgeValueClass(edge: number): string {
  if (edge >= 0.06) return "text-positive font-bold"
  if (edge >= 0) return "text-warn"
  return "text-danger"
}

function finishInfo(finish: number): { icon: string; text: string; cls: string } {
  if (finish === 1) return { icon: "🟢", text: "1着 的中", cls: "text-positive font-semibold" }
  if (finish <= 3) return { icon: "🟡", text: `${finish}着 複勝圏`, cls: "text-warn font-medium" }
  return { icon: "🔴", text: `${finish}着 外れ`, cls: "text-muted-foreground" }
}

// ── 結果カード ─────────────────────────────────────────────

function ResultCard({ race }: { race: RaceEntry }) {
  const ar = race.actual_result!
  const honmei = race.prediction.honmei
  const fi = finishInfo(ar.honmei_finish)
  const winner = ar.result?.find((r) => r.finish === 1)

  return (
    <div className="rounded-xl border border-gold-faint bg-card/70 p-4 sm:p-5">
      {/* 上段: 日付・グレード・レース名・着順結果 */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">{formatDate(race.race_date)}</span>
          <span
            className={`shrink-0 rounded px-2 py-0.5 text-xs font-bold ${gradeBadgeClass(race.grade)}`}
          >
            {race.grade}
          </span>
          <span className="font-serif text-base font-semibold">{race.race_name}</span>
        </div>
        <span className={`shrink-0 text-sm ${fi.cls}`}>
          {fi.icon} {fi.text}
        </span>
      </div>

      {/* 中段: 本命・エッジ・判定 */}
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2">
        <div className="flex items-center gap-1.5">
          <span className="font-serif text-lg font-bold leading-none text-gold">◎</span>
          <span className="text-sm font-medium">{honmei.horse_name}</span>
          <span className="text-xs text-muted-foreground">
            {honmei.popularity > 0 ? `${honmei.popularity}番人気` : ""}
            {honmei.odds > 0 ? ` ${honmei.odds}倍` : ""}
          </span>
        </div>
        <div>
          <span className="text-xs text-muted-foreground">エッジ </span>
          <span className={`font-mono text-sm font-bold ${edgeValueClass(honmei.edge)}`}>
            {formatEdge(honmei.edge)}
          </span>
        </div>
        <span className={`rounded-md border px-2.5 py-1 text-xs font-medium ${verdictClass(race.verdict)}`}>
          {race.verdict}
        </span>
      </div>

      {/* 1着馬 */}
      {winner && (
        <p className="mt-2 text-xs text-muted-foreground">
          1着:{" "}
          <span className="font-medium text-foreground/80">{winner.horse_name}</span>
          （{winner.popularity}番人気 単勝{winner.tansho_odds}倍）
        </p>
      )}

      {/* 結果コメント */}
      {ar.verdict_result && (
        <p className="mt-2 text-[11px] text-foreground/70">{ar.verdict_result}</p>
      )}
      {ar.edge_accuracy_note && (
        <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground/75">
          {ar.edge_accuracy_note}
        </p>
      )}
    </div>
  )
}

// ── ページ ───────────────────────────────────────────────

export default function ResultsPage() {
  const { races, stats } = loadData()

  const resultRaces = races
    .filter((r) => r.actual_result !== undefined)
    .sort((a, b) => b.race_date.localeCompare(a.race_date))

  const pnlCount = resultRaces.filter(
    (r) => r.actual_result?.pnl && r.actual_result.pnl.invested > 0,
  ).length
  const showRoi = pnlCount >= 10 && stats?.tansho_roi != null

  const SAMPLE_TARGET = 30

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <main className="mx-auto max-w-[900px] px-5 pb-16 pt-10">
        {/* パンくず + タイトル */}
        <div className="mb-8">
          <a
            href="/"
            className="mb-3 inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-gold"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            トップ
          </a>
          <h1 className="font-serif text-3xl font-bold text-gold-gradient">的中実績</h1>
          <p className="mt-1 text-sm text-muted-foreground">公開予測の全記録</p>
          {stats && (
            <p className="mt-1 text-xs text-muted-foreground/70">
              公開開始: {stats.public_start_date} ／ 最終更新: {stats.last_updated}
            </p>
          )}
        </div>

        {/* 累計サマリーカード */}
        {stats ? (
          <div className="mb-8 rounded-xl border border-gold-faint bg-card/70 p-5 sm:p-6">
            <p className="mb-4 text-xs font-medium tracking-wide text-gold">累計サマリー</p>

            {/* サンプル蓄積中プログレスバー */}
            {stats.total_races < SAMPLE_TARGET && (
              <div className="mb-5">
                <div className="mb-1.5 flex items-baseline justify-between">
                  <span className="text-xs text-muted-foreground">
                    サンプル蓄積中（{stats.total_races}/{SAMPLE_TARGET}R）
                  </span>
                  <span className="text-xs text-warn">
                    {SAMPLE_TARGET - stats.total_races}R で統計評価可能
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-border/50">
                  <div
                    className="h-2 rounded-full bg-warn transition-all"
                    style={{
                      width: `${Math.min(100, (stats.total_races / SAMPLE_TARGET) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            )}

            {/* 統計グリッド */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="text-center">
                <p className="text-xs text-muted-foreground">
                  <span className="text-gold">◎</span>的中率
                </p>
                <p className="mt-2 font-serif text-3xl font-bold text-gold-gradient">
                  {(stats.honmei_win_rate * 100).toFixed(1)}
                  <span className="text-base font-normal">%</span>
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {stats.honmei_wins}/{stats.total_races}R
                </p>
              </div>

              <div className="text-center">
                <p className="text-xs text-muted-foreground">複勝率</p>
                <p className="mt-2 font-serif text-3xl font-bold text-gold-gradient">
                  {(stats.honmei_place_rate * 100).toFixed(1)}
                  <span className="text-base font-normal">%</span>
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">3着以内</p>
              </div>

              <div className="text-center">
                <p className="text-xs text-muted-foreground">検証R数</p>
                <p className="mt-2 font-serif text-3xl font-bold text-gold-gradient">
                  {stats.total_races}
                  <span className="text-base font-normal">R</span>
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">実績記録済み</p>
              </div>

              {showRoi ? (
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">単勝回収率</p>
                  <p className="mt-2 font-serif text-3xl font-bold text-gold-gradient">
                    {stats.tansho_roi!.toFixed(1)}
                    <span className="text-base font-normal">%</span>
                  </p>
                  <p className="mt-1 text-[11px] text-muted-foreground">{pnlCount}R記録</p>
                </div>
              ) : (
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">単勝回収率</p>
                  <p className="mt-2 font-serif text-2xl font-bold text-muted-foreground">—</p>
                  <p className="mt-1 text-[11px] text-muted-foreground/60">
                    10R以上で表示
                  </p>
                </div>
              )}
            </div>

            {stats.note && (
              <p className="mt-4 text-[11px] text-muted-foreground/70">{stats.note}</p>
            )}
          </div>
        ) : (
          <div className="mb-8 rounded-xl border border-gold-faint bg-card/60 p-8 text-center">
            <p className="text-sm text-muted-foreground">実績データ準備中</p>
          </div>
        )}

        {/* レース別結果一覧 */}
        <div className="mb-6 flex items-baseline justify-between">
          <h2 className="font-serif text-xl font-semibold">レース別結果</h2>
          <span className="text-xs text-muted-foreground">{resultRaces.length}件</span>
        </div>

        {resultRaces.length === 0 ? (
          <div className="rounded-xl border border-gold-faint bg-card/60 p-12 text-center">
            <p className="text-sm text-muted-foreground">実績データ準備中</p>
            <p className="mt-2 text-xs text-muted-foreground/70">
              レース後に result_checker.py が照合・記録します
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {resultRaces.map((race) => (
              <ResultCard key={`${race.race_name}-${race.race_date}`} race={race} />
            ))}
          </div>
        )}

        {/* 注記 */}
        <div className="mt-10 rounded-xl border border-gold-faint/40 bg-card/40 p-5 text-xs leading-relaxed text-muted-foreground">
          <p>※ 結果は公開予測のみ対象です。バックテスト値とは異なります。</p>
          <p className="mt-1">
            ※ 30R 以上で統計的評価が可能になります。現在は参考値としてご確認ください。
          </p>
          <p className="mt-1">
            ※ 購入の最終判断はユーザーが行います。本サービスは馬券購入を勧誘するものではありません。
          </p>
        </div>
      </main>

      <SiteFooter />
    </div>
  )
}
