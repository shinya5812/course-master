import { ChevronRight, Star } from "lucide-react"
import { ranking } from "@/lib/data"

export function RankingTable() {
  return (
    <div className="rounded-xl border border-gold-faint bg-card/60 p-6">
      <h2 className="font-serif text-xl font-semibold">
        エッジ上位ランキング <span className="text-xs text-muted-foreground">（今週）</span>
      </h2>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[480px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-gold-faint text-[11px] text-muted-foreground">
              <th className="py-2 text-left font-normal">順位</th>
              <th className="py-2 text-left font-normal">馬番</th>
              <th className="py-2 text-left font-normal">馬名</th>
              <th className="py-2 text-left font-normal">レース</th>
              <th className="py-2 text-right font-normal">推定勝率</th>
              <th className="py-2 text-right font-normal">市場確率</th>
              <th className="py-2 text-right font-normal text-gold">エッジ</th>
              <th className="py-2 text-center font-normal">判定</th>
            </tr>
          </thead>
          <tbody>
            {ranking.map((row) => (
              <tr key={row.rank} className="border-b border-gold-faint/50">
                <td className="py-3 text-left text-muted-foreground">{row.rank}</td>
                <td className="py-3 text-left font-medium text-gold">{row.no}</td>
                <td className="py-3 text-left text-foreground/90">{row.name}</td>
                <td className="py-3 text-left text-foreground/80">{row.race}</td>
                <td className="py-3 text-right">{row.est}</td>
                <td className="py-3 text-right text-muted-foreground">{row.mkt}</td>
                <td className="py-3 text-right text-positive">{row.edge}</td>
                <td className="py-3 text-center">
                  <Star className="mx-auto h-3.5 w-3.5 fill-gold text-gold" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
