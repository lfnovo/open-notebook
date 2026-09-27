import apiClient from '@/lib/api/client'
export type ResearchReport = { content:string; researched_at:string|null; sha256:string; citations:string[]; provenance:string; origin_url:string; evidence:{name:string;content:string}[]; original_files:{name:string;bytes:number}[] }
export type BrowserProgress = { phase:string; message:string; url?:string|null }
export type ResearchPolicy = {version:string;event:string;rules_evaluated:number;blocked:boolean;block_status:string|null;findings:{id:string;severity:string;action:string;message:string;evidence:Record<string,unknown>}[];checked_at?:string;factual_verification:false}
export type ResearchStage = {preparation?:PreparationPlan|null; control_state?:'stopping'|'stopped'|'paused'|'cancelled'|'stop_failed'|null; control_error?:string|null;  account_profile?:'preliminary_research'|'preliminary_merge'|'research_review'; depends_on?:string[]; policy?:ResearchPolicy; id:string; provider:string; round:number; mode:'import'|'account'|'browser'; status:string; attempts:number; report:ResearchReport|null; error:string|null; usage:{total_tokens?:number;prompt_tokens?:number;completion_tokens?:number;execution?:{requested_model?:string;requested_effort?:string;reported_models?:string[]}}|null; note_id:string|null; browser_progress:BrowserProgress|null; retry_index:number; next_retry_at:string|null }
export type ExecutionMode = 'imports'|'browser'
export type ResearchRun = { id:string; question:string; scope:string; as_of:string; language:string; auto_synthesize:boolean; execution_mode:ExecutionMode; preliminary?:boolean;account_review?:boolean; control_state?:'stopping'|'stopped'|'cancelled'|'stop_failed'|null; control_error?:string|null; paused:boolean; status:string; stages:ResearchStage[]; created_at:string; updated_at:string; notebook_id:string|null; sync_error:string|null }
export type RunControlSnapshot = {status:string;paused:boolean;control_state:string|null;stages:(string|number|null)[][]}
export type StageControlSnapshot = {scope:'stage';run_paused:boolean;run_control_state:string|null;stage:(string|number|null)[]}
export type ControlSnapshot = RunControlSnapshot | StageControlSnapshot
export function controlSnapshot(run: ResearchRun, stageId?:string): ControlSnapshot { if(stageId) { const stage=run.stages.find(s=>s.id===stageId)!;return {scope:'stage',run_paused:run.paused,run_control_state:run.control_state||null,stage:[stage.id,stage.status,stage.attempts,stage.control_state||null]} }  return {status:run.status,paused:run.paused,control_state:run.control_state || null,stages:run.stages.map(s=>[s.id,s.status,s.attempts,s.control_state||null])} }
export type ResearchSummary = Pick<ResearchRun,'id'|'question'|'scope'|'created_at'|'updated_at'|'status'|'notebook_id'> & {completed:number;total?:number}
export type ResearchCreate = {preliminary?:boolean;account_review?:boolean;question:string;scope:string;as_of:string;language:string;auto_synthesize:boolean;execution_mode:ExecutionMode}
export type BrowserConnection = {provider:string;status:string;message:string}
export type BrowserStatus = {checked_at:string;deep:boolean;connections:BrowserConnection[]}
export type InputBudget = {raw_tokens:number;transport_raw_tokens:number;counted_tokens:number;automatic_input_limit:number;effective_raw_limit:number;remaining_input_tokens:number;utilization:number;fits:boolean;tokenizer:string;token_margin:{multiplier:number;overhead_tokens:number;basis:string;calibration_fingerprint?:string|null}}
export type ContextPlanRow = Partial<InputBudget> & {stage_id:string;provider:string;round:number;projection?:boolean;known_raw_tokens?:number;missing_reports?:number;reserved_report_tokens?:number;warning:boolean;error?:string}
export type PreparationPlan = {version:string;parts:number;source_bytes:number;source_sha256:string;coverage_verified:boolean;semantic_lossless:false;status:string;minimum_calls:number;completed_calls?:number;current?:string}
export type CompactionAudit = {version?:string;referenced_blocks?:number;preservation_verified?:boolean;before_tokens:number;after_tokens:number;saved_tokens:number;removed_sentences:number;candidates:number;round_raw_limit:number;fits:boolean;rolled_back?:boolean;marker:string;by_reason:Record<string,number>;by_stage:Record<string,number>}
export type ResearchPacket = Partial<InputBudget> & {prompt:string;sha256:string;estimated_tokens:number;automatic_input_limit:number;report_count:number;policy?:ResearchPolicy;evidence_packet?:{sha256:string;bytes:number;format:string};compaction?:CompactionAudit|null;preparation?:PreparationPlan|null}
export const researchApi = {
  list:async () => (await apiClient.get<ResearchSummary[]>('/research/runs')).data,
  get:async (id:string) => (await apiClient.get<ResearchRun>(`/research/runs/${id}`)).data,
  contextPlan:async (id:string) => (await apiClient.get<{stages:ContextPlanRow[]}>(`/research/runs/${id}/context-plan`)).data,
  create:async (body:ResearchCreate,key:string) => (await apiClient.post<ResearchRun>('/research/runs',body,{headers:{'Idempotency-Key':key}})).data,
  packet:async (id:string,stage:string) => (await apiClient.get<ResearchPacket>(`/research/runs/${id}/stages/${stage}/packet`)).data,
  evidence:async (id:string,stage:string) => (await apiClient.get<Blob>(`/research/runs/${id}/stages/${stage}/evidence`,{responseType:'blob'})).data,
  import:async (id:string,stage:string,body:FormData) => (await apiClient.post<ResearchRun>(`/research/runs/${id}/stages/${stage}/import`,body)).data,
  action:async (id:string,action:'pause'|'resume'|'sync'|'automate'|'stop'|'cancel'|'restore',expectedState?:ControlSnapshot) => (await apiClient.post<ResearchRun>(`/research/runs/${id}/${action}`,{expected_state:expectedState})).data,
  stageAction:async (id:string,stage:string,action:'pause'|'stop'|'cancel'|'resume'|'restore'|'retry'|'skip',expectedState:ControlSnapshot) => (await apiClient.post<ResearchRun>(`/research/runs/${id}/stages/${stage}/actions/${action}`,{expected_state:expectedState})).data,
  retryStage:async (id:string,stage:string,expectedState?:ControlSnapshot) => (await apiClient.post<ResearchRun>(`/research/runs/${id}/stages/${stage}/retry`,{expected_state:expectedState})).data,
  export:async (id:string) => (await apiClient.get<Blob>(`/research/runs/${id}/export`,{responseType:'blob'})).data,
  browserStatus:async (deep:boolean) => (await apiClient.get<BrowserStatus>('/research/browser/status',{params:{deep}})).data,
  browserLogin:async () => (await apiClient.post<{pid:number;already_open:boolean;message:string}>('/research/browser/login')).data,
}
export function downloadResearchFile(content:Blob|string,name:string) {
  const url=URL.createObjectURL(typeof content==='string'?new Blob([content],{type:'text/markdown;charset=utf-8'}):content)
  const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
