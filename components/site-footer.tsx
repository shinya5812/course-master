import Image from "next/image"

const footerLinks = ["利用規約", "プライバシーポリシー", "特定商取引法に基づく表記", "お問い合わせ"]

export function SiteFooter() {
  return (
    <footer className="border-t border-gold-faint">
      <div className="mx-auto max-w-[1180px] px-5 py-10">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Image
              src="/images/course-master-logo.png"
              alt="COURSE MASTER ロゴ"
              width={100}
              height={100}
              className="h-11 w-11 object-contain"
            />
            <div className="leading-tight">
              <p className="font-serif text-lg font-semibold text-gold-gradient">
                COURSE MASTER
              </p>
              <p className="text-[11px] text-muted-foreground">
                競馬市場の歪みを指数化する予測エンジン
              </p>
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {footerLinks.map((link) => (
              <a
                key={link}
                href="#"
                className="text-xs text-foreground/75 transition-colors hover:text-gold"
              >
                {link}
              </a>
            ))}
          </nav>
        </div>

        <p className="mt-8 text-[11px] text-muted-foreground">
          © 2026 COURSE MASTER All Rights Reserved.
        </p>
      </div>
    </footer>
  )
}
