import Image from "next/image"
import Link from "next/link"
import { nav } from "@/lib/data"

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-gold-faint bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-20 max-w-[1180px] items-center justify-between px-5">
        <Link href="/">
          <Image
            src="/logo.png"
            alt="COURSE MASTER"
            width={300}
            height={60}
            priority
            className="h-12 w-auto"
          />
        </Link>

        <nav className="hidden items-center gap-7 lg:flex">
          {nav.map((item) => (
            <a
              key={item.label}
              href={item.href ?? "#"}
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
