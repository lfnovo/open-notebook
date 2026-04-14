'use client'

import { useState, useEffect } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { AppShell } from '@/components/layout/AppShell'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { GenerateForm } from '@/components/question-paper/GenerateForm'
import { PapersList } from '@/components/question-paper/PapersList'
import { PaperResultView } from '@/components/question-paper/PaperResult'
import { BankView } from '@/components/question-paper/BankView'
import {
  useGeneratePaper,
  usePapers,
  usePaperResult,
  usePaperStatus,
  useDeletePaper,
} from '@/lib/hooks/use-question-paper'
import type { GeneratePaperRequest } from '@/lib/types/question-paper'

export default function QuestionPaperPage() {
  const { t } = useTranslation()
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null)
  const [pendingPaperId, setPendingPaperId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const { data: papers = [], isLoading: papersLoading } = usePapers()
  const { mutate: generatePaper, isPending: isGenerating } = useGeneratePaper()
  const { mutate: deletePaper } = useDeletePaper()

  // Poll status for in-progress generation
  const { data: pendingStatus } = usePaperStatus(pendingPaperId)

  // Fetch result when a paper is selected or pending paper completes
  const activeId = selectedPaperId ?? (pendingStatus?.status === 'completed' ? pendingPaperId : null)
  const { data: paperResult, isLoading: resultLoading } = usePaperResult(
    activeId,
    !!activeId,
  )

  // Sync: when pending paper completes or fails, update states
  useEffect(() => {
    if (pendingStatus?.status === 'completed' && pendingPaperId && !selectedPaperId) {
      setSelectedPaperId(pendingPaperId)
      setPendingPaperId(null)
    } else if (pendingStatus?.status === 'failed' && pendingPaperId) {
      toast.error(pendingStatus.error_message || t.questionPaper.generationFailed)
      setPendingPaperId(null)
    }
  }, [pendingStatus?.status, pendingPaperId, selectedPaperId, t.questionPaper.generationFailed])

  const handleGenerate = (request: GeneratePaperRequest) => {
    generatePaper(request, {
      onSuccess: (response) => {
        toast.success(t.questionPaper.generationStarted)
        setPendingPaperId(response.paper_id)
        setSelectedPaperId(null)
      },
      onError: () => {
        toast.error(t.questionPaper.generationFailed)
      },
    })
  }

  const handleDelete = (paperId: string) => {
    setDeletingId(paperId)
    if (selectedPaperId === paperId) setSelectedPaperId(null)
    deletePaper(paperId, { onSettled: () => setDeletingId(null) })
  }

  const isRunning = !!(pendingPaperId && pendingStatus?.status && !['completed', 'failed'].includes(pendingStatus.status))

  return (
    <AppShell>
      <div className="h-full flex flex-col">
        <div className="p-6 pb-4 border-b">
          <h1 className="text-2xl font-bold">{t.questionPaper.title}</h1>
          <p className="text-muted-foreground text-sm mt-1">{t.questionPaper.subtitle}</p>
        </div>

        <div className="flex-1 overflow-hidden">
          <Tabs defaultValue="generate" className="h-full flex flex-col">
            <div className="px-6 pt-4">
              <TabsList>
                <TabsTrigger value="generate">{t.questionPaper.generateTab}</TabsTrigger>
                <TabsTrigger value="papers">{t.questionPaper.papersTab}</TabsTrigger>
                <TabsTrigger value="bank">{t.questionPaper.bankTab}</TabsTrigger>
              </TabsList>
            </div>

            {/* Generate Tab */}
            <TabsContent value="generate" className="flex-1 overflow-auto px-6 pb-6 mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-6xl">
                {/* Form */}
                <Card>
                  <CardHeader>
                    <CardTitle>{t.questionPaper.configureTitle}</CardTitle>
                    <CardDescription>{t.questionPaper.configureDesc}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <GenerateForm onSubmit={handleGenerate} isLoading={isGenerating || isRunning} />
                  </CardContent>
                </Card>

                {/* Result / Status */}
                <Card>
                  <CardHeader>
                    <CardTitle>{t.questionPaper.resultTitle}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {isRunning && (
                      <div className="flex flex-col items-center justify-center py-12 gap-3">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        <p className="text-sm text-muted-foreground">{t.questionPaper.generating}</p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {t.questionPaper.status}: {pendingStatus?.status}
                        </p>
                      </div>
                    )}
                    {resultLoading && !isRunning && (
                      <div className="flex justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      </div>
                    )}
                    {paperResult && !isRunning && (
                      <PaperResultView result={paperResult} />
                    )}
                    {!isRunning && !resultLoading && !paperResult && (
                      <p className="text-sm text-muted-foreground text-center py-12">
                        {t.questionPaper.resultEmpty}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Papers History Tab */}
            <TabsContent value="papers" className="flex-1 overflow-auto px-6 pb-6 mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-6xl">
                <Card>
                  <CardHeader>
                    <CardTitle>{t.questionPaper.papersTitle}</CardTitle>
                    <CardDescription>{t.questionPaper.papersDesc}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {papersLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                      </div>
                    ) : (
                      <PapersList
                        papers={papers}
                        onSelect={(id) => setSelectedPaperId(id)}
                        onDelete={handleDelete}
                        selectedId={selectedPaperId}
                        deletingId={deletingId}
                      />
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>{t.questionPaper.selectedPaperTitle}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {resultLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      </div>
                    ) : paperResult ? (
                      <PaperResultView result={paperResult} />
                    ) : (
                      <p className="text-sm text-muted-foreground text-center py-8">
                        {t.questionPaper.selectPaperHint}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Bank Tab */}
            <TabsContent value="bank" className="flex-1 overflow-auto px-6 pb-6 mt-4">
              <div className="max-w-3xl">
                <Card>
                  <CardHeader>
                    <CardTitle>{t.questionPaper.bankTitle}</CardTitle>
                    <CardDescription>{t.questionPaper.bankDesc}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <BankView />
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </AppShell>
  )
}
