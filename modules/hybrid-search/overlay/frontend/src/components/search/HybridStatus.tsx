'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Layers, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react'
import apiClient from '@/lib/api/client'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { RetrievalDiagnostics } from '@/lib/types/search'

type IndexStatus = {status:string;processed:number;total:number;error:string|null;passages:number;index?:{model:string;synced_at:string;documents:number}|null}
export function HybridStatus() {
  const {t}=useTranslation();const client=useQueryClient()
  const status=useQuery({queryKey:['hybrid-index'],queryFn:async()=>(await apiClient.get<IndexStatus>('/search/index/status')).data,retry:false,refetchInterval:15000})
  const refresh=useMutation({mutationFn:async()=>(await apiClient.post('/search/index/refresh')).data,onSuccess:()=>client.invalidateQueries({queryKey:['hybrid-index']}),retry:false})
  const value=status.data;const busy=value?.status==='indexing'||refresh.isPending
  return <section className="mb-6 rounded-2xl border bg-card p-4 sm:p-5" aria-label={t('modules.hybrid.indexTitle')}>
    <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><div className="rounded-xl bg-primary/10 p-2 text-primary"><Layers className="size-5"/></div><div><h2 className="text-sm font-semibold">{t('modules.hybrid.indexTitle')}</h2><p className="mt-1 text-xs text-muted-foreground">{t('modules.hybrid.description')}</p></div></div>
      <Button size="sm" variant="outline" disabled={busy} onClick={()=>refresh.mutate()}><RefreshCw className={`mr-2 size-4 ${busy?'animate-spin':''}`}/>{t('modules.hybrid.refresh')}</Button></div>
    <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground" role="status">
      {status.isError||refresh.isError?<span className="flex items-center gap-1 text-warn"><AlertCircle className="size-3"/>{t('modules.hybrid.statusError')}</span>:value?<><Badge variant="outline">{t('modules.hybrid.states.'+value.status)}</Badge><span>{t('modules.hybrid.coverage',{documents:value.index?.documents??0,passages:value.passages})}</span>{busy&&<span>{value.processed} / {value.total}</span>}{value.index&&<span>{value.index.model}</span>}{value.error&&<span className="text-warn">{value.error}</span>}</>:<span>{t('modules.hybrid.loading')}</span>}
    </div>
  </section>
}
export function RetrievalFeedback({value}:{value:RetrievalDiagnostics}) {
 const {t}=useTranslation()
 return <div className="my-3 rounded-xl border bg-muted/20 px-4 py-3 text-xs" role="status">
  <div className="flex flex-wrap items-center gap-2"><CheckCircle2 className="size-3 text-primary"/><span>{t('modules.hybrid.timing',{ms:value.timings.total_ms})}</span><span>·</span><span>{t('modules.hybrid.candidates',{count:value.candidates})}</span><Badge variant="outline">{t(value.reranked?'modules.hybrid.reranked':'modules.hybrid.fused')}</Badge></div>
  {value.warnings.map((w,i)=><p className="mt-2 flex items-start gap-2 text-warn" key={i}><AlertCircle className="mt-0.5 size-3 shrink-0"/>{t('modules.hybrid.warnings.'+w)}</p>)}
 </div>
}
