'use client'

import { useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import {
  User, AlertTriangle, Shield, MapPin, Calendar,
  Users, FileText, Eye, Target, ChevronRight,
  BookOpen, Network, Smartphone, TrendingUp, Lock,
  Search, Crosshair, Brain, Activity,
} from 'lucide-react'

interface InvestigativeProfileInsightViewerProps {
  content: string
}

export function isInvestigativeProfileInsight(insightType: string): boolean {
  return insightType.toLowerCase().includes('investigat')
}

// ── helpers ───────────────────────────────────────────────────────────────────

function clean(val: string): string {
  return val.replace(/\*\*/g, '').replace(/`/g, '').trim()
}

function isInsuff(val: string): boolean {
  const v = val.toLowerCase().trim()
  return !v || ['insufficient data', 'unknown', 'not available', '---', 'n/a', 'not provided'].some(s => v === s || v.includes(s))
}

// Extract a ## or ### section by heading keyword, returns { heading, body }
function extractSection(content: string, keyword: string): { heading: string; body: string } {
  const re = new RegExp(
    `(#{1,3})\\s+(?:\\d+\\.?\\s*)?([^\\n]*${keyword}[^\\n]*)\\n([\\s\\S]*?)(?=\\n#{1,3}\\s|$)`,
    'i'
  )
  const m = content.match(re)
  if (!m) return { heading: '', body: '' }
  return { heading: clean(m[2]), body: m[3] }
}

// Get all top-level sections from markdown
interface Section { heading: string; level: number; body: string }
function getAllSections(content: string): Section[] {
  const sections: Section[] = []
  const re = /^(#{1,3})\s+(.+)$/gm
  let match: RegExpExecArray | null
  const indices: { idx: number; level: number; heading: string }[] = []
  while ((match = re.exec(content)) !== null) {
    indices.push({ idx: match.index, level: match[1].length, heading: clean(match[2]) })
  }
  for (let i = 0; i < indices.length; i++) {
    const start = content.indexOf('\n', indices[i].idx) + 1
    const end = i + 1 < indices.length ? indices[i + 1].idx : content.length
    sections.push({ heading: indices[i].heading, level: indices[i].level, body: content.slice(start, end).trim() })
  }
  return sections
}

// Extract bullet lines from body text
function extractBullets(body: string): string[] {
  return body.split('\n')
    .filter(l => /^[-*•]/.test(l.trim()))
    .map(l => clean(l.replace(/^[-*•]\s*/, '')))
    .filter(l => l && !isInsuff(l))
}

// Extract sub-sections (### inside a section body)
function extractSubSections(body: string): { title: string; lines: string[] }[] {
  const result: { title: string; lines: string[] }[] = []
  const re = /\*\*([^*]+)\*\*[:\s]*([\s\S]*?)(?=\*\*[^*]+\*\*[:\s]|$)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(body)) !== null) {
    const title = m[1].trim()
    const lines = m[2].split('\n')
      .map(l => clean(l.replace(/^[-*•]\s*/, '')))
      .filter(l => l && !isInsuff(l))
    if (lines.length > 0) result.push({ title, lines })
  }
  return result
}

// Parse markdown table rows
function parseMarkdownTable(body: string): { headers: string[]; rows: string[][] } {
  const lines = body.split('\n').filter(l => l.includes('|'))
  const headers: string[] = []
  const rows: string[][] = []
  for (const line of lines) {
    const cells = line.split('|').map(c => clean(c)).filter(Boolean)
    if (cells.every(c => /^[-:]+$/.test(c))) continue
    if (headers.length === 0) { headers.push(...cells); continue }
    rows.push(cells)
  }
  return { headers, rows }
}

// Extract inline value after a label - handles bold labels and multi-word label variants
function extractInline(content: string, label: string): string {
  const re = new RegExp(`(?:^|\\n)[-*•]?\\s*\\*?\\*?${label}\\*?\\*?[:\\s]+([^\\n]+)`, 'i')
  const m = content.match(re)
  return m ? clean(m[1]) : ''
}

// Extract subject name - handles many label variants the LLM uses
function extractSubjectName(content: string): string {
  const patterns = [
    /\*\*Full\s+Name\s*[/\\|]?\s*Identifier\*\*[:\s]+([^\n]+)/i,
    /\*\*Full\s+Name\*\*[:\s]+([^\n]+)/i,
    /\*\*Name\*\*[:\s]+([^\n]+)/i,
    /\*\*Subject\s+Name\*\*[:\s]+([^\n]+)/i,
    /\*\*Subject\*\*[:\s]+([^\n]+)/i,
    /Full\s+Name\s*[/\\|]?\s*Identifier[:\s]+([^\n]+)/i,
    /Full\s+Name[:\s]+([^\n]+)/i,
    /Subject\s+Name[:\s]+([^\n]+)/i,
    /^[-*•]\s*Name[:\s]+([^\n]+)/im,
  ]
  for (const re of patterns) {
    const m = content.match(re)
    if (m) {
      const val = clean(m[1])
      if (val && !isInsuff(val)) return val
    }
  }
  return ''
}

// ── Section icon map ──────────────────────────────────────────────────────────

const SECTION_ICONS: { keywords: string[]; icon: React.ElementType; color: string }[] = [
  { keywords: ['subject', 'identification', 'bio', 'personal'], icon: User, color: 'text-blue-500' },
  { keywords: ['physical'], icon: Eye, color: 'text-violet-500' },
  { keywords: ['modus', 'operandi', 'behavioral', 'behaviour'], icon: TrendingUp, color: 'text-orange-500' },
  { keywords: ['chronological', 'case', 'history', 'criminal record'], icon: FileText, color: 'text-rose-500' },
  { keywords: ['organizational', 'network', 'associate', 'gang'], icon: Network, color: 'text-teal-500' },
  { keywords: ['digital', 'operational', 'evasion', 'footprint'], icon: Smartphone, color: 'text-indigo-500' },
  { keywords: ['risk', 'threat', 'assessment'], icon: Shield, color: 'text-rose-600' },
  { keywords: ['actionable', 'directive', 'field'], icon: Target, color: 'text-red-500' },
  { keywords: ['gap', 'unknown', 'missing', 'confidence'], icon: AlertTriangle, color: 'text-amber-500' },
  { keywords: ['key insight', 'insight', 'finding'], icon: Brain, color: 'text-purple-500' },
  { keywords: ['follow', 'surveillance', 'next step'], icon: Search, color: 'text-cyan-500' },
  { keywords: ['network analysis'], icon: Network, color: 'text-teal-500' },
  { keywords: ['violent', 'incident', 'activity'], icon: Activity, color: 'text-rose-500' },
  { keywords: ['location', 'address', 'place'], icon: MapPin, color: 'text-green-500' },
  { keywords: ['education', 'academic'], icon: BookOpen, color: 'text-blue-400' },
  { keywords: ['family', 'relative'], icon: Users, color: 'text-teal-400' },
  { keywords: ['point', 'follow-up'], icon: Crosshair, color: 'text-red-400' },
]

function getSectionIcon(heading: string): { icon: React.ElementType; color: string } {
  const h = heading.toLowerCase()
  for (const entry of SECTION_ICONS) {
    if (entry.keywords.some(k => h.includes(k))) return { icon: entry.icon, color: entry.color }
  }
  return { icon: ChevronRight, color: 'text-muted-foreground' }
}

// ── UI primitives ─────────────────────────────────────────────────────────────

function SectionCard({ icon: Icon, title, iconColor, badge, children }: {
  icon: React.ElementType; title: string; iconColor: string
  badge?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border bg-card overflow-hidden shadow-sm">
      <div className="flex items-center gap-2.5 px-4 py-3 border-b bg-muted/30">
        <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} />
        <h3 className="text-sm font-semibold">{title}</h3>
        {badge && <div className="ml-auto">{badge}</div>}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  const empty = !value || isInsuff(value)
  return (
    <div className="flex items-start gap-3 py-2 border-b last:border-0">
      <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground w-28 shrink-0 mt-0.5">{label}</span>
      {empty
        ? <span className="text-[10px] text-muted-foreground/40 italic">—</span>
        : <span className="text-xs font-medium flex-1">{value}</span>}
    </div>
  )
}

function BulletList({ items, color = 'text-muted-foreground' }: { items: string[]; color?: string }) {
  return (
    <div className="space-y-1.5">
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-2 text-xs">
          <ChevronRight className={`h-3 w-3 shrink-0 mt-0.5 ${color}`} />
          <span className="leading-relaxed">{item}</span>
        </div>
      ))}
    </div>
  )
}

// Render a generic section body - handles bullets, sub-sections, tables, plain text
function GenericSectionBody({ body }: { body: string }) {
  const bullets = extractBullets(body)
  const table = parseMarkdownTable(body)
  const subSections = extractSubSections(body)
  const plainLines = body.split('\n')
    .filter(l => l.trim() && !/^#{1,3}/.test(l.trim()) && !/^\|/.test(l.trim()) && !/^[-*•]/.test(l.trim()))
    .map(l => clean(l))
    .filter(l => l && !isInsuff(l))

  // Table rendering
  if (table.headers.length >= 2 && table.rows.length > 0) {
    return (
      <div className="overflow-x-auto -mx-4 -mb-4">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted/40 border-b">
              {table.headers.map((h, i) => (
                <th key={i} className="px-4 py-2.5 text-left font-semibold text-muted-foreground whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, i) => (
              <tr key={i} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-2.5 text-xs">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // Sub-sections with bullets
  if (subSections.length > 0) {
    return (
      <div className="space-y-3">
        {subSections.map((sub, i) => (
          <div key={i}>
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-1.5">{sub.title}</p>
            <BulletList items={sub.lines} />
          </div>
        ))}
        {bullets.length > 0 && !subSections.some(s => s.lines.join(' ').includes(bullets[0])) && (
          <BulletList items={bullets} />
        )}
      </div>
    )
  }

  // Bullet list
  if (bullets.length > 0) {
    return <BulletList items={bullets} />
  }

  // Plain text paragraphs
  if (plainLines.length > 0) {
    return (
      <div className="space-y-1.5">
        {plainLines.map((line, i) => (
          <p key={i} className="text-xs text-muted-foreground leading-relaxed">{line}</p>
        ))}
      </div>
    )
  }

  return <p className="text-xs text-muted-foreground/40 italic">No data available.</p>
}

// ── main viewer ───────────────────────────────────────────────────────────────

export function InvestigativeProfileInsightViewer({ content }: InvestigativeProfileInsightViewerProps) {
  // Pre-process: unescape JSON-encoded string (\\n -> newline, \\" -> ")
  const processedContent = useMemo(() => {
    let c = content
    // If content looks like an escaped JSON string, unescape it
    if (c.includes('\\n') || c.includes('\\"')) {
      try {
        // Try parsing as JSON string value
        const unescaped = JSON.parse('"' + c.replace(/^"|"$/g, '').replace(/\n/g, '\\n') + '"')
        if (typeof unescaped === 'string' && unescaped.length > 10) c = unescaped
      } catch {
        // Manual unescape fallback
        c = c
          .replace(/\\n/g, '\n')
          .replace(/\\t/g, '\t')
          .replace(/\\"/g, '"')
          .replace(/\\\\/g, '\\')
      }
    }
    return c
  }, [content])
  const parsed = useMemo(() => {
    const sections = getAllSections(processedContent)
    // Use broad name extraction to handle all LLM label variants
    const name        = extractSubjectName(processedContent)
                     || extractInline(processedContent, 'Name')
                     || extractInline(processedContent, 'Subject')
    const prisonerId  = processedContent.match(/Prisoner\s*ID[:\s#]+(\w+)/i)?.[1] ?? ''
    const dob         = extractInline(processedContent, 'DOB')
                     || extractInline(processedContent, 'Date of Birth')
                     || extractInline(processedContent, 'Date\\s+of\\s+Birth')
    const address     = extractInline(processedContent, 'Last known address')
                     || extractInline(processedContent, 'Address')
                     || extractInline(processedContent, 'Current\\s+Address')
    const education   = extractInline(processedContent, 'Education')
                     || extractInline(processedContent, 'Academic')
    const threatLevel = extractInline(processedContent, 'Threat Level')
                     || (processedContent.match(/Threat\s+Level[:\s*]+([^\n]+)/i)?.[1]?.replace(/\*\*/g, '').trim() ?? '')
    const confidence  = extractInline(processedContent, 'Confidence Level')
                     || extractInline(processedContent, 'Overall Confidence')
                     || extractInline(processedContent, 'Confidence')
    return { sections, name, prisonerId, dob, address, education, threatLevel, confidence }
  }, [processedContent])

  const { sections, name, prisonerId, dob, address, education, threatLevel, confidence } = parsed

  const threatColor = threatLevel.toLowerCase().includes('low')
    ? 'from-emerald-600 to-emerald-800'
    : threatLevel.toLowerCase().includes('high')
      ? 'from-rose-600 to-rose-800'
      : 'from-amber-600 to-amber-800'

  // Sections to skip from generic rendering (shown in hero)
  const HERO_KEYWORDS = ['subject identification', 'bio']

  return (
    <div className="space-y-5 pb-4">

      {/* ── Hero banner ── */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-white shadow-xl">
        {/* Decorative background elements */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-10 -right-10 w-72 h-72 rounded-full bg-rose-500/10 blur-3xl" />
          <div className="absolute -bottom-10 -left-10 w-56 h-56 rounded-full bg-blue-500/10 blur-3xl" />
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        </div>

        {/* Top accent bar */}
        <div className="h-1 w-full bg-gradient-to-r from-rose-500 via-orange-400 to-amber-500" />

        <div className="relative p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-0">
              {/* Label */}
              <div className="flex items-center gap-2 mb-4">
                <div className="flex items-center gap-1.5 bg-rose-500/20 border border-rose-500/30 rounded-full px-3 py-1">
                  <Shield className="h-3 w-3 text-rose-400" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-rose-300">Investigative Profile</span>
                </div>
              </div>

              {/* Subject identity */}
              <div className="flex items-center gap-4 mb-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-slate-700 to-slate-600 border border-white/10 flex items-center justify-center shrink-0 shadow-lg">
                  <User className="h-7 w-7 text-slate-200" />
                </div>
                <div>
                  <h2 className="text-2xl font-black text-white tracking-tight leading-tight">
                    {name || 'UNKNOWN SUBJECT'}
                  </h2>
                  {prisonerId && (
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wide">Prisoner ID:</span>
                      <span className="text-xs font-bold text-amber-300 font-mono">{prisonerId}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Meta chips */}
              <div className="flex flex-wrap gap-2">
                {dob && !isInsuff(dob) && (
                  <span className="flex items-center gap-1.5 text-[11px] bg-white/8 border border-white/15 rounded-lg px-3 py-1.5 text-slate-200">
                    <Calendar className="h-3 w-3 text-blue-400 shrink-0" />
                    <span className="font-medium">{dob}</span>
                  </span>
                )}
                {education && !isInsuff(education) && (
                  <span className="flex items-center gap-1.5 text-[11px] bg-white/8 border border-white/15 rounded-lg px-3 py-1.5 text-slate-200">
                    <BookOpen className="h-3 w-3 text-green-400 shrink-0" />
                    <span className="font-medium">{education}</span>
                  </span>
                )}
                {address && !isInsuff(address) && (
                  <span className="flex items-center gap-1.5 text-[11px] bg-white/8 border border-white/15 rounded-lg px-3 py-1.5 text-slate-200">
                    <MapPin className="h-3 w-3 text-rose-400 shrink-0" />
                    <span className="font-medium truncate max-w-[200px]">{address}</span>
                  </span>
                )}
              </div>
            </div>

            {/* Threat level card */}
            {threatLevel && !isInsuff(threatLevel) && (
              <div className={`rounded-xl p-4 text-white bg-gradient-to-br ${threatColor} shadow-lg text-center min-w-[140px] border border-white/10`}>
                <div className="flex items-center justify-center gap-1 mb-2">
                  <AlertTriangle className="h-3.5 w-3.5 opacity-80" />
                  <p className="text-[9px] font-black uppercase tracking-widest opacity-80">Threat Level</p>
                </div>
                <p className="text-base font-black leading-tight">{threatLevel}</p>
                {confidence && !isInsuff(confidence) && (
                  <div className="mt-2 pt-2 border-t border-white/20">
                    <p className="text-[9px] opacity-70 uppercase tracking-wide">Confidence</p>
                    <p className="text-[11px] font-bold opacity-90">{confidence}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Dynamic sections ── */}
      {sections
        .filter(s => !HERO_KEYWORDS.some(k => s.heading.toLowerCase().includes(k)))
        .filter(s => s.body.trim().length > 10)
        .map((section, i) => {
          const { icon, color } = getSectionIcon(section.heading)

          // Special: case history table
          const isCase = /chronological|case history|criminal record/i.test(section.heading)
          const table = parseMarkdownTable(section.body)
          const hasCaseTable = isCase && table.headers.length >= 2 && table.rows.length > 0

          // Special: associates
          const isAssoc = /associate|network|organizational/i.test(section.heading)
          const bullets = extractBullets(section.body)

          // Badge for case count
          const badge = hasCaseTable
            ? <Badge variant="destructive" className="text-[10px] font-bold">{table.rows.length} cases</Badge>
            : isAssoc && bullets.length > 0
              ? <Badge variant="secondary" className="text-[10px] font-bold">{bullets.length}</Badge>
              : undefined

          return (
            <SectionCard key={i} icon={icon} title={section.heading} iconColor={color} badge={badge}>
              <GenericSectionBody body={section.body} />
            </SectionCard>
          )
        })}

    </div>
  )
}
