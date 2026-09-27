'use client'
import { useQuery } from '@tanstack/react-query'
import apiClient from '@/lib/api/client'
import { useTranslation } from '@/lib/hooks/use-translation'
export function PreliminaryAccounts(){const {t}=useTranslation();const q=useQuery({queryKey:['preliminary-accounts'],queryFn:async()=>(await apiClient.get<{profiles:Record<string,{model:string;effort:string}>}>('/research/accounts/status')).data,staleTime:60000,retry:false});return <div className="rounded-xl border bg-muted/20 p-3 text-xs" role="status"><p className="mb-2 font-medium">{t('research.requestedModels')}</p>{q.data?<div className="space-y-1">{Object.entries(q.data.profiles).map(([id,p])=><p key={id}>{id.replace('-account','')} · {p.model} · {p.effort}</p>)}</div>:<p>{t(q.isError?'research.accountStatusError':'common.loading')}</p>}<p className="mt-2 text-muted-foreground">{t('research.modelSelectionHelp')}</p></div>}
