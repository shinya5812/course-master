import { ChevronRight } from "lucide-react"
import type { RaceEntry } from "@/app/page"

type Props = {
  races: RaceEntry[]
}

// ── ユーティリティ ────────────────────────────────────────

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const dow = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()]
  return `${d.getMonth() + 1}/${d.getDate()} (${dow})`
}

function formatEdge(edge: number): string {
  const sign = edge >= 0 ? "+" : ""
  return `${sign}${edge.toFixed(3)}`
}

function gradeBadgeClass(grade: string): string {
  if (grade === "G1") return "bg-red-600 text-white"
  if (grade === "G2") return "bg-purple-600 text-white"
  if (grade === "G3") return "bg-blue-600 text-white"
  return "bg-muted text-muted-foreground border border-border"
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
    return "bg-positive/20 text-positive border border-positive/50 shadow-[0_0_10px_oklch(0.78_0.16_150/35%)]"
  if (verdict.includes("推奨"))
    return "bg-positive/15 text-positive border border-positive/30"
  if (verdict.includes("様子見"))
    return "bg-warn/15 text-warn border border-warn/30"
  if (verdict.includes("保留"))
    return "bg-warn/20 text-warn border border-warn/40"
  return "bg-danger/15 text-danger border border-danger/30"
}

function edgeValueClass(edge: number): string {
  if (edge >= 0.06) return "text-positive"
  if (edge >= 0) return "text-warn"
  return "text-danger"
}

function resultInfo(finish: number): { label: string; cls: string } {
  if (finish === 1) return { label: "◎1着 的中!", cls: "text-positive font-semibold" }
  if (finish <= 3) return { label: `◎${finish}着 複勝圏`, cls: "text-warn" }
  return { label: `◎${finish}着 外れ`, cls: "text-muted-foreground" }
}

// ── カード ───────────────────────────────────────────────

function RaceCard({ race }: { race: RaceEntry }) {
  const honmei = race.prediction.honmei
  const ar = race.actual_result

  return (
    <div className="flex flex-col rounded-xl border border-gold-faint bg-card/70 p-5 transition-colors hover:border-gold/60">
      {/* グレードバッジ＋レース名 */}
      <div className="flex items-center gap-2">
        <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-bold ${gradeBadgeClass(race.grade)}`}>
          {race.grade}
        </span>
        <h3 className="flex-1 font-serif text-base font-semibold truncate">{race.race_name}</h3>
        {race.anaba_flag && (
          <span className="shrink-0 rounded bg-gold/20 px-1.5 py-0.5 text-[10px] font-bold text-gold border border-gold/40">
            穴馬★
          </span>
        )}
      </div>
      <p className="mt-1 text-[11px] text-muted-foreground">
        {formatDate(race.race_date)} {race.venue} {race.surface}{race.distance}m
        {race.track_cond ? ` (${race.track_cond})` : ""}
      </p>

      {/* 荒れ指数バー */}
      <div className="mt-4">
        <div className="flex items-baseline justify-between mb-1.5">
          <span className="text-[10px] text-muted-foreground tracking-wide">荒れ指数 ADI</span>
          <span className={`font-serif text-xl font-bold ${adiTextClass(race.adi)}`}>
            {race.adi.toFixed(1)}
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-border/50 overflow-hidden">
          <div
            className={`h-2 rounded-full ${adiBarClass(race.adi)}`}
            style={{ width: `${Math.min(100, Math.max(0, race.adi))}%` }}
          />
        </div>
        <p className="mt-1 text-[10px] text-muted-foreground">{race.adi_label}</p>
      </div>

      {/* 本命馬 */}
      <div className="mt-4 rounded-lg border border-gold-faint bg-gold/5 px-4 py-3 text-center">
        <p className="text-[10px] tracking-widest text-gold">本命 ◎</p>
        <p className="mt-1 font-serif text-xl font-bold text-foreground">{honmei.horse_name}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {honmei.popularity > 0 ? `${honmei.popularity}番人気` : ""}
          {honmei.odds > 0 ? ` ${honmei.odds}倍` : ""}
        </p>
      </div>

      {/* エッジ＋判定 */}
      <div className="mt-3 flex items-stretch gap-2">
        <div className="flex-1 rounded-md border border-gold-faint bg-card px-3 py-2 text-center">
          <p className="text-[10px] text-muted-foreground">エッジ</p>
          <p className={`font-mono text-lg font-bold ${edgeValueClass(honmei.edge)}`}>
            {formatEdge(honmei.edge)}
          </p>
        </div>
        <div className={`flex-1 flex items-center justify-center rounded-md px-3 py-2 text-xs font-semibold leading-snug text-center ${verdictClass(race.verdict)}`}>
          {race.verdict}
        </div>
      </div>

      {/* 結果（actual_result がある場合） */}
      {ar && (
        <div className="mt-3 border-t border-gold-faint pt-3 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className={resultInfo(ar.honmei_finish).cls}>
              {resultInfo(ar.honmei_finish).label}
            </span>
            {ar.result && ar.result[0] && (
              <span className="text-muted-foreground truncate">
                1着: {ar.result[0].horse_name} ({ar.result[0].tansho_odds}倍)
              </span>
            )}
          </div>
          {ar.verdict_result && (
            <p className="mt-1 text-[10px] text-muted-foreground">{ar.verdict_result}</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── セクション ────────────────────────────────────────────

export function WeeklyRaces({ races }: Props) {
  const colsClass =
    races.length <= 1
      ? "sm:grid-cols-1 sm:max-w-sm"
      : races.length === 2
      ? "sm:grid-cols-2"
      : races.length === 3
      ? "sm:grid-cols-2 lg:grid-cols-3"
      : "sm:grid-cols-2 lg:grid-cols-4"

  return (
    <section className="mx-auto max-w-[1180px] px-5 py-8">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-2xl font-semibold">今週の重賞予測</h2>
        <a
          href="/weekly"
          className="flex items-center gap-1 text-xs text-foreground/80 transition-colors hover:text-gold"
        >
          すべてのレースを見る
          <ChevronRight className="h-3.5 w-3.5" />
        </a>
      </div>

      {races.length === 0 ? (
        <div className="mt-6 rounded-xl border border-gold-faint bg-card/60 p-10 text-center">
          <p className="text-sm text-muted-foreground">次回レース予測データを更新後に表示されます</p>
          <p className="mt-2 text-xs text-muted-foreground/70">土曜・日曜の週次フロー実行後に自動反映</p>
        </div>
      ) : (
        <div className={`mt-6 grid grid-cols-1 gap-5 ${colsClass}`}>
          {races.map((race) => (
            <RaceCard key={`${race.race_name}-${race.race_date}`} race={race} />
          ))}
        </div>
      )}
    </section>
  )
}
