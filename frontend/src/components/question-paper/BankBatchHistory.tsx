'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { Download, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { questionPaperApi } from '@/lib/api/question-paper'
import {
  useBankBatches,
  useQuestionBooks,
} from '@/lib/hooks/use-question-paper'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  apiErrorDetail,
  bankBatchCanExport,
  bankBatchCanView,
  bankBatchQuestionIds,
  bankBatchReviewPath,
  bankBatchStopReason,
  formatBankBatchStopReason,
} from '@/lib/question-paper-bank-batch'
import {
  formatChapterLabel,
  formatCreatedDate,
  formatDifficulty,
  formatPaperStatus,
  formatQuestionProgress,
} from '@/lib/question-paper-labels'
import type { BankBatchSummary } from '@/lib/types/question-paper'

function statusClass(status: string): string {
  if (status === 'completed') return 'text-green-700'
  if (status === 'partial' || status === 'completed_partial') return 'text-amber-700'
  if (status === 'failed') return 'text-destructive'
  if (status === 'running' || status === 'pending' || status === 'submitted') return 'text-blue-700'
  return 'text-muted-foreground'
}

async function downloadXlsx(questionIds: string[], batchId: string) {
  const blob = await questionPaperApi.exportBankXlsx(questionIds)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `question_bank_${batchId.replace(/[:/\\]/g, '_')}.xlsx`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function BankBatchHistory() {
  const { t } = useTranslation()
  const { data: batches = [], isLoading } = useBankBatches()
  const [exportingId, setExportingId] = useState<string | null>(null)

  const bookIds = useMemo(
    () => batches.map((batch) => String(batch.book_id || '')).filter(Boolean),
    [batches],
  )
  const bookTitles = useQuestionBooks(bookIds)

  const exportBatch = async (batch: BankBatchSummary) => {
    if (exportingId) return
    setExportingId(batch.batch_id)
    try {
      let ids = bankBatchQuestionIds(batch)
      if (ids.length === 0) {
        const fetched = await questionPaperApi.getBankBatchResult(batch.batch_id)
        ids = bankBatchQuestionIds(batch, fetched)
      }
      if (ids.length === 0) {
        toast.error(t.questionPaper.bankDownloadEmpty)
        return
      }
      await downloadXlsx(ids, batch.batch_id)
    } catch (err: unknown) {
      toast.error(apiErrorDetail(err, t.questionPaper.bankDownloadFailed))
    } finally {
      setExportingId(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.questionPaper.bankHistoryTitle}</CardTitle>
        <CardDescription>{t.questionPaper.bankHistoryDesc}</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : batches.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-10">
            {t.questionPaper.bankHistoryEmpty}
          </p>
        ) : (
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left">
                <tr className="border-b">
                  <th className="px-3 py-2 font-medium">{t.questionPaper.grade}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.storedBook}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.chapter}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.difficulty}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.bankRequested}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.bankAccepted}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.status}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.historyColCreated}</th>
                  <th className="px-3 py-2 font-medium">{t.questionPaper.bankHistoryColBatchId}</th>
                  <th className="px-3 py-2 font-medium text-right">{t.questionPaper.historyColActions}</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.batch_id} className="border-b last:border-0">
                    <td className="px-3 py-2 whitespace-nowrap">{batch.grade || '—'}</td>
                    <td
                      className="px-3 py-2 whitespace-nowrap max-w-[12rem] truncate"
                      title={bookTitles[batch.book_id || ''] || batch.book_id || ''}
                    >
                      {batch.book_id ? (bookTitles[batch.book_id] || batch.book_id) : '—'}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {formatChapterLabel(batch.chapter) || '—'}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">{formatDifficulty(batch.difficulty)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{batch.requested}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {formatQuestionProgress(batch.accepted, batch.requested)}
                    </td>
                    <td className={`px-3 py-2 ${statusClass(batch.status)}`}>
                      <p className="font-medium whitespace-nowrap">
                        {batch.status === 'completed_partial'
                          ? t.questionPaper.bankStatusPartial
                          : formatPaperStatus(batch.status)}
                      </p>
                      {batch.status === 'completed_partial' && formatBankBatchStopReason(bankBatchStopReason(batch)) ? (
                        <p className="text-xs font-normal text-muted-foreground max-w-[12rem] truncate" title={formatBankBatchStopReason(bankBatchStopReason(batch))}>
                          {formatBankBatchStopReason(bankBatchStopReason(batch))}
                        </p>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-muted-foreground">
                      {formatCreatedDate(batch.created)}
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground max-w-[10rem] truncate" title={batch.batch_id}>
                      {batch.batch_id}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-2">
                        {bankBatchCanView(batch.status) ? (
                          <Button variant="outline" size="sm" asChild>
                            <Link href={bankBatchReviewPath(batch.batch_id)}>
                              {t.questionPaper.bankHistoryViewQuestions}
                            </Link>
                          </Button>
                        ) : (
                          <Button variant="outline" size="sm" disabled>
                            {t.questionPaper.bankHistoryViewQuestions}
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={!bankBatchCanExport(batch.status, batch) || exportingId === batch.batch_id}
                          onClick={() => exportBatch(batch)}
                        >
                          {exportingId === batch.batch_id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Download className="h-3.5 w-3.5" />
                          )}
                          {t.questionPaper.bankDownloadExcel}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
