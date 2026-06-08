import { ChevronRight, Network, BarChart3, Crosshair, RefreshCw } from "lucide-react"
import { features, news } from "@/lib/data"

const icons = [Network, BarChart3, Crosshair, RefreshCw]

export function FeaturesNews() {
  return (
    <section className="mx-auto max-w-[1180px] px-5 py-8">
      <div className="grid grid-cols-1 gap-6 rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8 lg:grid-cols-[1.6fr_1fr]">
        {/* Features */}
        <div className="lg:border-r lg:border-gold-faint lg:pr-8">
          <h2 className="font-serif text-xl font-semibold">COURSE MASTER の特徴</h2>
          <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
            {features.map((feature, i) => {
              const Icon = icons[i]
              return (
                <div key={feature.title} className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <Icon className="h-5 w-5 text-gold" />
                    <h3 className="text-sm font-semibold text-foreground/90">
                      {feature.title}
                    </h3>
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {feature.desc}
                  </p>
                </div>
              )
            })}
          </div>
        </div>

        {/* News */}
        <div>
          <h2 className="font-serif text-xl font-semibold">お知らせ</h2>
          <ul className="mt-6 space-y-4">
            {news.map((item) => (
              <li key={item.date} className="flex flex-col gap-0.5">
                <span className="font-mono text-[11px] text-gold">{item.date}</span>
                <a href="#" className="text-sm text-foreground/85 transition-colors hover:text-gold">
                  {item.text}
                </a>
              </li>
            ))}
          </ul>
          <a
            href="#"
            className="mt-6 flex items-center gap-1 text-xs text-foreground/80 transition-colors hover:text-gold"
          >
            お知らせ一覧へ
            <ChevronRight className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>
    </section>
  )
}
