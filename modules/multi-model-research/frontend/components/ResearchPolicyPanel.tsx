'use client'

import { ShieldCheck, AlertTriangle } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { ResearchPolicy } from '@/modules/multi-model-research/api'

export function ResearchPolicyPanel({policy}:{policy?:ResearchPolicy}) {
  const {t}=useTranslation()
  if(!policy)return null
  const review=policy.findings.some(f=>f.severity!=='info')
  return <details className="mb-5 rounded-xl border bg-muted/20 p-4" open={policy.blocked}>
    <summary className="cursor-pointer list-none rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary">
      <span className="flex flex-wrap items-center gap-2 text-sm font-medium">
        {review?<AlertTriangle aria-hidden className="size-4 shrink-0 text-warn"/>:<ShieldCheck aria-hidden className="size-4 shrink-0 text-muted-foreground"/>}
        {t('research.policyTitle')}
        <span className="text-xs font-normal text-muted-foreground">{t('research.policyChecked',{count:policy.rules_evaluated})}</span>
      </span>
      <span className="mt-1 block text-xs text-muted-foreground">{t(policy.blocked?'research.policyBlocked':review?'research.policyReview':'research.policyInfo')} · {policy.findings.length}</span>
    </summary>
    <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{t('research.policyNote')}</p>
    <ul className="mt-3 space-y-3">{policy.findings.map((finding,i)=><li key={`${finding.id}-${i}`} className="rounded-lg border bg-background/50 p-3">
      <span className="text-xs font-medium text-muted-foreground">{finding.id}</span>
      <p className="mt-1 text-sm leading-relaxed">{finding.message}</p>
      <details className="mt-2 text-xs text-muted-foreground"><summary className="cursor-pointer">{t('research.policyEvidence')}</summary><pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all">{JSON.stringify(finding.evidence,null,2)}</pre></details>
    </li>)}</ul>
  </details>
}
