'use client'

import { useMemo } from 'react'
import {
  Phone, MessageSquare, MapPin, Radio,
  ArrowDownCircle, ArrowUpCircle, Activity,
  AlertTriangle, Clock, Users, Signal,
  Lightbulb, FileCode, ChevronRight, Target,
  TrendingUp, BarChart2,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface TimelineAnalysisInsightViewerProps {
  content: string
}

export function isTimelineAnalysisInsight(insightType: string): boolean {
  return insightType.toLowerCase().includes('timeline')
}

function extractSection(content: string, heading: string): string {
  const mdRe = new RegExp(
    `#{1,4}\\s*\\*?\\*?${heading}[^\\n]*\\n([\\s\\S]*?)(?=\\n#{1,4}\\s|\\n---\\n|$)`,
    'i'
  )
  const mdM = content.match(mdRe)
  if (mdM) return mdM[1].trim()
  const secRe = new RegExp(
    `SECTION\\s+\\d+\\s*[=—–-]+\\s*${heading}[^\\n]*\\n(?:[=\\-]{3,}\\n)?([\\s\\S]*?)(?=\\n[=\\-]{3,}\\nSECTION|\\n[=\\-]{10,}|$)`,
    'i'
  )
  const secM = content.match(secRe)
  if (secM) return secM[1].trim()
  return ''
}

function extractBullets(text: string): { label: string; detail: string }[] {
  const results: { label: string; detail: string }[] = []
  for (const line of text.split('\n')) {
    const trimmed = line.trim()
    if (!/^[-*•]|\d+\./.test(trimmed)) continue
    const clean = trimmed.replace(/^[-*•\d.]+\s*/, '').replace(/\*\*/g, '')
    const colonIdx = clean.indexOf(':')
    if (colonIdx > 0 && colonIdx < 50) {
      results.push({ label: clean.slice(0, colonIdx).trim(), detail: clean.slice(colonIdx + 1).trim() })
    } else {
      results.push({ label: '', detail: clean })
    }
  }
  return results
}

function extractCodeTokens(text: string): string[] {
  return [...text.matchAll(/`([^`]+)`/g)].map(m => m[1]).filter(Boolean)
}

function isInsuff(s: string): boolean {
  return /insufficient|not available|n\/a/i.test(s.trim())
}

function detectServiceTypes(content: string): { type: string; label: string; color: string; icon: React.ElementType }[] {
  const types: { token: string; type: string; label: string; color: string; icon: React.ElementType }[] = [
    { token: 'SMT',   type: 'SMT',   label: 'Short Message Transfer',  color: 'from-violet-600 to-violet-800',  icon: MessageSquare },
    { token: 'IN',    type: 'IN',    label: 'Incoming Call',            color: 'from-emerald-600 to-emerald-800', icon: ArrowDownCircle },
    { token: 'OUT',   type: 'OUT',   label: 'Outgoing Call',            color: 'from-blue-600 to-blue-800',      icon: ArrowUpCircle },
    { token: 'BSM',   type: 'BSM',   label: 'Bulk Short Message',       color: 'from-amber-600 to-amber-800',    icon: Radio },
    { token: 'Voice', type: 'Voice', label: 'Voice Call',               color: 'from-teal-600 to-teal-800',      icon: Phone },
    { token: 'Pre',   type: 'Pre',   label: 'Pre-paid Service',         color: 'from-slate-600 to-slate-800',    icon: Signal },
  ]
  return types
    .filter(t => content.includes(`\`${t.token}\``) || content.includes(t.token))
    .map(({ token: _t, ...rest }) => rest)
}

function parseUseCases(content: string): { title: string; desc: string }[] {
  const section = extractSection(content, 'Use Cases') || extractSection(content, 'Possible Use Cases') || extractSection(content, 'Potential Use Cases')
  if (!section) return []
  return extractBullets(section).filter(b => b.label || b.detail).map(b => ({ title: b.label || b.detail.split('.')[0], desc: b.detail }))
}

function parseNextSteps(content: string): string[] {
  const section = extractSection(content, 'Next Steps')
  if (!section) return []
  return extractBullets(section).map(b => (b.label ? `${b.label}: ${b.detail}` : b.detail)).filter(Boolean)
}

function parseFields(content: string): { name: string; example: string }[] {
  const section = extractSection(content, 'Data Structure') || extractSection(content, 'Data Overview')
  if (!section) return []
  return extractBullets(section).filter(b => b.label).map(b => {
    const ex = b.detail.match(/e\.g\.,?\s*`?([^`)]+)`?/)
    return { name: b.label, example: ex ? ex[1].trim() : b.detail.slice(0, 60) }
  })
}

function parseExample(content: string): { request: string; response: string } | null {
  const reqM = content.match(/\*\*Request\*\*[:\s]*\n([^\n]+)/)
  const resM = content.match(/```[a-z]*\n([\s\S]*?)```/)
  if (!reqM && !resM) return null
  return { request: reqM ? reqM[1].replace(/"/g, '').trim() : '', response: resM ? resM[1].trim() : '' }
}

function parseNotes(content: string): string[] {
  const section = extractSection(content, 'Notes')
  if (!section) return []
  return extractBullets(section).map(b => (b.label ? `${b.label}: ${b.detail}` : b.detail)).filter(Boolean)
}

function parseObservations(content: string): { title: string; detail: string }[] {
  const section = extractSection(content, 'Notable Observations') || extractSection(content, 'Key Observations')
  if (!section) return []
  return extractBullets(section).filter(b => b.label || b.detail).map(b => ({ title: b.label || b.detail.split('.')[0], detail: b.detail }))
}

function parseMissingData(content: string): string[] {
  const section = extractSection(content, 'Missing') || extractSection(content, 'Placeholder')
  if (!section) return []
  return extractBullets(section).map(b => (b.label ? `${b.label}: ${b.detail}` : b.detail)).filter(Boolean)
}

function parseConclusion(content: string): string {
  const section = extractSection(content, 'Conclusion')
  return section.replace(/\*\*/g, '').replace(/\n+/g, ' ').trim()
}

function parseImsInfo(content: string): string[] {
  const lines: string[] = []
  for (const line of content.split('\n')) {
    if (/IMS|VoLTE|VoIP/i.test(line)) {
      const clean = line.replace(/^[-*•\d.#\s]+/, '').replace(/\*\*/g, '').trim()
      if (clean.length > 10) lines.push(clean)
    }
  }
  return [...new Set(lines)].slice(0, 4)
}

interface FreqRow { period: string; count: number }
function parseFrequencyTable(content: string): { rows: FreqRow[]; highest: string; lowest: string; pattern: string } {
  const section = extractSection(content, 'FREQUENCY[\\s\\S]{0,20}ANAL') || extractSection(content, 'FREQUENCY')
  const rows: FreqRow[] = []
  for (const line of section.split('\n')) {
    if (!line.includes('|')) continue
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (cells.length < 2 || /^[-:]+$/.test(cells[0]) || /period|count/i.test(cells[0])) continue
    const count = parseInt(cells[1])
    if (!isNaN(count)) rows.push({ period: cells[0], count })
  }
  const bullets = extractBullets(section)
  return {
    rows,
    highest: bullets.find(b => /highest/i.test(b.label))?.detail ?? '',
    lowest:  bullets.find(b => /lowest/i.test(b.label))?.detail ?? '',
    pattern: bullets.find(b => /pattern/i.test(b.label))?.detail ?? '',
  }
}

interface EntityRow { entity: string; period: string; count: string; value: string }
function parseEntityTable(content: string): EntityRow[] {
  const section = extractSection(content, 'ENTITY[\\s\\S]{0,30}ANAL') || extractSection(content, 'ENTITY')
  if (!section) return []
  const rows: EntityRow[] = []
  for (const line of section.split('\n')) {
    if (!line.includes('|')) continue
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (cells.length < 3 || /^[-:]+$/.test(cells[0]) || /entity/i.test(cells[0])) continue
    rows.push({ entity: cells[0], period: cells[1] ?? '', count: cells[2] ?? '', value: cells[3] ?? '' })
  }
  return rows
}

function parseEntityInsights(content: string): string[] {
  const section = extractSection(content, 'ENTITY[\\s\\S]{0,30}ANAL') || extractSection(content, 'ENTITY')
  if (!section) return []
  const insightBlock = section.match(/Insights:([\s\S]*)/i)
  const src = insightBlock ? insightBlock[1] : section
  return src.split('\n').filter(l => /^[-*•]/.test(l.trim()))
    .map(l => l.replace(/^[-*•]\s*/, '').replace(/\*\*/g, '').trim()).filter(Boolean)
}

interface ChartSeries { label: string; data: { period: string; value: number }[] }
function parseChartData(content: string): ChartSeries[] {
  const section = extractSection(content, 'CHART[\\s\\S]{0,20}DATA')
  if (!section) return []
  const series: ChartSeries[] = []
  let current: ChartSeries | null = null
  for (const line of section.split('\n')) {
    const trimmed = line.trim()
    const headerM = trimmed.match(/^([A-Za-z][A-Za-z /]+):\s*$/)
    if (headerM) {
      if (current) series.push(current)
      current = { label: headerM[1].trim(), data: [] }
      continue
    }
    const dataM = trimmed.match(/^-\s*(\d{4}(?:-\d{2})?):\s*[₹]?([\d,]+\.?\d*)/)
    if (dataM && current) {
      current.data.push({ period: dataM[1], value: parseFloat(dataM[2].replace(/,/g, '')) || 0 })
    }
  }
  if (current) series.push(current)
  return series.filter(s => s.data.length > 0)
}

function parseFinalInsights(content: string): string[] {
  const section = extractSection(content, 'FINAL[\\s\\S]{0,20}INSIGHT')
  if (!section) return []
  return section.split('\n').filter(l => /^[-*•]/.test(l.trim()))
    .map(l => l.replace(/^[-*•]\s*/, '').replace(/\*\*/g, '').trim()).filter(Boolean)
}

function parseBehavioralShifts(content: string): { label: string; detail: string }[] {
  const section = extractSection(content, 'BEHAVIORAL[\\s\\S]{0,20}SHIFT')
  if (!section || isInsuff(section)) return []
  return extractBullets(section).filter(b => b.label || b.detail)
}

function parseAnomalyTimeline(content: string): string {
  const section = extractSection(content, 'ANOMALY[\\s\\S]{0,20}TIMELINE')
  if (!section || isInsuff(section)) return ''
  return section.replace(/\*\*/g, '').replace(/\n+/g, ' ').trim()
}

function parseCategoryAnalysis(content: string): string[] {
  const section = extractSection(content, 'CATEGORY[\\s\\S]{0,30}ANAL') || extractSection(content, 'TAX[\\s\\S]{0,20}PURPOSE')
  if (!section || isInsuff(section)) return []
  return extractBullets(section).map(b => (b.label ? `${b.label}: ${b.detail}` : b.detail)).filter(Boolean)
}

function ServiceTypeCard({ type, label, color, icon: Icon }: { type: string; label: string; color: string; icon: React.ElementType }) {
  return (
    <div className={`rounded-xl p-3.5 text-white bg-gradient-to-br ${color} shadow-sm flex items-start gap-3`}>
      <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <p className="text-[10px] font-black uppercase tracking-widest opacity-75 mb-0.5">Type</p>
        <p className="text-base font-black leading-tight">{type}</p>
        <p className="text-[11px] opacity-75 mt-0.5">{label}</p>
      </div>
    </div>
  )
}

function SectionCard({ icon: Icon, title, iconClass = 'text-muted-foreground', badge, children }: {
  icon: React.ElementType; title: string; iconClass?: string; badge?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border bg-card overflow-hidden shadow-sm">
      <div className="flex items-center gap-2.5 px-4 py-3 border-b bg-muted/30">
        <Icon className={`h-4 w-4 shrink-0 ${iconClass}`} />
        <h3 className="text-sm font-semibold">{title}</h3>
        {badge && <div className="ml-auto">{badge}</div>}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

function FieldRow({ name, example }: { name: string; example: string }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b last:border-0">
      <ChevronRight className="h-3.5 w-3.5 text-blue-500 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <span className="text-xs font-bold">{name}</span>
        {example && <span className="ml-2 text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">e.g. {example}</span>}
      </div>
    </div>
  )
}

function HBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="mb-2 last:mb-0">
      <div className="flex justify-between text-xs mb-1">
        <span className="font-medium tabular-nums">{label}</span>
        <span className="text-muted-foreground tabular-nums">{value} ({pct}%)</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

const USE_CASE_COLORS = [
  'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800/40',
  'bg-violet-50 dark:bg-violet-950/20 border-violet-200 dark:border-violet-800/40',
  'bg-teal-50 dark:bg-teal-950/20 border-teal-200 dark:border-teal-800/40',
  'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/40',
]
const USE_CASE_ICON_COLORS = ['text-blue-500', 'text-violet-500', 'text-teal-500', 'text-amber-500']
const USE_CASE_ICONS = [Activity, AlertTriangle, FileCode, Target]

export function TimelineAnalysisInsightViewer({ content }: TimelineAnalysisInsightViewerProps) {
  const data = useMemo(() => {
    const serviceTypes    = detectServiceTypes(content)
    const fields          = parseFields(content)
    const useCases        = parseUseCases(content)
    const nextSteps       = parseNextSteps(content)
    const example         = parseExample(content)
    const notes           = parseNotes(content)
    const observations    = parseObservations(content)
    const missingData     = parseMissingData(content)
    const conclusion      = parseConclusion(content)
    const imsInfo         = parseImsInfo(content)
    const frequency       = parseFrequencyTable(content)
    const entityRows      = parseEntityTable(content)
    const entityInsights  = parseEntityInsights(content)
    const chartSeries     = parseChartData(content)
    const finalInsights   = parseFinalInsights(content)
    const behavioralShifts = parseBehavioralShifts(content)
    const anomalyTimeline = parseAnomalyTimeline(content)
    const categoryLines   = parseCategoryAnalysis(content)

    const destTokens = extractCodeTokens(content)
      .filter(t => /^[A-Z]{2,}-[A-Z]{2,}$/.test(t) || /^[A-Z]{3,}$/.test(t))
      .filter((v, i, a) => a.indexOf(v) === i).slice(0, 10)

    const geoMatches = [...content.matchAll(/\d{1,3}\.\d+\/\d{1,3}\.\d+/g)]
    const geoExamples = [...new Set(geoMatches.map(m => m[0]))].slice(0, 4)

    const tsMatches = [...content.matchAll(/\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}/g)]
    const tsExamples = [...new Set(tsMatches.map(m => m[0]))].slice(0, 3)

    return {
      serviceTypes, fields, useCases, nextSteps, example, notes,
      destTokens, geoExamples, tsExamples,
      observations, missingData, conclusion, imsInfo,
      frequency, entityRows, entityInsights, chartSeries, finalInsights,
      behavioralShifts, anomalyTimeline, categoryLines,
    }
  }, [content])

  const freqMax = Math.max(...data.frequency.rows.map(r => r.count), 1)
  const freqColors = ['bg-blue-500','bg-indigo-500','bg-violet-500','bg-purple-500','bg-fuchsia-500']

  return (
    <div className="space-y-5 pb-4">

      {/* ── Hero banner ── */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-900 via-indigo-950 to-violet-950 text-white p-6 shadow-lg">
        <div className="absolute inset-0 opacity-5 pointer-events-none">
          <div className="absolute top-0 right-0 w-72 h-72 rounded-full bg-violet-400 blur-3xl" />
          <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-blue-400 blur-3xl" />
        </div>
        <div className="relative">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="h-4 w-4 text-violet-300" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-violet-300">Timeline Analysis</span>
          </div>
          <h2 className="text-2xl font-black text-white mb-1">Structured Data Report</h2>
          <p className="text-sm text-violet-200/70 mb-4">Multi-format analysis — Telecom / Financial / Compliance / Network</p>
          <div className="flex flex-wrap gap-2">
            {data.tsExamples.length > 0 && (
              <div className="flex items-center gap-1.5 bg-white/10 border border-white/20 rounded-full px-3 py-1">
                <Clock className="h-3 w-3 text-violet-300" />
                <span className="text-[10px] font-bold text-violet-200">{data.tsExamples[0]}</span>
              </div>
            )}
            {data.geoExamples.length > 0 && (
              <div className="flex items-center gap-1.5 bg-white/10 border border-white/20 rounded-full px-3 py-1">
                <MapPin className="h-3 w-3 text-rose-300" />
                <span className="text-[10px] font-bold text-rose-200">{data.geoExamples[0]}</span>
              </div>
            )}
            {data.frequency.highest && (
              <div className="flex items-center gap-1.5 bg-white/10 border border-white/20 rounded-full px-3 py-1">
                <TrendingUp className="h-3 w-3 text-emerald-300" />
                <span className="text-[10px] font-bold text-emerald-200">Peak: {data.frequency.highest}</span>
              </div>
            )}
            {data.destTokens.slice(0, 2).map((t, i) => (
              <div key={i} className="flex items-center gap-1.5 bg-white/10 border border-white/20 rounded-full px-3 py-1">
                <Signal className="h-3 w-3 text-teal-300" />
                <span className="text-[10px] font-bold text-teal-200">{t}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Service type cards ── */}
      {data.serviceTypes.length > 0 && (
        <div>
          <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-3 px-1">Event / Service Types</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {data.serviceTypes.map((s, i) => (
              <ServiceTypeCard key={i} type={s.type} label={s.label} color={s.color} icon={s.icon} />
            ))}
          </div>
        </div>
      )}

      {/* ── Frequency Analysis ── */}
      {data.frequency.rows.length > 0 && (
        <SectionCard icon={BarChart2} title="Frequency Analysis" iconClass="text-indigo-500"
          badge={data.frequency.pattern ? <Badge variant="secondary" className="text-[10px] font-bold">{data.frequency.pattern}</Badge> : undefined}>
          <div className="space-y-1.5 mb-3">
            {data.frequency.rows.map((r, i) => (
              <HBar key={i} label={r.period} value={r.count} max={freqMax} color={freqColors[i % freqColors.length]} />
            ))}
          </div>
          {(data.frequency.highest || data.frequency.lowest) && (
            <div className="flex gap-3 pt-3 border-t">
              {data.frequency.highest && (
                <div className="flex items-center gap-1.5 text-xs">
                  <TrendingUp className="h-3 w-3 text-emerald-500" />
                  <span className="text-muted-foreground">Highest:</span>
                  <span className="font-bold">{data.frequency.highest}</span>
                </div>
              )}
              {data.frequency.lowest && (
                <div className="flex items-center gap-1.5 text-xs">
                  <Activity className="h-3 w-3 text-rose-500" />
                  <span className="text-muted-foreground">Lowest:</span>
                  <span className="font-bold">{data.frequency.lowest}</span>
                </div>
              )}
            </div>
          )}
        </SectionCard>
      )}

      {/* ── Entity Analysis ── */}
      {data.entityRows.length > 0 && (
        <SectionCard icon={Users} title="Entity Analysis" iconClass="text-blue-500"
          badge={<Badge variant="secondary" className="text-[10px] font-bold">{data.entityRows.length} entities</Badge>}>
          <div className="overflow-x-auto -mx-4 -mb-4">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-muted/40 border-b">
                  {['Entity', 'Period', 'Count', 'Value'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left font-semibold text-muted-foreground whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.entityRows.map((row, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-2.5 font-medium">{row.entity}</td>
                    <td className="px-4 py-2.5 tabular-nums text-muted-foreground">{row.period}</td>
                    <td className="px-4 py-2.5 tabular-nums text-center font-bold">{row.count}</td>
                    <td className="px-4 py-2.5 tabular-nums text-emerald-600 dark:text-emerald-400 font-bold">
                      {row.value && !isInsuff(row.value) ? row.value : <span className="text-muted-foreground/40 italic text-[10px]">N/A</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.entityInsights.length > 0 && (
            <div className="mt-4 pt-3 border-t space-y-1.5">
              {data.entityInsights.map((ins, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                  <ChevronRight className="h-3 w-3 text-blue-400 shrink-0" />
                  <span>{ins}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {/* ── Behavioral Shifts + Anomaly Timeline ── */}
      {(data.behavioralShifts.length > 0 || data.anomalyTimeline) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {data.behavioralShifts.length > 0 && (
            <SectionCard icon={Activity} title="Behavioral Shifts" iconClass="text-violet-500">
              <div className="space-y-2">
                {data.behavioralShifts.map((b, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs p-2 rounded-lg bg-violet-50/50 dark:bg-violet-950/10 border border-violet-100 dark:border-violet-900/30">
                    <ChevronRight className="h-3 w-3 text-violet-500 shrink-0 mt-0.5" />
                    <span>{b.label ? <><span className="font-bold">{b.label}:</span> {b.detail}</> : b.detail}</span>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}
          {data.anomalyTimeline && (
            <SectionCard icon={AlertTriangle} title="Anomaly Timeline" iconClass="text-rose-500">
              <p className="text-xs text-muted-foreground leading-relaxed">{data.anomalyTimeline}</p>
            </SectionCard>
          )}
        </div>
      )}

      {/* ── Chart Data ── */}
      {data.chartSeries.length > 0 && (
        <SectionCard icon={BarChart2} title="Chart Data — Period Breakdown" iconClass="text-indigo-500">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {data.chartSeries.map((series, si) => {
              const maxVal = Math.max(...series.data.map(d => d.value), 1)
              const seriesColors = ['bg-blue-500','bg-emerald-500','bg-rose-500','bg-amber-500','bg-violet-500']
              const color = seriesColors[si % seriesColors.length]
              const isCount = /volume|anomal|count/i.test(series.label)
              return (
                <div key={si}>
                  <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">{series.label}</p>
                  <div className="space-y-2">
                    {series.data.map((d, di) => {
                      const pct = Math.round((d.value / maxVal) * 100)
                      return (
                        <div key={di}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="font-medium tabular-nums">{d.period}</span>
                            <span className="text-muted-foreground tabular-nums">
                              {isCount ? d.value : `₹${d.value.toLocaleString('en-IN')}`}
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-muted overflow-hidden">
                            <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </SectionCard>
      )}

      {/* ── Category Analysis ── */}
      {data.categoryLines.length > 0 && (
        <SectionCard icon={Target} title="Category / Tax / Purpose Analysis" iconClass="text-amber-500">
          <div className="space-y-2">
            {data.categoryLines.map((line, i) => (
              <div key={i} className="flex items-start gap-2 text-xs p-2 rounded-lg bg-amber-50/50 dark:bg-amber-950/10 border border-amber-100 dark:border-amber-900/30">
                <ChevronRight className="h-3 w-3 text-amber-500 shrink-0 mt-0.5" />
                <span>{line}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Final Insights ── */}
      {data.finalInsights.length > 0 && (
        <SectionCard icon={TrendingUp} title="Final Insights" iconClass="text-emerald-500">
          <div className="space-y-2">
            {data.finalInsights.map((line, i) => (
              <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/10 border border-emerald-100 dark:border-emerald-900/30">
                <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-[10px] font-black shrink-0 mt-0.5">{i + 1}</span>
                <span className="text-xs leading-relaxed">{line}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Data structure fields ── */}
      {data.fields.length > 0 && (
        <SectionCard icon={FileCode} title="Data Structure — Field Reference" iconClass="text-blue-500"
          badge={<Badge variant="secondary" className="text-[10px] font-bold">{data.fields.length} fields</Badge>}>
          <div className="divide-y">
            {data.fields.map((f, i) => <FieldRow key={i} name={f.name} example={f.example} />)}
          </div>
        </SectionCard>
      )}

      {/* ── Geolocation + Timestamps ── */}
      {(data.geoExamples.length > 0 || data.tsExamples.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {data.geoExamples.length > 0 && (
            <SectionCard icon={MapPin} title="Geolocation Samples" iconClass="text-rose-500">
              <div className="flex flex-wrap gap-2">
                {data.geoExamples.map((g, i) => (
                  <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40">
                    <MapPin className="h-3 w-3 text-rose-500 shrink-0" />
                    <span className="font-mono text-xs text-rose-700 dark:text-rose-300">{g}</span>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}
          {data.tsExamples.length > 0 && (
            <SectionCard icon={Clock} title="Timestamp Samples" iconClass="text-indigo-500">
              <div className="flex flex-col gap-2">
                {data.tsExamples.map((ts, i) => (
                  <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/40">
                    <Clock className="h-3 w-3 text-indigo-500 shrink-0" />
                    <span className="font-mono text-xs text-indigo-700 dark:text-indigo-300">{ts}</span>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}
        </div>
      )}

      {/* ── Destination / Operator tokens ── */}
      {data.destTokens.length > 0 && (
        <SectionCard icon={Signal} title="Detected Networks / Destinations" iconClass="text-teal-500">
          <div className="flex flex-wrap gap-2">
            {data.destTokens.map((t, i) => (
              <span key={i} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-teal-50 dark:bg-teal-950/20 border border-teal-200 dark:border-teal-800/40 text-xs font-bold text-teal-700 dark:text-teal-300">
                <Signal className="h-3 w-3" />{t}
              </span>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Use cases ── */}
      {data.useCases.length > 0 && (
        <SectionCard icon={Lightbulb} title="Potential Use Cases" iconClass="text-amber-500">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {data.useCases.map((uc, i) => {
              const Icon = USE_CASE_ICONS[i % USE_CASE_ICONS.length]
              return (
                <div key={i} className={`rounded-xl border p-3.5 ${USE_CASE_COLORS[i % USE_CASE_COLORS.length]}`}>
                  <div className="flex items-center gap-2 mb-1.5">
                    <Icon className={`h-3.5 w-3.5 shrink-0 ${USE_CASE_ICON_COLORS[i % USE_CASE_ICON_COLORS.length]}`} />
                    <p className="text-xs font-bold">{uc.title}</p>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{uc.desc}</p>
                </div>
              )
            })}
          </div>
        </SectionCard>
      )}

      {/* ── Next steps ── */}
      {data.nextSteps.length > 0 && (
        <SectionCard icon={Users} title="Next Steps" iconClass="text-emerald-500">
          <div className="space-y-2">
            {data.nextSteps.map((step, i) => (
              <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/10 border border-emerald-100 dark:border-emerald-900/30">
                <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-[10px] font-black shrink-0 mt-0.5">{i + 1}</span>
                <span className="text-xs leading-relaxed">{step}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Example ── */}
      {data.example && (
        <SectionCard icon={FileCode} title="Example Request &amp; Response" iconClass="text-blue-500">
          {data.example.request && (
            <div className="mb-3">
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-1.5">Request</p>
              <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800/40">
                <ChevronRight className="h-3.5 w-3.5 text-blue-500 shrink-0 mt-0.5" />
                <p className="text-xs text-blue-800 dark:text-blue-200 italic">&quot;{data.example.request}&quot;</p>
              </div>
            </div>
          )}
          {data.example.response && (
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-1.5">Response</p>
              <pre className="text-[10px] font-mono bg-slate-900 text-emerald-400 p-3 rounded-lg overflow-x-auto leading-relaxed">{data.example.response}</pre>
            </div>
          )}
        </SectionCard>
      )}

      {/* ── Notes ── */}
      {data.notes.length > 0 && (
        <SectionCard icon={AlertTriangle} title="Notes &amp; Considerations" iconClass="text-amber-500">
          <div className="space-y-2">
            {data.notes.map((note, i) => (
              <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/40">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
                <span className="text-xs leading-relaxed">{note}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Notable Observations ── */}
      {data.observations.length > 0 && (
        <SectionCard icon={Activity} title="Notable Observations" iconClass="text-blue-500">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {data.observations.map((obs, i) => (
              <div key={i} className="rounded-xl border p-3.5 bg-blue-50/50 dark:bg-blue-950/10 border-blue-200 dark:border-blue-800/40">
                {obs.title && <p className="text-xs font-bold text-blue-700 dark:text-blue-300 mb-1">{obs.title}</p>}
                <p className="text-xs text-muted-foreground leading-relaxed">{obs.detail}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── IMS / VoLTE ── */}
      {data.imsInfo.length > 0 && (
        <SectionCard icon={Signal} title="IMS / VoLTE Services" iconClass="text-indigo-500">
          <div className="space-y-2">
            {data.imsInfo.map((line, i) => (
              <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/40">
                <Signal className="h-3.5 w-3.5 text-indigo-500 shrink-0 mt-0.5" />
                <span className="text-xs leading-relaxed">{line}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Missing data ── */}
      {data.missingData.length > 0 && (
        <SectionCard icon={AlertTriangle} title="Missing / Placeholder Data" iconClass="text-rose-500">
          <div className="space-y-2">
            {data.missingData.map((item, i) => (
              <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40">
                <AlertTriangle className="h-3.5 w-3.5 text-rose-500 shrink-0 mt-0.5" />
                <span className="text-xs leading-relaxed">{item}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Conclusion ── */}
      {data.conclusion && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900/60 dark:to-slate-800/40 p-5 shadow-sm">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
              <Target className="h-4 w-4 text-slate-600 dark:text-slate-300" />
            </div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Conclusion</h3>
          </div>
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{data.conclusion}</p>
        </div>
      )}

    </div>
  )
}
