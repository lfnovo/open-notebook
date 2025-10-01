'use client'

import { useState } from 'react'

import { AppShell } from '@/components/layout/AppShell'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EpisodesTab } from '@/components/podcasts/EpisodesTab'
import { TemplatesTab } from '@/components/podcasts/TemplatesTab'

export default function PodcastsPage() {
  const [activeTab, setActiveTab] = useState<'episodes' | 'templates'>('episodes')

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-6 space-y-6">
          <header className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Podcasts</h1>
            <p className="text-muted-foreground">
              Keep track of generated episodes and manage reusable templates.
            </p>
          </header>

          <Tabs
            value={activeTab}
            onValueChange={(value) => setActiveTab(value as 'episodes' | 'templates')}
            className="space-y-6"
          >
            <TabsList className="w-fit">
              <TabsTrigger value="episodes">Episodes</TabsTrigger>
              <TabsTrigger value="templates">Templates</TabsTrigger>
            </TabsList>

            <TabsContent value="episodes">
              <EpisodesTab />
            </TabsContent>

            <TabsContent value="templates">
              <TemplatesTab />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </AppShell>
  )
}
