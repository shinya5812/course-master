"use client"

import { useEffect, useState } from "react"
import { ChevronUp } from "lucide-react"

export function ScrollToTop() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY >= 300)
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  if (!visible) return null

  return (
    <button
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="ページトップへ戻る"
      className="fixed bottom-6 right-6 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-[#c9a84c] text-black shadow-lg transition-transform hover:scale-110 active:scale-95"
    >
      <ChevronUp className="h-5 w-5 stroke-[2.5]" />
    </button>
  )
}
