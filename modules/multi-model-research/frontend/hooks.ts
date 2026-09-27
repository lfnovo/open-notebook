import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { isAxiosError } from 'axios'
import { researchApi, ResearchCreate, ResearchRun, ControlSnapshot } from '@/modules/multi-model-research/api'
import { QUERY_KEYS as CORE_KEYS } from '@/lib/api/query-client'
const QUERY_KEYS = { ...CORE_KEYS, research: ['module', 'multi-model-research'] as const, researchRun: (id:string)=>['module','multi-model-research',id] as const, researchPacket: (id:string,stage:string)=>['module','multi-model-research','packet',id,stage] as const }
import { useTranslation } from '@/lib/hooks/use-translation'
export function useResearchRuns() {
  return useQuery({queryKey:QUERY_KEYS.research,queryFn:researchApi.list,retry:false,refetchInterval:5000})
}
export function useResearchRun(id:string|null) {
  return useQuery({queryKey:QUERY_KEYS.researchRun(id||''),queryFn:()=>researchApi.get(id!),enabled:!!id,retry:false,refetchInterval:3000})
}
export function useContextPlan(id:string,enabled:boolean) {
  return useQuery({queryKey:[...QUERY_KEYS.researchRun(id),'context-plan'],queryFn:()=>researchApi.contextPlan(id),enabled,retry:false,refetchInterval:5000})
}
export function useResearchPacket(id:string,stage:string,enabled:boolean) {
  return useQuery({queryKey:QUERY_KEYS.researchPacket(id,stage),queryFn:()=>researchApi.packet(id,stage),enabled,retry:false,staleTime:Infinity})
}
export function useBrowserStatus(enabled:boolean,deep=false) {
  // Opening the browser is slow and user visible, so this is never polled on a timer.
  return useQuery({queryKey:[...QUERY_KEYS.research,'browser',deep],queryFn:()=>researchApi.browserStatus(deep),enabled,retry:false,staleTime:30000,refetchOnWindowFocus:false})
}
export function useBrowserLogin() {
  const client=useQueryClient();const {t}=useTranslation()
  return useMutation({mutationFn:researchApi.browserLogin,retry:false,
    onSuccess:result=>{toast.success(result.message);client.invalidateQueries({queryKey:[...QUERY_KEYS.research,'browser']})},
    onError:(err:unknown)=>toast.error(isAxiosError(err)&&typeof err.response?.data?.detail==='string'?err.response.data.detail:t('research.error'))})
}
export function useResearchActions() {
  const client=useQueryClient();const {t}=useTranslation()
  const success=(run:ResearchRun)=>{client.setQueryData(QUERY_KEYS.researchRun(run.id),run);client.invalidateQueries({queryKey:QUERY_KEYS.research});client.invalidateQueries({queryKey:QUERY_KEYS.notebooks})}
  const error=(err:unknown)=>toast.error(isAxiosError(err)&&typeof err.response?.data?.detail==='string'?err.response.data.detail:t('research.error'))
  const create=useMutation({mutationFn:({body,key}:{body:ResearchCreate;key:string})=>researchApi.create(body,key),retry:false,onSuccess:run=>{success(run);toast.success(t('research.created'))},onError:error})
  const upload=useMutation({mutationFn:({id,stage,data}:{id:string;stage:string;data:FormData})=>researchApi.import(id,stage,data),retry:false,onSuccess:run=>{success(run);toast.success(t('research.imported'))},onError:error})
  const action=useMutation({mutationFn:({id,action,expectedState}:{id:string;expectedState?:ControlSnapshot;action:'pause'|'resume'|'sync'|'automate'|'stop'|'cancel'|'restore'})=>researchApi.action(id,action,expectedState),retry:false,onSuccess:success,onError:error})
  const retry=useMutation({mutationFn:({id,stage,expectedState}:{id:string;stage:string;expectedState?:ControlSnapshot})=>researchApi.retryStage(id,stage,expectedState),retry:false,onSuccess:run=>{success(run);toast.success(t('research.retryStarted'))},onError:error})
  const stageAction=useMutation({mutationFn:({id,stage,action,expectedState}:{id:string;stage:string;action:'pause'|'stop'|'cancel'|'resume'|'restore'|'retry'|'skip';expectedState:ControlSnapshot})=>researchApi.stageAction(id,stage,action,expectedState),retry:false,onSuccess:success,onError:error})
  return {create,upload,action,retry,stageAction,error}
}
