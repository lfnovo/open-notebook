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
import { formatPaperStatus, formatQuestionCount, paperDisplayStatus } from '@/lib/question-paper-labels'
import { DifficultyBreakdown } from '@/components/question-paper/DifficultyBreakdown'

export default function QuestionPaperPage() {
  const { t } = useTranslation()
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null)
  const [pendingPaperId, setPendingPaperId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const { data: papers = [], isLoading: papersLoading } = usePapers()
  const { mutate: generatePaper, isPending: isGenerating } = useGeneratePaper()
  const { mutate: deletePaper } = useDeletePaper()
  const { data: pendingStatus } = usePaperStatus(pendingPaperId)

  const selectedPaper = papers.find((paper) => paper.paper_id === selectedPaperId)
  const selectedReady = ['completed', 'needs_manual_review'].includes(selectedPaper?.status ?? '')
  const pendingReady = ['completed', 'needs_manual_review'].includes(pendingStatus?.status ?? '')
  const activeId = selectedPaperId && selectedReady
    ? selectedPaperId
    : pendingReady
      ? pendingPaperId
      : null
  const { data: paperResult, isLoading: resultLoading, refetch: refetchResult } = usePaperResult(
    activeId,
    !!activeId,
  )

  // Sync: when pending paper completes or fails, update states
  useEffect(() => {
    if (['completed', 'needs_manual_review'].includes(pendingStatus?.status ?? '') && pendingPaperId && !selectedPaperId) {
      setSelectedPaperId(pendingPaperId)
      setPendingPaperId(null)
      if (pendingStatus?.status === 'needs_manual_review') {
        toast.error(pendingStatus.error_message || t.questionPaper.auditFailedTitle)
      }
    } else if (pendingStatus?.status === 'failed' && pendingPaperId) {
      toast.error(pendingStatus.error_message || t.questionPaper.generationFailed)
      setPendingPaperId(null)
    }
  }, [pendingStatus?.status, pendingStatus?.error_message, pendingPaperId, selectedPaperId, t.questionPaper.generationFailed, t.questionPaper.auditFailedTitle])

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

  const isRunning = !!(pendingPaperId && pendingStatus?.status && !['completed', 'failed', 'needs_manual_review'].includes(pendingStatus.status))

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
              <TabsList className="flex w-full flex-nowrap justify-start h-auto">
                <TabsTrigger value="generate" className="flex-none whitespace-nowrap">
                  {t.questionPaper.generateTab}
                </TabsTrigger>
                <TabsTrigger value="papers" className="flex-none whitespace-nowrap">
                  {t.questionPaper.papersTab}
                </TabsTrigger>
                <TabsTrigger value="bank" className="flex-none whitespace-nowrap">
                  {t.questionPaper.bankTab}
                </TabsTrigger>
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
                      <PaperResultView result={paperResult} onRegenerated={() => refetchResult()} />
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
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 max-w-7xl">
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
                      <PaperResultView result={paperResult} onRegenerated={() => refetchResult()} />
                    ) : selectedPaper ? (
                      <div className="space-y-3">
                        <p className="text-sm font-medium">{formatPaperStatus(paperDisplayStatus(selectedPaper))}</p>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
                          <div>
                            <p className="text-muted-foreground">{t.questionPaper.requestedQuestions}</p>
                            <p className="font-medium">{formatQuestionCount(selectedPaper.requested_questions)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{t.questionPaper.generatedQuestions}</p>
                            <p className="font-medium">{formatQuestionCount(selectedPaper.generated_questions)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">{t.questionPaper.remainingQuestions}</p>
                            <p className="font-medium">{formatQuestionCount(selectedPaper.remaining_questions)}</p>
                          </div>
                        </div>
                        {selectedPaper.target_marks != null && (
                          <p className="text-xs text-muted-foreground">
                            {t.questionPaper.targetMarks}: {selectedPaper.target_marks}
                          </p>
                        )}
                        <DifficultyBreakdown
                          requested={selectedPaper.requested_difficulty}
                          generated={selectedPaper.generated_difficulty}
                          remaining={selectedPaper.remaining_difficulty}
                        />
                        {selectedPaper.error_message && (
                          <pre className="text-xs whitespace-pre-wrap break-words rounded-md border bg-muted/40 p-3">
                            {selectedPaper.error_message}
                          </pre>
                        )}
                      </div>
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
              <div className="max-w-7xl">
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
