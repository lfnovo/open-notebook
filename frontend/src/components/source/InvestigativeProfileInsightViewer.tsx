'use client'

import { useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import {
  User, AlertTriangle, Shield, MapPin, Calendar,
  Users, FileText, Eye, Target, ChevronRight,
  BookOpen, Network, Smartphone, TrendingUp, Lock,
} from 'lucide-react'

interface InvestigativeProfileInsightViewerProps {
  content: string
}

// ── detector ──────────────────────────────────────────────────────────────────

export function isInvestigativeProfileInsight(insightType: string): boolean {
  return insightType.toLowerCase().includes('investigat')
}

// ── helpers ───────────────────────────────────────────────────────────────────

const INSUFF = ['insufficient data', 'unknown', 'not available', '---', 'n/a', '']

function clean(val: string): string {
  return val.replace(/\*\*/g, '').replace(/`/g, '').trim()
}

function isInsuff(val: string): boolean {
  return INSUFF.some(s => val.toLowerCase().trim() === s || val.toLowerCase().includes('insufficient data'))
}

// Parse a markdown table section into key→value map
function parseMarkdownTable(section: string): Record<string, string> {
  const map: Record<string, string> = {}
  for (const line of section.split('\n')) {
    if (!line.includes('|')) continue
    const cells = line.split('|').map(c => clean(c)).filter(Boolean)
    if (cells.length < 2) continue
    if (/^[-:]+$/.test(cells[0])) continue          // separator row
    if (/^field$/i.test(cells[0])) continue          // header row
    const key = cells[0].toLowerCase().replace(/[^a-z0-9]/g, '_')
    const val = cells[1]
    if (key && val) map[key] = val
  }
  return map
}

// Extract a ## section by heading keyword
function extractSection(content: string, keyword: string): string {
  const re = new RegExp(
    `##\\s+\\d*\\.?\\s*${keyword}[^\\n]*\\n([\\s\\S]*?)(?=\\n##\\s|$)`,
    'i'
  )
  const m = content.match(re)
  return m ? m[1] : ''
}

// Parse case history table rows
interface CaseRow { date: string; location: string; sections: string; status: string }
function parseCaseHistory(content: string): CaseRow[] {
  const section = extractSection(content, 'Chronological')
  const rows: CaseRow[] = []
  for (const line of section.split('\n')) {
    if (!line.includes('|')) continue
    const cells = line.split('|').map(c => clean(c)).filter(Boolean)
    if (cells.length < 4) continue
    if (/^[-:]+$/.test(cells[0])) continue
    if (/date|location|legal/i.test(cells[0])) continue
    if (!/\d/.test(cells[0])) continue
    rows.push({ date: cells[0], location: cells[1], sections: cells[2], status: cells[3] })
  }
  return rows
}

// Extract bullet lines from a section (strips ** and leading markers)
function extractBullets(section: string): string[] {
  return section.split('\n')
    .filter(l => /^[-*•]/.test(l.trim()))
    .map(l => clean(l.replace(/^[-*•]\s*/, '')))
    .filter(l => l && !isInsuff(l))
}

// Extract numbered list items
function extractNumbered(section: string): { num: string; text: string }[] {
  return section.split('\n')
    .filter(l => /^\d+\./.test(l.trim()))
    .map(l => {
      const m = l.trim().match(/^(\d+)\.\s*(.+)/)
      return m ? { num: m[1], text: clean(m[2]) } : null
    })
    .filter(Boolean) as { num: string; text: string }[]
}

// Parse associates from section 4
interface Associate { name: string; relation: string }
function parseAssociates(content: string): Associate[] {
  const section = extractSection(content, 'Organizational')
  const results: Associate[] = []
  // Match "NAME (Relation)" pattern
  const re1 = /([A-Z][A-Z\s]{2,})\s*\(([^)]+)\)/g
  let m: RegExpExecArray | null
  while ((m = re1.exec(section)) !== null) {
    const name = m[1].trim()
    const rel  = m[2].trim()
    if (!isInsuff(name) && !results.find(r => r.name === name)) {
      results.push({ name, relation: rel })
    }
  }
  // Match "Relation: NAME" pattern
  const re2 = /(Father|Mother|Spouse|Co-Brother|Brother|Sister|Friend)[:\s]+([A-Z][A-Za-z\s]+?)(?:[,;.\n]|$)/g
  while ((m = re2.exec(section)) !== null) {
    const rel  = m[1].trim()
    const name = m[2].trim()
    if (!isInsuff(name) && !results.find(r => r.name === name)) {
      results.push({ name, relation: rel })
    }
  }
  return results.slice(0, 8)
}

// Parse actionable directives (ALL-CAPS label: detail)
interface Directive { title: string; detail: string }
function parseDirectives(content: string): Directive[] {
  const section = extractSection(content, 'Actionable')
  return section.split('\n')
    .filter(l => /^[A-Z\s]{4,}:/.test(l.trim()))
    .map(l => {
      const idx = l.indexOf(':')
      return { title: clean(l.slice(0, idx)), detail: clean(l.slice(idx + 1)) }
    })
    .filter(d => d.title && d.detail)
}

// ── UI primitives ─────────────────────────────────────────────────────────────

function SectionCard({ icon: Icon, title, iconClass = 'text-muted-foreground', badge, children }: {
  icon: React.ElementType; title: string; iconClass?: string
  badge?: React.ReactNode; children: React.ReactNode
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

function InfoRow({ label, value }: { label: string; value: string }) {
  const empty = !value || isInsuff(value)
  return (
    <div className="flex items-start gap-3 py-2 border-b last:border-0">
      <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground w-28 shrink-0 mt-0.5">{label}</span>
      {empty
        ? <span className="text-[10px] text-muted-foreground/40 italic">Insufficient Data</span>
        : <span className="text-xs font-medium flex-1">{value}</span>}
    </div>
  )
}

const DIRECTIVE_COLORS = [
  'border-blue-200 dark:border-blue-800/40 bg-blue-50 dark:bg-blue-950/20',
  'border-rose-200 dark:border-rose-800/40 bg-rose-50 dark:bg-rose-950/20',
  'border-violet-200 dark:border-violet-800/40 bg-violet-50 dark:bg-violet-950/20',
  'border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-950/20',
]
const DIRECTIVE_ICON_COLORS = ['text-blue-500', 'text-rose-500', 'text-violet-500', 'text-amber-500']

// ── main viewer ───────────────────────────────────────────────────────────────

export function InvestigativeProfileInsightViewer({ content }: InvestigativeProfileInsightViewerProps) {
  const data = useMemo(() => {
    // ── Section 1: Bio data table ──
    const bioSection = extractSection(content, 'Subject Identification')
    const bio = parseMarkdownTable(bioSection)

    const name       = bio['name']       || ''
    const dob        = bio['dob']        || ''
    const parentage  = bio['parentage']  || ''
    const education  = bio['education']  || ''
    const aliases    = bio['aliases']    || ''
    const habits     = bio['habits']     || ''
    const contact    = bio['contact']    || ''
    const physical   = bio['physical_identification'] || bio['physical_id'] || ''

    // Extract prisoner ID from title
    const prisonerId = content.match(/Prisoner\s*ID[:\s#]+(\d+)/i)?.[1] ?? ''

    // Physical sub-fields from the Physical Identification row value
    const physRaw = bioSection + '\n' + content
    const idMark    = physRaw.match(/ID\s*Mark[:\s]+([^\n|;]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''
    const scars     = physRaw.match(/Scars\/Tattoos[:\s]+([^\n|;]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''
    const buildVal  = physRaw.match(/Build[:\s]+([^\n|;]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''
    const heightVal = physRaw.match(/Height[:\s]+([^\n|;]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''
    const complexion = physRaw.match(/Complexion[:\s]+([^\n|;]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''
    const grooming  = physRaw.match(/Grooming[:\s]+([^\n|;]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''

    // ── Section 2: Modus Operandi ──
    const moSection  = extractSection(content, 'Modus Operandi')
    const moTable    = parseMarkdownTable(moSection)
    const moLines    = extractBullets(moSection)
    const weapons    = moTable['weapons_preference'] || moTable['weapons'] || ''
    const violence   = moTable['violence_threshold'] || moTable['violence'] || ''
    const environment = moTable['preferred_environment'] || moTable['environment'] || ''

    // ── Section 3: Case history ──
    const caseRows = parseCaseHistory(content)
    const severitySection = extractSection(content, 'Chronological')
    const severityLines = severitySection.split('\n')
      .filter(l => l.trim().length > 20 && !/^\|/.test(l.trim()) && !/^#+/.test(l.trim()))
      .map(l => clean(l))
      .filter(l => l && !isInsuff(l))
      .slice(0, 3)

    // ── Section 4: Associates ──
    const associates = parseAssociates(content)
    const address = content.match(/(?:Last\s*known\s*address|address)[:\s]+([^\n.(]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''

    // ── Section 5: Digital evasion ──
    const digitalSection = extractSection(content, 'Digital')
    const digitalLines   = extractBullets(digitalSection)

    // ── Section 6: Risk assessment ──
    const riskSection  = extractSection(content, 'Risk')
    const threatLevel  = content.match(/Threat\s*Level[:\s]+([^\n(]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''
    const confidence   = content.match(/Overall\s*Confidence\s*Level[:\s]+([^\n]+)/i)?.[1]?.trim().replace(/\*\*/g, '') ?? ''
    const riskLines    = extractBullets(riskSection)

    // ── Section 7: Directives ──
    const directives = parseDirectives(content)

    // ── Section 8: Intelligence gaps ──
    const gapSection = extractSection(content, 'Intelligence Gaps')
    const gaps = extractBullets(gapSection)
    const missingItems = gapSection.split('\n')
      .filter(l => l.trim().length > 5 && !/^#+/.test(l.trim()) && !/^\|/.test(l.trim()))
      .map(l => clean(l.replace(/^[-*•\d.]+\s*/, '')))
      .filter(l => l && !isInsuff(l))
      .slice(0, 6)

    return {
      name, prisonerId, dob, parentage, education, aliases, habits, contact, physical,
      idMark, scars, buildVal, heightVal, complexion, grooming,
      weapons, violence, environment, moLines,
      caseRows, severityLines,
      associates, address,
      digitalLines,
      threatLevel, confidence, riskLines,
      directives,
      gaps, missingItems,
    }
  }, [content])

  const threatColor = data.threatLevel.toLowerCase().includes('low')
    ? 'from-emerald-600 to-emerald-800'
    : data.threatLevel.toLowerCase().includes('high')
      ? 'from-rose-600 to-rose-800'
      : 'from-amber-600 to-amber-800'

  return (
    <div className="space-y-5 pb-4">

      {/* ── Hero banner ── */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6 shadow-lg">
        <div className="absolute inset-0 opacity-5 pointer-events-none">
          <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-rose-400 blur-3xl" />
          <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-slate-400 blur-3xl" />
        </div>
        <div className="relative flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Shield className="h-4 w-4 text-slate-400" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Investigative Profile</span>
            </div>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 rounded-xl bg-slate-700 border border-slate-600 flex items-center justify-center shrink-0">
                <User className="h-6 w-6 text-slate-300" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white">{data.name || 'UNKNOWN'}</h2>
                {data.prisonerId && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    Prisoner ID: <span className="font-bold text-slate-300">{data.prisonerId}</span>
                  </p>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {data.dob       && <span className="flex items-center gap-1 text-[10px] bg-white/10 border border-white/20 rounded-full px-2.5 py-1"><Calendar className="h-2.5 w-2.5" />{data.dob}</span>}
              {data.education && <span className="flex items-center gap-1 text-[10px] bg-white/10 border border-white/20 rounded-full px-2.5 py-1"><BookOpen className="h-2.5 w-2.5" />{data.education}</span>}
              {data.address   && <span className="flex items-center gap-1 text-[10px] bg-white/10 border border-white/20 rounded-full px-2.5 py-1"><MapPin className="h-2.5 w-2.5" />{data.address}</span>}
            </div>
          </div>
          {data.threatLevel && (
            <div className={`rounded-xl p-4 text-white bg-gradient-to-br ${threatColor} shadow-md text-center min-w-[130px]`}>
              <p className="text-[10px] font-black uppercase tracking-widest opacity-75 mb-1">Threat Level</p>
              <p className="text-sm font-black leading-tight">{data.threatLevel}</p>
              {data.confidence && (
                <p className="text-[10px] opacity-70 mt-1.5">Confidence: {data.confidence}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Bio + Physical ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <SectionCard icon={User} title="Subject Identification" iconClass="text-blue-500">
          <InfoRow label="Full Name"  value={data.name} />
          <InfoRow label="DOB"        value={data.dob} />
          <InfoRow label="Parentage"  value={data.parentage} />
          <InfoRow label="Education"  value={data.education} />
          <InfoRow label="Aliases"    value={data.aliases} />
          <InfoRow label="Habits"     value={data.habits} />
          <InfoRow label="Contact"    value={data.contact} />
        </SectionCard>

        <SectionCard icon={Eye} title="Physical Identification" iconClass="text-violet-500">
          <InfoRow label="ID Mark"    value={data.idMark} />
          <InfoRow label="Scars/Tattoos" value={data.scars} />
          <InfoRow label="Build"      value={data.buildVal} />
          <InfoRow label="Height"     value={data.heightVal} />
          <InfoRow label="Complexion" value={data.complexion} />
          <InfoRow label="Grooming"   value={data.grooming} />
          {data.address && <InfoRow label="Last Address" value={data.address} />}
        </SectionCard>
      </div>

      {/* ── Modus Operandi ── */}
      {(data.weapons || data.violence || data.environment || data.moLines.length > 0) && (
        <SectionCard icon={TrendingUp} title="Modus Operandi &amp; Behavioral Analysis" iconClass="text-orange-500">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
            <div className="rounded-lg border p-3 bg-orange-50/50 dark:bg-orange-950/10 border-orange-200 dark:border-orange-800/40">
              <p className="text-[10px] font-black uppercase tracking-widest text-orange-600 dark:text-orange-400 mb-1">Weapons</p>
              <p className="text-xs">{data.weapons && !isInsuff(data.weapons) ? data.weapons : <span className="text-muted-foreground/40 italic">Insufficient Data</span>}</p>
            </div>
            <div className="rounded-lg border p-3 bg-orange-50/50 dark:bg-orange-950/10 border-orange-200 dark:border-orange-800/40">
              <p className="text-[10px] font-black uppercase tracking-widest text-orange-600 dark:text-orange-400 mb-1">Violence Threshold</p>
              <p className="text-xs">{data.violence && !isInsuff(data.violence) ? data.violence : <span className="text-muted-foreground/40 italic">Insufficient Data</span>}</p>
            </div>
            <div className="rounded-lg border p-3 bg-orange-50/50 dark:bg-orange-950/10 border-orange-200 dark:border-orange-800/40">
              <p className="text-[10px] font-black uppercase tracking-widest text-orange-600 dark:text-orange-400 mb-1">Environment</p>
              <p className="text-xs">{data.environment && !isInsuff(data.environment) ? data.environment : <span className="text-muted-foreground/40 italic">Insufficient Data</span>}</p>
            </div>
          </div>
          {data.moLines.length > 0 && (
            <div className="space-y-1.5">
              {data.moLines.map((line, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <ChevronRight className="h-3 w-3 text-orange-500 shrink-0 mt-0.5" />
                  <span>{line}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {/* ── Case history ── */}
      {data.caseRows.length > 0 && (
        <SectionCard icon={FileText} title="Chronological Case History" iconClass="text-rose-500"
          badge={<Badge variant="destructive" className="text-[10px] font-bold">{data.caseRows.length} cases</Badge>}>
          <div className="overflow-x-auto -mx-4 -mb-4">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-muted/40 border-b">
                  {['Date', 'Location / Jurisdiction', 'Legal Sections', 'Status'].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left font-semibold text-muted-foreground whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.caseRows.map((row, i) => (
                  <tr key={i} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-2.5 whitespace-nowrap tabular-nums font-medium">{row.date}</td>
                    <td className="px-4 py-2.5">{row.location}</td>
                    <td className="px-4 py-2.5 font-mono text-[10px] text-rose-600 dark:text-rose-400">{row.sections}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.severityLines.length > 0 && (
            <div className="mt-4 pt-3 border-t space-y-1.5">
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">Severity Analysis</p>
              {data.severityLines.map((line, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <ChevronRight className="h-3 w-3 text-rose-400 shrink-0 mt-0.5" />
                  <span>{line}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {/* ── Associates + Risk ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {data.associates.length > 0 && (
          <SectionCard icon={Users} title="Known Associates" iconClass="text-teal-500"
            badge={<Badge variant="secondary" className="text-[10px] font-bold">{data.associates.length}</Badge>}>
            <div className="space-y-2">
              {data.associates.map((a, i) => (
                <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-teal-50/50 dark:bg-teal-950/10 border border-teal-100 dark:border-teal-900/30">
                  <div className="w-7 h-7 rounded-full bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center shrink-0">
                    <User className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold truncate">{a.name}</p>
                    <p className="text-[10px] text-muted-foreground capitalize">{a.relation}</p>
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {data.riskLines.length > 0 && (
          <SectionCard icon={Shield} title="Risk Profile" iconClass="text-rose-500">
            <div className="space-y-2">
              {data.riskLines.map((line, i) => (
                <div key={i} className="flex items-start gap-2 text-xs p-2 rounded-lg bg-rose-50/50 dark:bg-rose-950/10 border border-rose-100 dark:border-rose-900/30">
                  <AlertTriangle className="h-3 w-3 text-rose-500 shrink-0 mt-0.5" />
                  <span>{line}</span>
                </div>
              ))}
            </div>
          </SectionCard>
        )}
      </div>

      {/* ── Digital evasion ── */}
      {data.digitalLines.length > 0 && (
        <SectionCard icon={Smartphone} title="Digital &amp; Operational Evasion" iconClass="text-indigo-500">
          <div className="space-y-2">
            {data.digitalLines.map((line, i) => (
              <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/40">
                <Lock className="h-3.5 w-3.5 text-indigo-500 shrink-0 mt-0.5" />
                <span className="text-xs leading-relaxed">{line}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Network / affiliations ── */}
      {content.toLowerCase().includes('gang') || content.toLowerCase().includes('syndicate') ? (
        <SectionCard icon={Network} title="Organizational Network" iconClass="text-purple-500">
          <p className="text-xs text-muted-foreground italic">
            No confirmed gang affiliations or cross-border activity detected.
          </p>
        </SectionCard>
      ) : null}

      {/* ── Actionable directives ── */}
      {data.directives.length > 0 && (
        <SectionCard icon={Target} title="Actionable Field Directives" iconClass="text-rose-500">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {data.directives.map((d, i) => (
              <div key={i} className={`rounded-xl border p-3.5 ${DIRECTIVE_COLORS[i % DIRECTIVE_COLORS.length]}`}>
                <div className="flex items-center gap-2 mb-1.5">
                  <Target className={`h-3.5 w-3.5 shrink-0 ${DIRECTIVE_ICON_COLORS[i % DIRECTIVE_ICON_COLORS.length]}`} />
                  <p className="text-[10px] font-black uppercase tracking-wide">{d.title}</p>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">{d.detail}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Intelligence gaps ── */}
      {(data.gaps.length > 0 || data.missingItems.length > 0) && (
        <SectionCard icon={AlertTriangle} title="Intelligence Gaps &amp; Confidence Level" iconClass="text-amber-500"
          badge={data.confidence ? <Badge variant="outline" className="text-[10px] border-amber-400 text-amber-600">{data.confidence}</Badge> : undefined}>
          <div className="space-y-2">
            {(data.gaps.length > 0 ? data.gaps : data.missingItems).map((gap, i) => (
              <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/40">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
                <span className="text-xs leading-relaxed">{gap}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

    </div>
  )
}
