'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FileText, FolderSearch, Copy, Download, RefreshCw, ChevronDown } from 'lucide-react'
import { toast } from 'sonner'
import apiClient from '@/lib/api/client'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useModules } from '@/lib/modules/hooks'

type FileHit={id:number;path:string;name:string;extension:string;size:number;status:string;error:string|null;snippet:string;copies:string[];sha256:string|null}
type Status={phase:string;files:number;counts:Record<string,number>;passages:number;vectors:number;visited:number;root:string;excluded:string[];unreadable_directories:number;semantic_error:string|null;max_content_bytes:number;enabled:boolean}
const base='/modules/local-files/service/'
export default function SearchPanel({query}:{query:string}) {
 const {t}=useTranslation(),cache=useQueryClient(),[selected,setSelected]=useState<FileHit|null>(null)
 const {data:modules}=useModules();const limit=Number(modules?.find(m=>m.id==='local-files')?.settings?.result_limit??20)
 const status=useQuery({queryKey:['local-files-status'],queryFn:async()=>(await apiClient.get<Status>(base+'status')).data,refetchInterval:10000,retry:false})
 const results=useQuery({queryKey:['local-files-search',query,limit],enabled:!!query,queryFn:async({signal})=>(await apiClient.post<{results:FileHit[];timing_ms:number;partial_index:boolean;query_terms:string[];warnings:string[]}>(base+'search',{query,limit},{signal})).data,retry:false})
 const refresh=useMutation({mutationFn:()=>apiClient.post(base+'refresh'),onSuccess:()=>cache.invalidateQueries({queryKey:['local-files-status']})})
 async function download(file:FileHit){try{const r=await apiClient.get(base+'files/'+file.id,{responseType:'blob'});const a=document.createElement('a');a.href=URL.createObjectURL(r.data);a.download=file.name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),5000)}catch{toast.error(t('files.unavailable'))}}
 const value=status.data
 return <section aria-label={t('files.title')} className="overflow-hidden rounded-2xl border bg-card">
  <div className="flex flex-wrap items-center justify-between gap-3 border-b bg-indigo-500/5 p-5"><div className="flex items-center gap-3"><FolderSearch className="size-5 text-indigo-500"/><div><h2 className="font-semibold">{t('files.title')}</h2><p className="mt-1 text-xs text-muted-foreground">{t('files.subtitle')}</p></div></div><Button size="sm" variant="outline" disabled={refresh.isPending} onClick={()=>refresh.mutate()}><RefreshCw className="mr-2 size-4"/>{t('files.refresh')}</Button></div>
  <div className="space-y-3 p-5">
   {status.isError||refresh.isError?<p role="alert" className="text-sm text-destructive">{t('files.unavailable')}</p>:value?<>
    <div className="flex flex-wrap items-center gap-2 text-xs"><Badge variant="outline">{t('files.phases.'+value.phase)}</Badge><span>{t('files.coverage',{files:value.files,indexed:value.counts.indexed??0,pending:value.counts.pending??0})}</span><span className="text-muted-foreground">{t('files.vectors',{count:value.vectors,total:value.passages})}</span></div>
    <details className="text-xs text-muted-foreground"><summary className="cursor-pointer">{t('files.scope')}</summary><div className="mt-3 space-y-2 break-words"><p>{value.root}</p><p>{t('files.exclude')}: {value.excluded.map(p=>p.split('/').pop()).join(', ')}</p><p>{t('files.coverageHelp',{mb:Math.round(value.max_content_bytes/1048576)})}</p><p>{t('files.metadata',{count:value.counts.metadata_only??0,large:value.counts.too_large??0,errors:value.counts.unreadable??0,dirs:value.unreadable_directories})}</p>{value.semantic_error&&<p>{t('files.semanticFallback')}</p>}</div></details>
   </>:<p className="text-sm text-muted-foreground">{t('common.loading')}</p>}
   {!query&&<p className="text-sm text-muted-foreground">{t('files.hint')}</p>}
   {query&&results.isFetching&&<p role="status" className="text-sm">{t('files.searching')}</p>}
   {results.isError&&<p role="alert" className="text-sm text-destructive">{t('files.unavailable')}</p>}
   {results.data&&<><div className="flex flex-wrap gap-2 text-xs text-muted-foreground"><span>{t('files.results',{count:results.data.results.length,ms:results.data.timing_ms})}</span>{results.data.partial_index&&<span>{t('files.partial')}</span>}</div>
    {results.data.warnings.map(w=><p key={w} role="status" className="text-xs text-muted-foreground">{t('files.warnings.'+w)}</p>)}
    <div className="space-y-2">{results.data.results.map(file=><button type="button" key={file.id} onClick={()=>setSelected(file)} className="group flex w-full gap-3 rounded-xl border bg-background/40 p-4 text-start transition-colors hover:border-indigo-500/40 hover:bg-indigo-500/5 focus-visible:outline-2 focus-visible:outline-primary"><FileText className="mt-0.5 size-5 shrink-0 text-indigo-400"/><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="break-all text-sm font-medium">{file.name}</span><Badge variant="outline" className="text-[10px] uppercase">{file.extension||t('files.file')}</Badge></div><p className="mt-1 truncate text-xs text-muted-foreground">{file.path}</p>{file.snippet&&<p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{file.snippet}</p>}{file.copies.length>0&&<p className="mt-2 text-xs text-indigo-400">{t('files.copies',{count:file.copies.length})}</p>}</div><ChevronDown className="size-4 shrink-0 text-muted-foreground"/></button>)}</div>
   </>}
  </div>
  <Dialog open={!!selected} onOpenChange={open=>!open&&setSelected(null)}><DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto"><DialogHeader><DialogTitle className="break-all pr-6">{selected?.name}</DialogTitle></DialogHeader>{selected&&<div className="space-y-4"><p className="break-all text-xs text-muted-foreground">{selected.path}</p><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={()=>navigator.clipboard.writeText(selected.path).then(()=>toast.success(t('files.copied'))).catch(()=>toast.error(t('files.unavailable')))}><Copy className="mr-2 size-4"/>{t('files.copy')}</Button><Button size="sm" onClick={()=>download(selected)}><Download className="mr-2 size-4"/>{t('files.download')}</Button><Badge variant="outline">{t('files.states.'+selected.status)}</Badge></div>{selected.error&&<p className="text-sm">{selected.error}</p>}{selected.snippet?<pre className="whitespace-pre-wrap break-words rounded-xl bg-muted/40 p-4 font-sans text-sm leading-7">{selected.snippet}</pre>:<p className="text-sm text-muted-foreground">{t('files.noPreview')}</p>}{selected.copies.map(p=><p key={p} className="break-all text-xs">{p}</p>)}</div>}</DialogContent></Dialog>
 </section>
}
