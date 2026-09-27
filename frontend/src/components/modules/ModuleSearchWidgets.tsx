'use client'
import { moduleEntries } from '@/lib/modules/generated'
import { useModules } from '@/lib/modules/hooks'
/** Search v1 port: query only. Modules own result types, state and transport. */
export function ModuleSearchWidgets({query}:{query:string}) {
 const {data}=useModules()
 return <>{data?.filter(m=>m.active).map(m=>{const Widget=moduleEntries[m.id]?.SearchWidget;return Widget?<Widget key={m.id} query={query}/>:null})}</>
}
