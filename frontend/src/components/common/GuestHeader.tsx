import Link from 'next/link'
import { ArrowLeft, Sparkles } from 'lucide-react'

interface GuestHeaderProps {
  primaryHref: string
  primaryLabel: string
  showBackIcon?: boolean
}

export function GuestHeader({ primaryHref, primaryLabel, showBackIcon = false }: GuestHeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-stone-200/60 bg-white/80 backdrop-blur-sm">
      <div className="mx-auto flex min-h-14 max-w-6xl flex-col gap-3 px-6 py-3 sm:flex-row sm:items-center sm:justify-between sm:py-0">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="text-base font-semibold text-stone-800">Lumina</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <nav aria-label="主导航" className="flex items-center gap-3">
            <Link
              href={primaryHref}
              className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-sm font-medium text-stone-600 shadow-sm transition-colors hover:text-stone-900"
            >
              {showBackIcon ? <ArrowLeft className="h-4 w-4" /> : null}
              {primaryLabel}
            </Link>
          </nav>

          <nav
            aria-label="账户操作"
            className="flex items-center gap-2 border-l border-stone-200 pl-3 sm:gap-3 sm:pl-4"
          >
            <Link
              href="/login"
              className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-sm font-medium text-stone-600 shadow-sm transition-colors hover:text-stone-900"
            >
              登录
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            >
              注册
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}
