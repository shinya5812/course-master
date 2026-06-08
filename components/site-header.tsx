import Image from "next/image"
import { nav } from "@/lib/data"

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-gold-faint bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-20 max-w-[1180px] items-center justify-between px-5">
        <div className="flex items-center gap-3">
          <Image
            src="/images/course-master-logo.png"
            alt="COURSE MASTER ロゴ"
            width={120}
            height={120}
            className="h-12 w-12 object-contain"
            priority
          />
          <div className="leading-tight">
            <p className="font-serif text-xl font-semibold tracking-wide text-gold-gradient">
              COURSE MASTER
            </p>
            <p className="text-[11px] text-muted-foreground">
              競馬市場の歪みを指数化する予測エンジン
            </p>
          </div>
        </div>

        <nav className="hidden items-center gap-7 lg:flex">
          {nav.map((item) => (
            <a
              key={item.label}
              href="#"
              className={`relative text-sm transition-colors hover:text-gold ${
                item.active ? "text-gold" : "text-foreground/80"
              }`}
            >
              {item.label}
              {item.active && (
                <span className="absolute -bottom-[26px] left-0 h-0.5 w-full bg-gold" />
              )}
            </a>
          ))}
        </nav>
      </div>
    </header>
  )
}
