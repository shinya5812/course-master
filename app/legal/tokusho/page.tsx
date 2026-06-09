import { SiteHeader } from "@/components/site-header"
import { ChevronLeft } from "lucide-react"

export default function TokushoPage() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] px-5 text-center">
        <p className="text-xs font-mono tracking-widest text-gold uppercase">Legal</p>
        <h1 className="mt-4 font-serif text-3xl font-bold text-gold-gradient">特定商取引法に基づく表記</h1>
        <p className="mt-4 text-sm text-muted-foreground leading-relaxed">
          このページは現在準備中です。<br />
          特定商取引法に基づく表記は近日公開予定です。
        </p>
        <a
          href="/"
          className="mt-8 inline-flex items-center gap-2 rounded-md border border-gold-faint px-6 py-3 text-sm text-foreground/90 transition-colors hover:border-gold hover:text-gold"
        >
          <ChevronLeft className="h-4 w-4" />
          トップに戻る
        </a>
      </main>
    </div>
  )
}
