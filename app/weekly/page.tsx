import fs from "fs"
import path from "path"
import { SiteHeader } from "@/components/site-header"
import { SiteFooter } from "@/components/site-footer"
import { ChevronLeft } from "lucide-react"
import type { RaceEntry, StatsData } from "@/app/page"

export const dynamic = 'force-dynamic'

// ── データ読み込み ─────────────────────────────────────────

function loadData(): { races: RaceEntry[]; stats: StatsData | null; last_updated: string } {
  try {
    const filePath = path.join(process.cwd(), "output", "latest_data.json")
    const raw = fs.readFileSync(filePath, "utf-8")
    const json = JSON.parse(raw)
    return {
      races: (json.races ?? []) as RaceEntry[],
      stats: (json.stats ?? null) as StatsData | null,
      last_updated: (json.stats?.last_updated ?? "") as string,
    }
  } catch {
    return { races: [], stats: null, last_updated: "" }
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

function adiBarClass(adi: number): string {
  if (adi < 50) return "bg-positive"
  if (adi < 70) return "bg-warn"
  if (adi < 85) return "bg-danger/70"
  return "bg-danger"
}

function adiTextClass(adi: number): string {
  if (adi < 50) return "text-positive"
  if (adi < 70) return "text-warn"
  return "text-danger"
}

function verdictClass(verdict: string): string {
  if (verdict.includes("強推奨"))
    return "bg-positive/20 text-positive border border-positive/50 shadow-[0_0_10px_oklch(0.78_0.16_150/25%)]"
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

function finishLabel(finish: number): { text: string; cls: string } {
  if (finish === 1) return { text: "◎1着 的中!", cls: "text-positive font-semibold" }
  if (finish <= 3) return { text: `◎${finish}着 複勝圏`, cls: "text-warn font-medium" }
  return { text: `◎${finish}着 外れ`, cls: "text-muted-foreground" }
}

// ── レースカード ───────────────────────────────────────────

function RaceCard({ race }: { race: RaceEntry }) {
  const honmei = race.prediction.honmei
  const renpuku = race.prediction.renpuku ?? []
  const santen = race.prediction.santen ?? []
  const ar = race.actual_result
  const isHold = race.verdict.includes("保留")

  return (
    <article className="rounded-xl border border-gold-faint bg-card/70 p-5 lg:p-6">
      {/* ベット保留バナー */}
      {isHold && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-warn/40 bg-warn/10 px-4 py-2 text-xs font-medium text-warn">
          🟠 ベット保留 — 距離2200m以上（検証専用・データ蓄積中）
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-[1fr_1.2fr]">
        {/* 左: レース情報 + 荒れ指数 */}
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-bold ${gradeBadgeClass(race.grade)}`}>
              {race.grade}
            </span>
            <h2 className="font-serif text-lg font-semibold leading-snug">{race.race_name}</h2>
            {race.anaba_flag && (
              <span className="shrink-0 rounded border border-gold/40 bg-gold/20 px-1.5 py-0.5 text-[10px] font-bold text-gold">
                穴馬★
              </span>
            )}
          </div>
          <p className="mt-1.5 text-xs text-muted-foreground">
            {formatDate(race.race_date)} {race.venue} {race.surface}{race.distance}m
            {race.track_cond ? `（${race.track_cond}）` : ""}
            {race.heads ? ` ${race.heads}頭立て` : ""}
          </p>

          {/* 荒れ指数バー */}
          <div className="mt-4">
            <div className="mb-1.5 flex items-baseline justify-between">
              <span className="text-[10px] tracking-wide text-muted-foreground">荒れ指数 ADI</span>
              <span className={`font-serif text-2xl font-bold ${adiTextClass(race.adi)}`}>
                {race.adi.toFixed(1)}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-border/50">
              <div
                className={`h-2 rounded-full transition-all ${adiBarClass(race.adi)}`}
                style={{ width: `${Math.min(100, Math.max(0, race.adi))}%` }}
              />
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground">{race.adi_label}</p>
          </div>

          {/* 判定バッジ */}
          <div className={`mt-4 inline-flex rounded-lg border px-3 py-1.5 text-xs font-semibold ${verdictClass(race.verdict)}`}>
            {race.verdict}
          </div>
          {race.verdict_detail && (
            <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">
              {race.verdict_detail}
            </p>
          )}
        </div>

        {/* 右: 予測印 */}
        <div className="flex flex-col gap-2">
          {/* ◎ 本命（大きく） */}
          <div className="rounded-lg border border-gold/30 bg-gold/5 px-4 py-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-start gap-2.5">
                <span className="font-serif text-2xl font-bold leading-none text-gold">◎</span>
                <div>
                  <p className="font-serif text-base font-semibold leading-snug">{honmei.horse_name}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    {honmei.popularity > 0 ? `${honmei.popularity}番人気` : ""}
                    {honmei.odds > 0 ? ` ${honmei.odds}倍` : ""}
                  </p>
                </div>
              </div>
              <div className="shrink-0 text-right">
                <p className="text-[10px] text-muted-foreground">エッジ</p>
                <p className={`font-mono text-base font-bold ${edgeValueClass(honmei.edge)}`}>
                  {formatEdge(honmei.edge)}
                </p>
              </div>
            </div>
          </div>

          {/* ○ 連複（中サイズ） */}
          {renpuku.length > 0 && (
            <div className="space-y-1.5">
              {renpuku.map((h) => (
                <div
                  key={h.horse_no}
                  className="flex items-center justify-between rounded-md border border-gold-faint bg-card/40 px-3 py-2"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="shrink-0 text-sm font-medium text-foreground/80">○</span>
                    <span className="truncate text-sm text-foreground/90">{h.horse_name}</span>
                    <span className="shrink-0 text-[10px] text-muted-foreground">
                      {h.popularity > 0 ? `${h.popularity}人気` : ""}
                      {h.odds > 0 ? ` ${h.odds}倍` : ""}
                    </span>
                  </div>
                  <span className={`shrink-0 font-mono text-xs ${edgeValueClass(h.edge)}`}>
                    {formatEdge(h.edge)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* ▲ 三番手（小サイズ） */}
          {santen.length > 0 && (
            <div className="space-y-1">
              {santen.map((h) => (
                <div key={h.horse_no} className="flex items-center justify-between px-3 py-1">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="shrink-0 text-xs text-muted-foreground">▲</span>
                    <span className="truncate text-xs text-foreground/70">{h.horse_name}</span>
                    <span className="shrink-0 text-[10px] text-muted-foreground/70">
                      {h.popularity > 0 ? `${h.popularity}人気` : ""}
                    </span>
                  </div>
                  <span className={`shrink-0 font-mono text-[11px] ${edgeValueClass(h.edge)}`}>
                    {formatEdge(h.edge)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 結果セクション */}
      {ar && (
        <div className="mt-5 rounded-lg border border-gold-faint/60 bg-background/40 p-4">
          <p className="mb-2 text-[10px] font-medium tracking-widest text-gold">レース結果</p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className={`text-sm ${finishLabel(ar.honmei_finish).cls}`}>
              {finishLabel(ar.honmei_finish).text}
            </span>
            {ar.result && ar.result[0] && (
              <span className="text-xs text-muted-foreground">
                1着: {ar.result[0].horse_name}（単勝{ar.result[0].tansho_odds}倍）
              </span>
            )}
          </div>
          {ar.verdict_result && (
            <p className="mt-1.5 text-[11px] text-foreground/70">{ar.verdict_result}</p>
          )}
          {ar.edge_accuracy_note && (
            <p className="mt-1 text-[10px] leading-relaxed text-muted-foreground/75">
              {ar.edge_accuracy_note}
            </p>
          )}
        </div>
      )}
    </article>
  )
}

// ── 過去レース折りたたみカード ────────────────────────────

function CollapsedRaceCard({ race }: { race: RaceEntry }) {
  const ar = race.actual_result!
  const honmei = race.prediction.honmei
  const fi = finishLabel(ar.honmei_finish)

  return (
    <details className="rounded-xl border border-gold-faint/50 overflow-hidden">
      {/* 折りたたみヘッダー（常時表示） */}
      <summary className="list-none cursor-pointer px-5 py-3 bg-card/50 hover:bg-card/80 transition-colors">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="text-xs text-muted-foreground">{formatDate(race.race_date)}</span>
          <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-bold ${gradeBadgeClass(race.grade)}`}>
            {race.grade}
          </span>
          <span className="font-serif text-sm font-semibold">{race.race_name}</span>
          <span className="text-xs text-muted-foreground">◎{honmei.horse_name}</span>
          <span className={`text-sm font-medium ${fi.cls}`}>{fi.text}</span>
          <span className={`ml-auto shrink-0 rounded-md border px-2.5 py-0.5 text-xs font-medium ${verdictClass(race.verdict)}`}>
            {race.verdict}
          </span>
          <span className="shrink-0 text-[10px] text-muted-foreground/60">詳細 ▼</span>
        </div>
      </summary>
      {/* 展開時コンテンツ */}
      <div className="border-t border-gold-faint/30">
        <RaceCard race={race} />
      </div>
    </details>
  )
}

// ── ページ ───────────────────────────────────────────────

export default function WeeklyPage() {
  const { races, stats, last_updated } = loadData()

  // 日付降順ソート（最新レースを上位に）
  const sortedRaces = [...races].sort(
    (a, b) => new Date(b.race_date).getTime() - new Date(a.race_date).getTime(),
  )

  // サマリー計算
  const strongCount = sortedRaces.filter((r) => r.verdict.includes("強推奨")).length
  const recommendCount = sortedRaces.filter(
    (r) => r.verdict.includes("推奨") && !r.verdict.includes("強推奨"),
  ).length
  const avgEdge =
    sortedRaces.length > 0
      ? sortedRaces.reduce((sum, r) => sum + r.prediction.honmei.edge, 0) / sortedRaces.length
      : 0

  const dates = [...new Set(sortedRaces.map((r) => r.race_date))].sort().reverse()
  const grades = [...new Set(sortedRaces.map((r) => r.grade))].sort()

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <main className="mx-auto max-w-[1180px] px-5 pb-16 pt-10">
        {/* パンくず + タイトル */}
        <div className="mb-8">
          <a
            href="/"
            className="mb-3 inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-gold"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            トップ
          </a>
          <div className="flex flex-wrap items-baseline gap-4">
            <h1 className="font-serif text-3xl font-bold text-gold-gradient">今週の重賞予測</h1>
            {last_updated && (
              <span className="text-xs text-muted-foreground">更新: {last_updated}</span>
            )}
          </div>
          {dates.length > 0 && (
            <p className="mt-1.5 text-sm text-foreground/70">
              {dates.map((d) => formatDate(d)).join("・")}
              {grades.length > 0 && (
                <span className="ml-3 text-xs text-muted-foreground">
                  対象: {grades.join(" / ")}
                </span>
              )}
            </p>
          )}
        </div>

        {/* 空データ */}
        {sortedRaces.length === 0 ? (
          <div className="rounded-xl border border-gold-faint bg-card/60 p-16 text-center">
            <p className="text-sm text-muted-foreground">今週の予測は準備中です</p>
            <p className="mt-2 text-xs text-muted-foreground/70">
              土曜・日曜の週次フロー実行後に自動反映されます
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_260px]">
            {/* メイン: レースカード一覧（最新順・過去レースは折りたたみ） */}
            <div className="space-y-5">
              {sortedRaces.map((race) =>
                race.actual_result ? (
                  <CollapsedRaceCard key={`${race.race_name}-${race.race_date}`} race={race} />
                ) : (
                  <RaceCard key={`${race.race_name}-${race.race_date}`} race={race} />
                ),
              )}
            </div>

            {/* サイドバー: サマリー */}
            <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
              {/* 今週サマリー */}
              <div className="rounded-xl border border-gold-faint bg-card/70 p-5">
                <p className="mb-4 text-xs font-medium tracking-wide text-gold">今週のサマリー</p>
                <div className="space-y-3">
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs text-muted-foreground">レース数</span>
                    <span className="font-serif text-2xl font-bold text-gold-gradient">
                      {sortedRaces.length}
                      <span className="text-sm font-normal">R</span>
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">🟢🟢 強推奨</span>
                    <span
                      className={`text-sm font-semibold ${strongCount > 0 ? "text-positive" : "text-muted-foreground"}`}
                    >
                      {strongCount}件
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">🟢 推奨</span>
                    <span
                      className={`text-sm font-semibold ${recommendCount > 0 ? "text-positive" : "text-muted-foreground"}`}
                    >
                      {recommendCount}件
                    </span>
                  </div>
                  <div className="border-t border-gold-faint pt-3">
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-muted-foreground">◎平均エッジ</span>
                      <span className={`font-mono text-sm font-bold ${edgeValueClass(avgEdge)}`}>
                        {formatEdge(avgEdge)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 累計パフォーマンス */}
              {stats && (
                <div className="rounded-xl border border-gold-faint bg-card/70 p-5">
                  <p className="mb-4 text-xs font-medium tracking-wide text-gold">累計パフォーマンス</p>
                  <div className="space-y-2.5">
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-muted-foreground">◎的中率</span>
                      <span className="font-serif text-xl font-bold text-gold-gradient">
                        {(stats.honmei_win_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-muted-foreground">検証R数</span>
                      <span className="text-sm font-semibold text-foreground/80">
                        {stats.total_races}R
                      </span>
                    </div>
                    {stats.tansho_roi != null && (
                      <div className="flex items-baseline justify-between">
                        <span className="text-xs text-muted-foreground">単勝回収率</span>
                        <span className="text-sm font-semibold text-foreground/80">
                          {stats.tansho_roi.toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {stats.note && (
                      <p className="text-[10px] text-muted-foreground/70">{stats.note}</p>
                    )}
                  </div>
                  <a
                    href="/results"
                    className="mt-4 block rounded-md border border-gold-faint py-2 text-center text-xs text-foreground/80 transition-colors hover:border-gold hover:text-gold"
                  >
                    的中実績を詳しく見る →
                  </a>
                </div>
              )}

              {/* 分析メソッドへのリンク */}
              <div className="rounded-xl border border-gold-faint/50 bg-card/40 p-4 text-center">
                <p className="text-xs text-muted-foreground">エッジ・ADIの計算方法</p>
                <a
                  href="/analysis"
                  className="mt-2 inline-block text-xs text-gold transition-colors hover:underline"
                >
                  分析メソッドを見る →
                </a>
              </div>
            </aside>
          </div>
        )}
      </main>

      <SiteFooter />
    </div>
  )
}
