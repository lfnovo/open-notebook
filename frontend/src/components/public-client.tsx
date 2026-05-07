'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { PublicNotebooks } from '@/components/public/PublicNotebooks'
import { PublicSources } from '@/components/public/PublicSources'
import { BookOpen, FileText, Globe, Search, TrendingUp } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { GuestHeader } from '@/components/common/GuestHeader'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

export function PublicContentExplorer({ className = '' }: { className?: string }) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'notebooks' | 'sources'>('notebooks')
  const [rankingMode, setRankingMode] = useState<'most_visited' | 'most_referenced'>('most_visited')

  return (
    <div className={`space-y-5 ${className}`}>
      <div className="rounded-lg border border-stone-200/80 bg-white/85 p-3 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex w-full gap-1 rounded-lg bg-stone-100 p-1 sm:w-auto">
              <button
                onClick={() => setActiveTab('notebooks')}
                className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors sm:flex-none ${
                  activeTab === 'notebooks'
                    ? 'bg-white text-stone-950 shadow-sm'
                    : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                <BookOpen className="h-4 w-4" />
                {t.public?.notebooks || 'Notebooks'}
              </button>
              <button
                onClick={() => setActiveTab('sources')}
                className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors sm:flex-none ${
                  activeTab === 'sources'
                    ? 'bg-white text-stone-950 shadow-sm'
                    : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                <FileText className="h-4 w-4" />
                {t.public?.sources || 'Sources'}
              </button>
            </div>

            <div className="flex w-full gap-1 rounded-lg bg-stone-100 p-1 sm:w-auto">
              <button
                onClick={() => setRankingMode('most_visited')}
                className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors sm:flex-none ${
                  rankingMode === 'most_visited'
                    ? 'bg-white text-stone-950 shadow-sm'
                    : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                <TrendingUp className="h-4 w-4" />
                {t.public?.mostVisited || '最热访问'}
              </button>
              <button
                onClick={() => setRankingMode('most_referenced')}
                className={`flex flex-1 items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors sm:flex-none ${
                  rankingMode === 'most_referenced'
                    ? 'bg-white text-stone-950 shadow-sm'
                    : 'text-stone-500 hover:text-stone-900'
                }`}
              >
                {t.public?.mostReferenced || '引用最多'}
              </button>
            </div>
          </div>

          <div className="relative w-full lg:w-80">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t.public?.searchPlaceholder || 'Search...'}
              className="h-9 border-stone-200 bg-white pl-9 shadow-none"
            />
          </div>
        </div>
      </div>

      {activeTab === 'notebooks' ? (
        <PublicNotebooks searchQuery={searchQuery} rankingMode={rankingMode} />
      ) : (
        <PublicSources searchQuery={searchQuery} rankingMode={rankingMode} />
      )}
    </div>
  )
}

export function PublicClient() {
  const { t } = useTranslation()
  const router = useRouter()
  const { hasHydrated, isAuthenticated, token } = useAuthStore()

  useEffect(() => {
    if (!hasHydrated) return
    if (isAuthenticated && token) {
      router.replace('/discover')
    }
  }, [hasHydrated, isAuthenticated, token, router])

  if (!hasHydrated || (isAuthenticated && token)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-50 to-white">
      <GuestHeader primaryHref="/" primaryLabel="返回首页" showBackIcon />

      <main className="px-6 py-10 sm:py-12">
        <section className="mx-auto max-w-5xl">
          <div className="mb-8 text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white/70 px-3 py-1 text-sm text-stone-500">
              <Globe className="h-4 w-4 text-primary" />
              {t.public?.discover || 'Discover'}
            </div>
            <h1 className="text-3xl font-bold tracking-normal text-stone-900 sm:text-4xl">
              {t.public?.title || '公开内容'}
            </h1>
            <p className="mx-auto mt-3 max-w-2xl text-base leading-relaxed text-stone-500">
              {t.public?.description || 'Browse publicly shared notebooks and sources'}
            </p>
          </div>
          <PublicContentExplorer />
        </section>
      </main>
    </div>
  )
}
