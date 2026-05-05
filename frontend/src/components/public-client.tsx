'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useTranslation } from '@/lib/hooks/use-translation'
import { PublicNotebooks } from '@/components/public/PublicNotebooks'
import { PublicSources } from '@/components/public/PublicSources'
import { Globe, Search, Sparkles } from 'lucide-react'
import { Input } from '@/components/ui/input'

export function PublicContentExplorer({
  compact = false,
  className = '',
}: {
  compact?: boolean
  className?: string
}) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<'notebooks' | 'sources'>('notebooks')

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1 rounded-lg bg-white/70 p-1 ring-1 ring-stone-200/70">
          <button
            onClick={() => setActiveTab('notebooks')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'notebooks'
                ? 'bg-white shadow-sm text-stone-900'
                : 'text-stone-500 hover:text-stone-900'
            }`}
          >
            {t.public?.notebooks || 'Notebooks'}
          </button>
          <button
            onClick={() => setActiveTab('sources')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'sources'
                ? 'bg-white shadow-sm text-stone-900'
                : 'text-stone-500 hover:text-stone-900'
            }`}
          >
            {t.public?.sources || 'Sources'}
          </button>
        </div>
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-stone-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.public?.searchPlaceholder || 'Search...'}
            className="border-stone-200 bg-white/80 pl-9"
          />
        </div>
      </div>

      {activeTab === 'notebooks' ? (
        <PublicNotebooks searchQuery={searchQuery} compact={compact} />
      ) : (
        <PublicSources searchQuery={searchQuery} compact={compact} />
      )}
    </div>
  )
}

export function PublicClient() {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-50 to-white">
      <header className="sticky top-0 z-50 border-b border-stone-200/60 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="text-base font-semibold text-stone-800">Lumina</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm text-stone-600 transition-colors hover:text-stone-900">
              登录
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              注册
            </Link>
          </div>
        </div>
      </header>

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
