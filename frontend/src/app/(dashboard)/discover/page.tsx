'use client'

import { PublicContentExplorer } from '@/components/public-client'

export default function DiscoverPage() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-5xl flex-col p-6">
        <PublicContentExplorer />
      </div>
    </div>
  )
}
