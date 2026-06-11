import { Analytics } from '@vercel/analytics/next'
import type { Metadata } from 'next'
import { Geist_Mono, Noto_Sans_JP, Noto_Serif_JP } from 'next/font/google'
import { ScrollToTop } from '@/components/scroll-to-top'
import './globals.css'

const notoSansJp = Noto_Sans_JP({
  variable: '--font-noto-sans-jp',
  subsets: ['latin'],
  weight: ['400', '500', '700'],
})
const notoSerifJp = Noto_Serif_JP({
  variable: '--font-noto-serif-jp',
  subsets: ['latin'],
  weight: ['500', '600', '700'],
})
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'COURSE MASTER｜競馬市場の歪みを指数化する予測エンジン',
  description:
    '12軸スコア×4チーム合議制で導き出すJRAレースのエッジと荒れ指数。データドリブンで期待値の高い予測を提供する競馬予測エンジン COURSE MASTER。',
  generator: 'v0.app',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="ja"
      className={`${notoSansJp.variable} ${notoSerifJp.variable} ${geistMono.variable} bg-background`}
    >
      <body className="font-sans antialiased">
        {children}
        <ScrollToTop />
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
