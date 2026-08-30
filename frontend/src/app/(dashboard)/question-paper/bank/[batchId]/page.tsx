'use client'

import { useParams } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { BankBatchReview } from '@/components/question-paper/BankBatchReview'

export default function BankBatchReviewPage() {
  const params = useParams()
  const batchId = params?.batchId ? decodeURIComponent(String(params.batchId)) : ''

  return (
    <AppShell>
      <BankBatchReview batchId={batchId} />
    </AppShell>
  )
}
