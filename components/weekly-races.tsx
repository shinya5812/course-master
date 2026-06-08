import { ChevronRight, Star } from "lucide-react"
import { weeklyRaces, type RaceCard } from "@/lib/data"

const toneClasses: Record<RaceCard["tagTone"], string> = {
  danger: "bg-danger/15 text-danger border border-danger/30",
  positive: "bg-positive/15 text-positive border border-positive/30",
  warn: "bg-warn/15 text-warn border border-warn/30",
}

function Card({ race }: { race: RaceCard }) {
  return (
    <div className="flex flex-col rounded-xl border border-gold-faint bg-card/70 p-5 transition-colors hover:border-gold/60">
      <div className="flex items-center gap-2">
        <h3 className="font-serif text-lg font-semibold">{race.name}</h3>
        <span className="rounded bg-gold/15 px-1.5 py-0.5 text-[10px] font-bold text-gold">
          {race.grade}
        </span>
      </div>
      <p className="mt-1 text-[11px] text-muted-foreground">{race.schedule}</p>

      <div className="mt-4 flex items-center gap-5">
        <div className="flex items-baseline gap-1.5">
          <span className="text-xs text-muted-foreground">ADI</span>
          <span className="font-serif text-2xl font-bold text-danger">{race.adi}</span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-xs text-muted-foreground">FRI</span>
          <span className="font-serif text-2xl font-bold text-positive">{race.fri}</span>
        </div>
      </div>

      <span
        className={`mt-3 w-fit rounded px-2 py-1 text-[11px] font-medium ${toneClasses[race.tagTone]}`}
      >
        {race.tag}
      </span>

      <div className="mt-4 border-t border-gold-faint pt-4">
        <p className="text-sm">
          <span className="text-gold">◎</span> {race.horseNo}{" "}
          <span className="text-foreground/90">{race.horseName}</span>
        </p>
        <div className="mt-2 flex items-center gap-4 text-[11px] text-muted-foreground">
          <span>
            エッジ <span className="text-positive">{race.edge}</span>
          </span>
          <span>
            推定勝率 <span className="text-foreground/90">{race.winProb}</span>
          </span>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 rounded-md border border-gold-faint bg-gold/5 px-3 py-2.5 text-xs">
        <Star className="h-3.5 w-3.5 fill-gold text-gold" />
        <span className="text-gold">推奨</span>
        <span className="text-muted-foreground">/ 単勝100円</span>
      </div>
    </div>
  )
}

export function WeeklyRaces() {
  return (
    <section className="mx-auto max-w-[1180px] px-5 py-8">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-2xl font-semibold">今週の重賞予測</h2>
        <a
          href="#"
          className="flex items-center gap-1 text-xs text-foreground/80 transition-colors hover:text-gold"
        >
          すべてのレースを見る
          <ChevronRight className="h-3.5 w-3.5" />
        </a>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {weeklyRaces.map((race) => (
          <Card key={race.name} race={race} />
        ))}
      </div>
    </section>
  )
}
