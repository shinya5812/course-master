import { ChevronRight } from "lucide-react"
import type { EdgeRankEntry } from "@/app/page"

type Props = {
  ranking: EdgeRankEntry[]
}

function edgeValueClass(edge: number): string {
  if (edge >= 0.06) return "text-positive font-bold"
  if (edge >= 0) return "text-warn"
  return "text-danger"
}

function edgeBgClass(edge: number): string {
  if (edge >= 0.06) return "bg-positive/10 border border-positive/25 rounded px-1.5 py-0.5"
  if (edge >= 0) return "bg-warn/10 border border-warn/25 rounded px-1.5 py-0.5"
  return ""
}

function edgeStr(edge: number): string {
  const sign = edge >= 0 ? "+" : ""
  return `${sign}${(edge * 100).toFixed(1)}%`
}

function markClass(mark: string): string {
  if (mark === "◎") return "text-gold font-bold text-base"
  if (mark === "○") return "text-foreground/80 font-medium"
  return "text-muted-foreground"
}

export function RankingTable({ ranking }: Props) {
  return (
    <div className="rounded-xl border border-gold-faint bg-card/60 p-6">
      <h2 className="font-serif text-xl font-semibold">
        エッジ上位ランキング{" "}
        <span className="text-xs text-muted-foreground">（今週）</span>
      </h2>

      <div className="mt-5 overflow-x-auto">
        {ranking.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            エッジデータを更新後に表示されます
          </p>
        ) : (
          <table className="w-full min-w-[480px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-gold-faint text-[11px] text-muted-foreground">
                <th className="py-2 text-left font-normal">順位</th>
                <th className="py-2 text-left font-normal">印</th>
                <th className="py-2 text-left font-normal">馬名</th>
                <th className="py-2 text-left font-normal">レース</th>
                <th className="py-2 text-right font-normal">推定勝率</th>
                <th className="py-2 text-right font-normal">市場確率</th>
                <th className="py-2 text-right font-normal text-gold">エッジ</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((row) => (
                <tr key={row.rank} className="border-b border-gold-faint/50 hover:bg-gold/5 transition-colors">
                  <td className="py-3 text-left text-muted-foreground">{row.rank}</td>
                  <td className={`py-3 text-left ${markClass(row.mark)}`}>{row.mark}</td>
                  <td className="py-3 text-left">
                    <span className="text-foreground/90 font-medium">{row.horse_name}</span>
                    <span className="ml-1.5 text-[10px] text-muted-foreground">
                      {row.popularity > 0 ? `${row.popularity}人気` : ""}
                    </span>
                  </td>
                  <td className="py-3 text-left text-xs text-foreground/70 max-w-[120px] truncate">
                    {row.race_name}
                  </td>
                  <td className="py-3 text-right text-positive">{row.est_win_prob}</td>
                  <td className="py-3 text-right text-muted-foreground">{row.mkt_win_prob}</td>
                  <td className="py-3 text-right">
                    <span className={`${edgeValueClass(row.edge)} ${edgeBgClass(row.edge)}`}>
                      {edgeStr(row.edge)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <a
        href="#"
        className="mx-auto mt-5 flex w-fit items-center gap-2 rounded-md border border-gold-faint px-6 py-2.5 text-xs text-foreground/90 transition-colors hover:border-gold hover:text-gold"
      >
        すべてのランキングを見る
        <ChevronRight className="h-3.5 w-3.5" />
      </a>
    </div>
  )
}
