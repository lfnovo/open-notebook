'use client'

import {
  InfographicResponse,
  InfographicColumn,
  InfographicHighlight,
} from '@/lib/api/infographic'
import {
  Info, Calendar, Target, Briefcase, AlertTriangle, Network,
  User, Building, Shield, Activity, BookOpen, BarChart2, MapPin,
  Scale, Lightbulb, FileText, Users, Zap, Sparkles,
} from 'lucide-react'

interface InfographicInsightViewerProps {
  content: string
}

// ── detector ──────────────────────────────────────────────────────────────────

export function isInfographicInsight(insightType: string): boolean {
  return insightType.toLowerCase().includes('infographic')
}

// ── icon map ──────────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, React.ElementType> = {
  user: User, building: Building, shield: Shield, activity: Activity,
  finance: BarChart2, law: Scale, medical: Zap, briefcase: Briefcase,
  document: FileText, education: BookOpen, chart: BarChart2, network: Network,
  info: Info, calendar: Calendar, target: Target, alert: AlertTriangle,
  lightbulb: Lightbulb, location: MapPin, group: Users, family: Users,
  timeline: Calendar, crime: AlertTriangle,
}

function ColIcon({ name }: { name?: string }) {
  const Icon = ICON_MAP[(name || 'info').toLowerCase()] ?? Info
  return <Icon className="h-4 w-4 text-blue-600 shrink-0" />
}

// Gradient pairs for highlight cards
const HIGHLIGHT_GRADIENTS = [
  'from-blue-600 to-blue-800',
  'from-teal-600 to-teal-800',
  'from-slate-600 to-slate-800',
]

function ColBlock({ item }: { item: InfographicColumn }) {
  return (
    <div className="group flex gap-3 items-start p-3 rounded-xl border border-transparent hover:border-blue-100 hover:bg-blue-50/50 dark:hover:bg-blue-950/10 transition-all duration-200">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/40 dark:to-indigo-900/40 flex items-center justify-center shrink-0 shadow-sm">
        <ColIcon name={item.icon} />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 mb-1">
          {item.title}
        </p>
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{item.description}</p>
      </div>
    </div>
  )
}

function HighlightCard({ item, gradient }: { item: InfographicHighlight; gradient: string }) {
  return (
    <div className="rounded-xl overflow-hidden shadow-sm border border-border/20 flex flex-col hover:shadow-md transition-shadow duration-200">
      <div className={`bg-gradient-to-br ${gradient} text-white px-4 py-3.5`}>
        <p className="text-[11px] font-black uppercase tracking-wide leading-tight">{item.title}</p>
        {item.subtitle && (
          <p className="text-[10px] opacity-75 mt-1 font-medium">{item.subtitle}</p>
        )}
      </div>
      <div className="p-3.5 bg-white dark:bg-slate-900 flex-1">
        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{item.description}</p>
      </div>
    </div>
  )
}

function InfographicView({ data }: { data: InfographicResponse }) {
  const header     = data.header ?? { title: 'REPORT', subtitle: '' }
  const left       = data.left_column ?? []
  const right      = data.right_column ?? []
  const highlights = data.highlights ?? []
  const stat       = data.stat

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 text-white p-8 text-center shadow-lg">
        {/* decorative rings */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full border-2 border-white" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full border border-white" />
        </div>
        <div className="relative">
          <div className="inline-flex items-center gap-1.5 bg-blue-500/20 border border-blue-400/30 rounded-full px-3 py-1 mb-4">
            <Sparkles className="h-3 w-3 text-blue-300" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-blue-300">Intelligence Report</span>
          </div>
          <h2 className="text-2xl font-black uppercase tracking-wide text-white mb-2">{header.title}</h2>
          <div className="w-16 h-0.5 bg-gradient-to-r from-transparent via-blue-400 to-transparent mx-auto mb-3" />
          {header.subtitle && (
            <p className="text-sm text-blue-200/80 italic max-w-xl mx-auto leading-relaxed">{header.subtitle}</p>
          )}
        </div>
      </div>

      {/* ── Two-column body ── */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border bg-card p-2 space-y-1">
          {left.map((item, i) => <ColBlock key={i} item={item} />)}
        </div>
        <div className="space-y-4">
          <div className="rounded-xl border bg-card p-2 space-y-1">
            {right.map((item, i) => <ColBlock key={i} item={item} />)}
          </div>
          {/* Stat card */}
          {stat?.value && (
            <div className="rounded-xl border bg-gradient-to-br from-blue-600 to-indigo-700 text-white p-5 shadow-md">
              <div className="text-4xl font-black leading-none tracking-tight">{stat.value}</div>
              <div className="text-xs font-bold uppercase tracking-widest text-blue-200 mt-2">{stat.label}</div>
            </div>
          )}
        </div>
      </div>

      {/* ── Highlights ── */}
      {highlights.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground px-2">
              Key Highlights &amp; Findings
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            {highlights.slice(0, 3).map((h, i) => (
              <HighlightCard key={i} item={h} gradient={HIGHLIGHT_GRADIENTS[i % HIGHLIGHT_GRADIENTS.length]} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── main viewer ───────────────────────────────────────────────────────────────

function extractJson(raw: string): string {
  // Strip markdown code fences: ```json ... ``` or ``` ... ```
  const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (fenceMatch) return fenceMatch[1].trim()
  // Find first { ... } block in case there's surrounding text
  const braceStart = raw.indexOf('{')
  const braceEnd = raw.lastIndexOf('}')
  if (braceStart !== -1 && braceEnd > braceStart) return raw.slice(braceStart, braceEnd + 1)
  return raw.trim()
}

export function InfographicInsightViewer({ content }: InfographicInsightViewerProps) {
  let data: InfographicResponse | null = null
  try {
    data = JSON.parse(extractJson(content)) as InfographicResponse
  } catch {
    // not valid JSON
  }

  if (!data || (!data.header && !data.left_column && !data.highlights)) {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
        No infographic data available.
      </div>
    )
  }

  return <InfographicView data={data} />
}
