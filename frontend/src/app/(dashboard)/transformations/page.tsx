'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DefaultPromptEditor } from './components/DefaultPromptEditor'
import { TransformationsList } from './components/TransformationsList'
import { TransformationPlayground } from './components/TransformationPlayground'
import { useTransformations } from '@/lib/hooks/use-transformations'
import { Transformation } from '@/lib/types/transformations'
import { Wand2, Play, RefreshCw } from 'lucide-react'

export default function TransformationsPage() {
  const [activeTab, setActiveTab] = useState('transformations')
  const [selectedTransformation, setSelectedTransformation] = useState<Transformation | undefined>()
  const { data: transformations, isLoading, refetch } = useTransformations()

  const handlePlayground = (transformation: Transformation) => {
    setSelectedTransformation(transformation)
    setActiveTab('playground')
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold">Transformations</h1>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="max-w-5xl">
          <p className="text-muted-foreground">
            Transformations are prompts that will be used by the LLM to process a source and extract insights, summaries, etc.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Choose a workspace</p>
            <TabsList aria-label="Transformation views" className="w-full max-w-xl">
              <TabsTrigger value="transformations" className="flex items-center gap-2">
                <Wand2 className="h-4 w-4" />
                Transformations
              </TabsTrigger>
              <TabsTrigger value="playground" className="flex items-center gap-2">
                <Play className="h-4 w-4" />
                Playground
              </TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="transformations" className="space-y-6">
            <DefaultPromptEditor />
            <TransformationsList 
              transformations={transformations} 
              isLoading={isLoading}
              onPlayground={handlePlayground}
            />
          </TabsContent>
          
          <TabsContent value="playground">
            <TransformationPlayground 
              transformations={transformations}
              selectedTransformation={selectedTransformation}
            />
          </TabsContent>
        </Tabs>
        </div>
      </div>
    </AppShell>
  )
}
