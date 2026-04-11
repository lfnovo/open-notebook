'use client'

import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  InfographicResponse,
  InfographicColumn,
} from '@/lib/api/infographic'
import {
  Info, Calendar, Target, Briefcase, AlertTriangle, Network,
  User, Building, Shield, Activity, BookOpen, BarChart2, MapPin,
  Scale, Lightbulb, FileText, Users, Zap, Sparkles,
  Search, Eye, ShieldCheck,
  Fingerprint, Layers, GraduationCap,
  Share2, Box, Trophy, Landmark, Lock, Globe,
  ShieldAlert, Database, History, TrendingUp, Cpu
} from 'lucide-react'

interface InfographicInsightViewerProps {
  content: string
}

// ── detector ──────────────────────────────────────────────────────────────────

export function isInfographicInsight(insightType: string): boolean {
  return insightType.toLowerCase().includes('infographic')
}

// ── helper: cleaning ─────────────────────────────────────────────────────────

function stripMarkdownSymbols(text: string): string {
  if (!text) return ''
  return text
    .replace(/\*{1,3}/g, '') // remove *, **, ***
    .replace(/_{1,3}/g, '')  // remove _, __, ___
    .replace(/#+\s/g, '')    // remove # headers
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // remove links but keep text
    .replace(/^[•\-\*]\s+/, '') // remove bullet points
    .replace(/\+\+/g, '')    // remove logical artifacts
    .trim()
}

function parseDataRow(line: string): [string, string] | null {
  const trimmed = line.trim().replace(/^[•\-\*\+]{1,2}\s*/, '')
  const colonIndex = trimmed.indexOf(':')
  
  if (colonIndex > 0 && colonIndex < trimmed.length - 1) {
    const rawLabel = trimmed.substring(0, colonIndex)
    const rawValue = trimmed.substring(colonIndex + 1)
    
    const label = stripMarkdownSymbols(rawLabel)
    const value = stripMarkdownSymbols(rawValue)
    
    if (label && value && label.length < 40) return [label, value]
  }
  return null
}

// ── visuals ──────────────────────────────────────────────────────────────────

function NetworkNodeDiagram() {
  return (
    <div className="relative w-full h-44 bg-slate-50 border border-slate-100 rounded-sm overflow-hidden p-6">
      <svg className="w-full h-full text-slate-200">
        <path d="M 20 20 L 50 50 L 80 20 M 50 50 L 50 85" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="3 3" />
        <circle cx="20%" cy="20%" r="5" fill="#964b3c" />
        <circle cx="80%" cy="20%" r="5" fill="#334155" />
        <circle cx="50%" cy="85%" r="5" fill="#334155" />
        <circle cx="50%" cy="50%" r="12" fill="#964b3c" stroke="white" strokeWidth="3" />
        <foreignObject x="43%" y="43%" width="14" height="14">
          <div className="flex items-center justify-center w-full h-full text-white">
            <Users size={10} />
          </div>
        </foreignObject>
      </svg>
    </div>
  )
}

// ── core sub-components ─────────────────────────────────────────────────────

function MarkdownContent({ content }: { content: string }) {
  const lines = content.split('\n').filter(l => l.trim())
  const dataRows: [string, string][] = []
  const remainingLines: string[] = []
  
  lines.forEach(line => {
    const row = parseDataRow(line)
    if (row) dataRows.push(row)
    else remainingLines.push(line)
  })

  return (
    <div className="space-y-4">
      {dataRows.length > 0 && (
        <div className="grid grid-cols-1 gap-y-3">
          {dataRows.map(([label, value], i) => (
            <div key={i} className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-4 group">
               <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 min-w-[120px] pt-0.5">
                  {label}
               </span>
               <span className="text-[13px] font-bold text-slate-900 flex-1 leading-tight tracking-tight">
                  {value}
               </span>
            </div>
          ))}
        </div>
      )}
      {remainingLines.length > 0 && (
        <div className="prose prose-sm prose-slate dark:prose-invert max-w-none 
          prose-p:leading-relaxed prose-p:my-1.5 
          prose-strong:text-slate-950 prose-strong:font-black
          text-[13px] font-medium text-slate-700">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {remainingLines.join('\n')}
          </ReactMarkdown>
        </div>
      )}
    </div>
  )
}

function GridSection({ title, children, icon: Icon, className = "" }: { title: string; children: React.ReactNode; icon?: any; className?: string }) {
  if (!children) return null
  return (
    <div className={`flex flex-col h-full bg-white border border-slate-100 rounded-none overflow-hidden shadow-sm ${className}`}>
      <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-[#964b3c]">
            {Icon && <Icon size={14} />}
          </div>
          <h3 className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-900">
            {title}
          </h3>
        </div>
        <div className="w-1.5 h-1.5 rounded-full bg-slate-200" />
      </div>
      <div className="p-8 flex-1">
        {children}
      </div>
    </div>
  )
}

function TimelineItem({ year, description }: { year: string; description: string }) {
  return (
    <div className="relative pl-10 pb-12 last:pb-0 group">
      <div className="absolute left-[3px] top-0 bottom-0 w-[1.5px] bg-slate-100 group-last:bottom-auto group-last:h-4" />
      <div className="absolute left-0 top-1.5 w-2 h-2 rounded-full border-2 border-slate-900 bg-white z-10" />
      
      <div className="flex flex-col gap-3">
         <span className="text-[11px] font-black tracking-widest text-[#964b3c] uppercase">{year}</span>
         <div className="bg-slate-50/30 p-4 border border-slate-100 rounded-sm">
            <MarkdownContent content={description} />
         </div>
      </div>
    </div>
  )
}

// ── main dashboard view ─────────────────────────────────────────────────────

function InfographicDashboard({ data }: { data: InfographicResponse }) {
  const headerTitleCombined = data.header?.title || 'Infographic View'
  const mainTitle = stripMarkdownSymbols(headerTitleCombined)
  const subTitle = stripMarkdownSymbols(data.header?.subtitle || '')

  const items = useMemo(() => [
    ...(data.left_column ?? []),
    ...(data.right_column ?? [])
  ], [data.left_column, data.right_column])

  const timelineItems = useMemo(() => {
    return items.filter(it => it.title.match(/\d{4}/) || it.description.match(/\d{4}/))
  }, [items])

  const profileItems = useMemo(() => {
    return items.filter(it => !timelineItems.includes(it) && 
      (it.icon === 'family' || it.icon === 'education' || 
       it.title.toLowerCase().includes('identity') || 
       it.title.toLowerCase().includes('origin')))
  }, [items, timelineItems])

  const operationsItems = useMemo(() => {
    return items.filter(it => !timelineItems.includes(it) && !profileItems.includes(it))
  }, [items, timelineItems, profileItems])

  return (
    <div className="bg-white text-slate-900 font-sans min-h-screen relative p-10 lg:p-14 selection:bg-[#964b3c] selection:text-white">
      
      {/* ── Main Header ── */ }
      <header className="mb-16 px-4">
        <div className="flex flex-col lg:flex-row items-end justify-between gap-12 border-b-2 border-slate-900 pb-12">
          <div className="flex-1">
             <h1 className="text-4xl md:text-6xl lg:text-7xl font-black uppercase tracking-tighter leading-[0.85] text-slate-900">
                {mainTitle.includes(':') ? (
                  mainTitle.split(':').map((w, i) => (
                    <span key={i} className={`block ${i === 1 ? 'text-[#964b3c] mt-2' : ''}`}>{w.trim()}</span>
                  ))
                ) : (
                  <span>{mainTitle}</span>
                )}
             </h1>
          </div>
          
          {subTitle && (
            <div className="lg:w-2/5 text-right">
               <p className="text-md md:text-lg font-bold italic text-slate-400 uppercase tracking-wide leading-tight border-r-4 border-[#964b3c] pr-8">
                  {subTitle}
               </p>
            </div>
          )}
        </div>
      </header>

      {/* ── Clean Landscape Grid ── */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* Profile (3/12) */}
        <div className="lg:col-span-3 space-y-8">
          <GridSection title="Subject Profile" icon={User}>
            <div className="space-y-12 py-2">
              {profileItems.slice(0, 10).map((it, i) => (
                <div key={i}>
                   <h4 className="font-black text-[10px] uppercase tracking-widest text-[#964b3c] mb-5 border-l-2 border-[#964b3c] pl-4">
                      {stripMarkdownSymbols(it.title)}
                   </h4>
                   <MarkdownContent content={it.description} />
                </div>
              ))}
            </div>
          </GridSection>
        </div>

        {/* Timeline (5/12) */}
        <div className="lg:col-span-5">
          <GridSection title="Temporal Events" icon={History}>
             <div className="mt-8">
               {timelineItems.length > 0 ? (
                 timelineItems.map((it, i) => {
                   const yearMatch = it.title.match(/(\d{4})/) || it.description.match(/(\d{4})/)
                   const year = yearMatch ? yearMatch[1] : `PHASE ${i + 1}`
                   return <TimelineItem key={i} year={year} description={it.description || it.title} />
                 })
               ) : (
                <div className="h-40 flex flex-col items-center justify-center text-slate-200 border-2 border-dashed border-slate-50 gap-4">
                   <p className="font-black uppercase text-[10px] tracking-widest italic opacity-50">No temporal data found</p>
                </div>
               )}
             </div>
          </GridSection>
        </div>

        {/* Details (4/12) */}
        <div className="lg:col-span-4 space-y-8">
           <GridSection title="Data Metrics" icon={BarChart2}>
             {data.stat && (
               <div className="flex items-end gap-5 mb-14">
                  <div className="text-7xl font-black tracking-tighter text-slate-900 leading-none">
                     {data.stat.value}
                  </div>
                  <div className="mb-1 bg-slate-100 px-3 py-1">
                     <div className="text-[10px] font-black uppercase tracking-widest text-[#964b3c]">
                       {stripMarkdownSymbols(data.stat.label)}
                     </div>
                  </div>
               </div>
             )}

             <div className="space-y-12">
                <div className="pt-2">
                   <NetworkNodeDiagram />
                </div>

                <div className="space-y-6 pt-10 border-t border-slate-100">
                  {operationsItems.slice(0, 8).map((it, i) => (
                    <div key={i} className="group p-6 bg-slate-50/50 border border-slate-100 hover:bg-white transition-all">
                       <div className="flex items-center gap-2 mb-4">
                          <Zap size={14} className="text-[#964b3c]" />
                          <h4 className="text-[10px] font-black uppercase tracking-wider text-slate-950">
                             {stripMarkdownSymbols(it.title)}
                          </h4>
                       </div>
                       <MarkdownContent content={it.description} />
                    </div>
                  ))}
                </div>
             </div>
           </GridSection>
        </div>
      </main>

    </div>
  )
}


function parseMarkdownToInfographic(raw: string): InfographicResponse {
  const lines = raw.split('\n')
  const sections: InfographicColumn[] = []
  
  let firstHeading = ''
  let currentHeader = ''
  let currentContent: string[] = []
  
  const finalizeSection = () => {
    const desc = currentContent.join('\n').trim()
    if (!desc) return
    let icon = 'info'
    const t = currentHeader.toLowerCase()
    if (t.includes('criminal') || t.includes('crime') || t.includes('arrest') || t.includes('gang') || t.includes('associate')) icon = 'crime'
    else if (t.includes('education') || t.includes('academic') || t.includes('mba')) icon = 'education'
    else if (t.includes('family') || t.includes('husband')) icon = 'family'
    else if (t.includes('personal') || t.includes('identity')) icon = 'personal'

    sections.push({ title: currentHeader, description: desc, icon })
    currentContent = []
  }

  for (const line of lines) {
    const t = line.trim()
    if (!t) continue
    
    const isSectionStart = t.startsWith('**PART') || 
                           (t.startsWith('**') && t.endsWith('**') && !t.includes('•') && t.length > 5) ||
                           t.match(/^#+\s/)

    if (!firstHeading && t.length > 5) {
      firstHeading = t
    }

    if (isSectionStart) {
      finalizeSection()
      currentHeader = t
    } else if (t.startsWith('**') && t.endsWith(':**')) {
      finalizeSection()
      currentHeader = t.slice(0, -1)
    } else {
      currentContent.push(line)
    }
  }
  finalizeSection()

  return {
    header: { 
      title: firstHeading || 'Information Extract', 
      subtitle: '' 
    },
    left_column: sections,
    right_column: [],
    source_id: 'clean-v1'
  }
}

// ── main helper ───────────────────────────────────────────────────────────────

function extractJson(raw: string): string {
  const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (fenceMatch) return fenceMatch[1].trim()
  const braceStart = raw.indexOf('{')
  const braceEnd = raw.lastIndexOf('}')
  if (braceStart !== -1 && braceEnd > braceStart) return raw.slice(braceStart, braceEnd + 1)
  return raw.trim()
}

export function InfographicInsightViewer({ content }: InfographicInsightViewerProps) {
  let data: InfographicResponse | null = null
  
  try {
    const jsonStr = extractJson(content)
    data = JSON.parse(jsonStr) as InfographicResponse
    if (!data.left_column && !data.header) throw new Error()
  } catch {
    data = parseMarkdownToInfographic(content)
  }

  if (!data) return null

  return <InfographicDashboard data={data} />
}