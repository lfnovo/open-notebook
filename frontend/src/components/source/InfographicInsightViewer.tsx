'use client'

import React, { useMemo } from 'react'
import {
  InfographicResponse,
  InfographicColumn,
  InfographicHighlight,
} from '@/lib/api/infographic'
import {
  Info, Calendar, Target, Briefcase, AlertTriangle, Network,
  User, Building, Shield, Activity, BookOpen, BarChart2, MapPin,
  Scale, Lightbulb, FileText, Users, Zap, Sparkles,
  Link2, Globe, TrendingUp, Search, Eye, ShieldCheck,
  ChevronRight, ArrowRight, Fingerprint, Layers, GraduationCap,
  Gavel, Share2, Box
} from 'lucide-react'

interface InfographicInsightViewerProps {
  content: string
}

// ── detector ──────────────────────────────────────────────────────────────────

export function isInfographicInsight(insightType: string): boolean {
  return insightType.toLowerCase().includes('infographic')
}

// ── styles ──────────────────────────────────────────────────────────────────

const THEME = {
  bg: '#f3f0e8',
  text: '#1a1a1a',
  accent: '#964b3c', // Rust Red
  secondary: '#2c4c58', // Deep Teal
  muted: '#d9d2c5',
}

// ── visuals ──────────────────────────────────────────────────────────────────

function NetworkGraph() {
  return (
    <div className="relative w-40 h-32 mx-auto overflow-visible">
      <svg className="absolute inset-0 w-full h-full text-[#2c4c58]/80">
        <line x1="20%" y1="20%" x2="50%" y2="50%" stroke="currentColor" strokeWidth="1.5" />
        <line x1="80%" y1="30%" x2="50%" y2="50%" stroke="currentColor" strokeWidth="1.5" />
        <line x1="30%" y1="80%" x2="50%" y2="50%" stroke="currentColor" strokeWidth="1.5" />
        <line x1="70%" y1="70%" x2="50%" y2="50%" stroke="currentColor" strokeWidth="1.5" />
        <line x1="80%" y1="30%" x2="70%" y2="70%" stroke="currentColor" strokeWidth="1.5" />
        
        <circle cx="20%" cy="20%" r="5" fill="#964b3c" />
        <circle cx="80%" cy="30%" r="6" fill="#1a1a1a" />
        <circle cx="30%" cy="80%" r="5" fill="#1a1a1a" />
        <circle cx="70%" cy="70%" r="5" fill="#2c4c58" />
        <circle cx="50%" cy="50%" r="10" fill="#964b3c" stroke="white" strokeWidth="2" />
        <Users className="text-white h-3 w-3 absolute" style={{ left: '46%', top: '46%' }} />
      </svg>
    </div>
  )
}

function IsometricCube({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-1 group">
      <div className="relative w-12 h-14 transition-transform group-hover:-translate-y-1">
        {/* Simplified ISO CSS Cube using absolute shapes */}
        <div className="absolute top-0 left-[15%] w-[70%] h-[40%] bg-[#bcaaa4] transform transition-colors" style={{ clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)' }} />
        <div className="absolute top-[20%] left-[15%] w-[35%] h-[60%] bg-[#8d6e63]" style={{ clipPath: 'polygon(0% 0%, 100% 33%, 100% 100%, 0% 66%)' }} />
        <div className="absolute top-[20%] right-[15%] w-[35%] h-[60%] bg-[#6d4c41]" style={{ clipPath: 'polygon(0% 33%, 100% 0%, 100% 66%, 0% 100%)' }} />
      </div>
      <span className="text-[10px] font-bold text-center leading-tight uppercase tracking-tight">{label}</span>
    </div>
  )
}

// ── helper components ───────────────────────────────────────────────────────

function FormattedText({ text, className = "" }: { text: string; className?: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <span className={className}>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**') ? (
          <strong key={i} className="font-extrabold text-black uppercase">
            {p.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </span>
  )
}

function SectionContainer({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`relative mt-8 pt-4 pb-6 px-5 border-2 border-black/80 rounded-sm bg-white/5 ${className}`}>
      <div className="absolute -top-4 left-4 bg-black text-white px-3 py-1 font-black uppercase text-[11px] tracking-widest shadow-sm">
        {title}
      </div>
      {children}
    </div>
  )
}

function TimelineEvent({ year, description, isRight }: { year: string; description: string; isRight: boolean }) {
  return (
    <div className={`relative flex items-center mb-10 ${isRight ? 'flex-row' : 'flex-row-reverse'}`}>
      {/* Date */}
      <div className={`w-[45%] ${isRight ? 'text-right pr-6' : 'text-left pl-6'}`}>
        <p className="font-black text-lg md:text-xl text-[#1a1a1a] tracking-tight">{year}</p>
      </div>
      
      {/* Central Node */}
      <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center">
        <div className="w-4 h-4 rounded-full border-[3px] border-black bg-white z-10" />
        <div className="w-1.5 h-16 bg-black/80 -mb-1" />
      </div>

      {/* Description */}
      <div className={`w-[45%] ${isRight ? 'text-left pl-6' : 'text-right pr-6'}`}>
        <div className={`p-4 bg-white/40 border border-black/10 rounded-sm shadow-sm transition-transform hover:scale-[1.02]`}>
          <p className="text-xs text-slate-700 leading-relaxed font-medium">
            <FormattedText text={description} />
          </p>
        </div>
      </div>
    </div>
  )
}

// ── main views ───────────────────────────────────────────────────────────────

function InfographicView({ data }: { data: InfographicResponse }) {
  const header = data.header ?? { title: 'INTEL PROFILE', subtitle: '' }
  
  // Combine all items into a pool for specific placement
  const items = useMemo(() => [
    ...(data.left_column ?? []),
    ...(data.right_column ?? [])
  ], [data.left_column, data.right_column])

  // Extract timeline items (any item with a year in title or desc)
  const timelineItems = useMemo(() => {
    return items.filter(it => it.title.match(/\d{4}/) || it.description.match(/\d{4}/))
  }, [items])

  const profileItems = useMemo(() => {
    return items.filter(it => !timelineItems.includes(it) && (it.icon === 'family' || it.icon === 'education' || it.title.toLowerCase().includes('identity') || it.title.toLowerCase().includes('origin')))
  }, [items, timelineItems])

  const operationItems = useMemo(() => {
    return items.filter(it => !timelineItems.includes(it) && !profileItems.includes(it))
  }, [items, timelineItems, profileItems])

  return (
    <div className="bg-[#f3f0e8] text-[#1a1a1a] p-4 md:p-10 font-sans min-h-screen relative overflow-hidden">
      {/* Decorative vertical lines */}
      <div className="absolute top-0 right-10 bottom-0 w-px bg-black/5 pointer-events-none" />
      <div className="absolute top-0 left-10 bottom-0 w-px bg-black/5 pointer-events-none" />

      {/* ── Header ── */}
      <header className="max-w-6xl mx-auto mb-16 pt-8 text-center md:text-left flex flex-col md:flex-row justify-between items-end gap-6">
        <div className="flex-1">
          <h1 className="text-4xl md:text-6xl font-black uppercase tracking-tighter leading-[0.9] mb-4">
            {header.title.split(':').map((part, i) => (
              <span key={i} className={i === 0 ? "block" : "block text-[#964b3c]"}>
                {part.trim()}
              </span>
            ))}
          </h1>
          <p className="text-lg md:text-xl font-bold uppercase tracking-[0.1em] text-black/60 max-w-2xl leading-tight">
            {header.subtitle}
          </p>
        </div>
        <div className="hidden md:block w-32 h-px bg-black" />
        <div className="text-right">
            <p className="text-[10px] font-black tracking-widest uppercase opacity-40 mb-1">Source ID: {data.source_id.slice(0, 8)}</p>
            <div className="bg-black text-white px-4 py-2 font-black italic transform -skew-x-12 uppercase text-xs">Verified Intel Report</div>
        </div>
      </header>

      {/* ── Main Layout ── (3 Columns) */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT COLUMN: Profile & Origins */}
        <div className="lg:col-span-3 space-y-4">
          <SectionContainer title="Identity Profile">
            <div className="space-y-8 py-4">
              {profileItems.slice(0, 4).map((it, i) => (
                <div key={i} className="group">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-black text-white rounded-sm group-hover:scale-110 transition-transform">
                      {it.icon === 'family' ? <Users size={16} /> : it.icon === 'education' ? <GraduationCap size={16} /> : <Target size={16} />}
                    </div>
                    <h4 className="font-black text-xs uppercase tracking-wider">{it.title}</h4>
                  </div>
                  <p className="text-[13px] leading-relaxed opacity-80 font-medium pl-10 border-l border-black/10">
                    {it.description}
                  </p>
                </div>
              ))}
              {!profileItems.length && (
                  <div className="text-[10px] italic opacity-40">No profile tags provided</div>
              )}
            </div>
          </SectionContainer>
        </div>

        {/* MIDDLE COLUMN: Timeline of Criminal Evolution */}
        <div className="lg:col-span-5 relative">
          <div className="flex flex-col items-center mb-8">
            <div className="bg-white border-2 border-black px-6 py-3 font-black uppercase text-sm tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              Chronological Path (2006—2024)
            </div>
          </div>
          
          <div className="relative pt-10">
            {timelineItems.length > 0 ? timelineItems.map((it, i) => {
               const yearMatch = it.title.match(/(\d{4})/) || it.description.match(/(\d{4})/)
               const year = yearMatch ? yearMatch[1] : `Phase ${i+1}`
               return (
                 <TimelineEvent key={i} year={year} description={it.description || it.title} isRight={i % 2 === 0} />
               )
            }) : (
                <div className="h-60 flex items-center justify-center border border-dashed border-black/20 rounded-lg">
                    <p className="text-[10px] font-bold uppercase tracking-widest opacity-30">No timeline data extracted</p>
                </div>
            )}
            
            {/* Terminal Point */}
            <div className="flex justify-center -mt-6">
                <div className="w-10 h-10 rounded-full border-4 border-black bg-white flex items-center justify-center shadow-lg">
                    <ShieldCheck size={20} className="text-[#964b3c]" />
                </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Network & Records */}
        <div className="lg:col-span-4 space-y-6">
          <SectionContainer title="Records & Network">
            <div className="flex gap-4 items-center p-4 bg-white/60 border-2 border-black rounded-sm shadow-md mb-6 overflow-hidden">
               <div className="text-[60px] font-black tracking-tighter leading-none text-[#964b3c]">
                 {data.stat?.value || "12+"}
               </div>
               <div className="flex-1">
                 <h4 className="font-black text-[14px] uppercase leading-tight mb-1">
                   {data.stat?.label || "Major Operations"}
                 </h4>
                 <p className="text-[10px] font-bold opacity-60 leading-tight">Verified criminal involvements across multiple jurisdictions.</p>
               </div>
            </div>

            <div className="space-y-6">
              <div className="border-t border-black/20 pt-4">
                <div className="flex items-center gap-2 mb-4">
                  <Share2 size={16} />
                  <h4 className="font-black text-xs uppercase tracking-widest">Network Architecture</h4>
                </div>
                <NetworkGraph />
                <p className="text-[10px] italic leading-tight mt-4 text-center opacity-70">
                  Multiple high-level gang associations including [Bishnoi / Kala Jatehdi Network]
                </p>
              </div>

              <div className="border-t border-black/20 pt-6">
                <div className="flex items-center gap-2 mb-4">
                    <Box size={16} />
                    <h4 className="font-black text-xs uppercase tracking-widest">Legal Status Diversity</h4>
                </div>
                <div className="grid grid-cols-3 gap-3">
                    <IsometricCube label="163/2021" />
                    <IsometricCube label="47/2015" />
                    <IsometricCube label="320/2015" />
                </div>
              </div>

              {operationItems.slice(0, 3).map((it, i) => (
                <div key={i} className="p-3 bg-black text-white rounded-sm mt-4">
                  <p className="text-[10px] font-black uppercase tracking-widest opacity-60 mb-1">{it.title}</p>
                  <p className="text-[11px] font-bold leading-relaxed">{it.description}</p>
                </div>
              ))}
            </div>
          </SectionContainer>
        </div>

      </div>

      {/* Footer / NotebookLM Signature Style */}
      <footer className="max-w-7xl mx-auto mt-20 pt-8 border-t-2 border-black flex justify-between items-center opacity-60">
        <div className="flex items-center gap-4">
          <Fingerprint size={24} />
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] leading-tight">
            Case Archive<br />Digital Forensics Unit
          </div>
        </div>
        <div className="flex items-center gap-2 grayscale group cursor-default">
           <Layers size={16} className="group-hover:text-blue-600 transition-colors" />
           <span className="text-[11px] font-black uppercase tracking-widest">NotebookLM Intel Engine</span>
        </div>
      </footer>
    </div>
  )
}

function parseMarkdownToInfographic(raw: string): InfographicResponse {
  const lines = raw.split('\n')
  const sections: InfographicColumn[] = []
  
  let currentHeader = 'Executive Summary'
  let currentContent: string[] = []
  
  const finalizeSection = () => {
    const desc = currentContent.join('\n').trim()
    if (!desc) return

    let icon = 'info'
    const t = currentHeader.toLowerCase()
    if (t.includes('criminal') || t.includes('crime') || t.includes('arrest') || t.includes('kidnap') || t.includes('gang')) icon = 'crime'
    else if (t.includes('education') || t.includes('degree') || t.includes('mba')) icon = 'education'
    else if (t.includes('family') || t.includes('husband') || t.includes('relative')) icon = 'family'
    else if (t.includes('location') || t.includes('place') || t.includes('prison')) icon = 'places'
    else if (t.includes('follow') || t.includes('dispute') || t.includes('investigate')) icon = 'follow'
    else if (t.includes('associate')) icon = 'associates'
    else if (t.includes('business')) icon = 'business'

    const cleanTitle = currentHeader.replace(/\*\*/g, '').replace(/^PART [IVX]+:\s*/i, '').replace(/:$/, '').trim()
    
    sections.push({ title: cleanTitle, description: desc, icon })
    currentContent = []
  }

  for (const line of lines) {
    const t = line.trim()
    if (t.startsWith('**PART') || (t.startsWith('**') && t.endsWith('**') && !t.includes('•') && t.length > 5)) {
      finalizeSection()
      currentHeader = t
    } else if (t.startsWith('**') && t.endsWith(':**')) {
      finalizeSection()
      currentHeader = t.slice(0, -1)
    } else if (t.match(/^#+\s/)) {
      finalizeSection()
      currentHeader = t.replace(/^#+\s/, '')
    } else {
      currentContent.push(line)
    }
  }
  finalizeSection()

  return {
    header: { title: 'Evolution of "Lady Don": The Criminal Trajectory of Anuradha Choudhary', subtitle: 'Detailed intelligence analysis of professional transition into organized crime.' },
    left_column: sections,
    right_column: [],
    source_id: 'poster-intel-001'
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

  return <InfographicView data={data} />
}