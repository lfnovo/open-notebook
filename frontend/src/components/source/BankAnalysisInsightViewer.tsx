'use client'

import { useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import {
  AlertTriangle, TrendingUp, TrendingDown,
  BarChart2, Users, ShieldAlert, Activity,
  ArrowUpCircle, ArrowDownCircle, Wallet,
} from 'lucide-react'

interface BankAnalysisInsightViewerProps {
  content: string
}

// ── helpers ───────────────────────────────────────────────────────────────────

function extractValue(text: string, label: string): string {
  const re = new RegExp(`\\*?\\*?${label}\\*?\\*?[:\\s]+([^\\n*|]+)`, 'i')
  const m = text.match(re)
  return m ? m[1].trim().replace(/\*+/g, '').replace(/\s+/g, ' ') : ''
}

function parseAmount(s: string): number {
  return parseFloat(s.replace(/[₹,\s]/g, '')) || 0
}

function fmt(n: number) {
  return `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

interface TxRow { date: string; description: string; type: string; amount: number; category: string }

function parseTransactions(content: string): TxRow[] {
  const rows: TxRow[] = []
  for (const line of content.split('\n')) {
    if (!line.trim().startsWith('|')) continue
    const cells = line.split('|').map(c => c.trim()).filter(Boolean)
    if (cells.length < 5) continue
    if (/^[-:]+$/.test(cells[0]) || /date/i.test(cells[0])) continue
    const amount = parseAmount(cells[3])
    if (isNaN(amount) || amount === 0) continue
    rows.push({ date: cells[0], description: cells[1], type: cells[2], amount, category: cells[4] ?? '' })
  }
  return rows
}

function parseInsightLines(content: string, sectionHeading: string): string[] {
  const re = new RegExp(`${sectionHeading}[\\s\\S]*?(?=\\n---\\n|\\n\\*\\*Risk|$)`, 'i')
  const m = content.match(re)
  if (!m) return []
  return m[0].split('\n')
    .filter(l => /^[-•*]|\d+\./.test(l.trim()))
    .map(l => l.replace(/^[-•*\d.]+\s*/, '').replace(/\*\*/g, '').trim())
    .filter(Boolean)
}

// ── UI primitives ─────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, gradient }: {
  label: string; value: string; sub?: string
  icon: React.ElementType; gradient: string
}) {
  return (
    <div className={`rounded-xl p-4 text-white bg-gradient-to-br ${gradient} shadow-sm`}>
      <div className="flex items-start justify-between mb-2">
        <p className="text-[10px] font-bold uppercase tracking-widest opacity-80">{label}</p>
        <Icon className="h-4 w-4 opacity-60" />
      </div>
      <p className="text-xl font-black leading-tight">{value}</p>
      {sub && <p className="text-[10px] opacity-70 mt-1">{sub}</p>}
    </div>
  )
}

function HBar({ label, value, max, color, amount }: {
  label: string; value: number; max: number; color: string; amount: string
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="font-medium truncate max-w-[55%]">{label}</span>
        <span className="text-muted-foreground shrink-0 tabular-nums">{amount} <span className="opacity-60">({pct}%)</span></span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function DonutChart({ segments }: { segments: { label: string; value: number; color: string }[] }) {
  const total = segments.reduce((s, x) => s + x.value, 0)
  const r = 42, circ = 2 * Math.PI * r
  let offset = 0
  return (
    <div className="flex items-center gap-5">
      <svg width="100" height="100" viewBox="0 0 100 100" className="shrink-0 drop-shadow-sm">
        {segments.map((seg, i) => {
          const pct = seg.value / total
          const dash = pct * circ
          const rot = offset * 360 - 90
          offset += pct
          return (
            <circle key={i} cx="50" cy="50" r={r} fill="none" strokeWidth="16"
              stroke={seg.color} strokeLinecap="round"
              strokeDasharray={`${dash} ${circ - dash}`}
              transform={`rotate(${rot} 50 50)`}
            />
          )
        })}
        <text x="50" y="46" textAnchor="middle" fontSize="11" fontWeight="800" fill="currentColor">{total}</text>
        <text x="50" y="58" textAnchor="middle" fontSize="7" fill="currentColor" opacity="0.5">total</text>
      </svg>
      <div className="flex flex-col gap-2.5 flex-1">
        {segments.map((seg, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: seg.color }} />
            <span className="text-xs flex-1">{seg.label}</span>
            <span className="text-xs font-bold tabular-nums">{seg.value}</span>
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {Math.round((seg.value / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

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

// ── detector ─────────────────────────────────────────────────────────────────

export function isBankAnalysisInsight(insightType: string): boolean {
  return insightType.toLowerCase().includes('bank anal')
}

// ── main viewer ───────────────────────────────────────────────────────────────

export function BankAnalysisInsightViewer({ content }: BankAnalysisInsightViewerProps) {
  const data = useMemo(() => {
    const holder      = extractValue(content, 'Account Holder Name')
                     || extractValue(content, 'Account Holder')
                     || extractValue(content, 'Holder')
    const accountType = extractValue(content, 'Account Type')
    const status      = extractValue(content, 'Status')
    const period      = extractValue(content, 'Period')
    const currency    = extractValue(content, 'Currency')
    const creditRisk  = extractValue(content, 'Credit Risk Score')
    const riskTier    = extractValue(content, 'Risk Tier')
    const reasoning   = extractValue(content, 'Reasoning')

    const transactions = parseTransactions(content)
    const totalCredit  = transactions.filter(t => /credit/i.test(t.type)).reduce((s, t) => s + t.amount, 0)
    const totalDebit   = transactions.filter(t => /debit/i.test(t.type)).reduce((s, t) => s + t.amount, 0)

    const categoryMap: Record<string, number> = {}
    for (const tx of transactions) {
      const cat = tx.category || 'Other'
      categoryMap[cat] = (categoryMap[cat] || 0) + tx.amount
    }
    const categories = Object.entries(categoryMap).sort((a, b) => b[1] - a[1]).map(([name, total]) => ({ name, total }))

    const entityMap: Record<string, number> = {}
    for (const tx of transactions) {
      const key = tx.description.split(/[-\s]/)[0].replace(/\./g, '').trim()
      if (key) entityMap[key] = (entityMap[key] || 0) + tx.amount
    }
    const topEntities = Object.entries(entityMap).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([name, value]) => ({ name, value }))

    const anomalies    = transactions.filter(t => /debit/i.test(t.type) && t.amount >= 5000)
    const normalCount  = transactions.length - anomalies.length
    const anomalyCount = anomalies.length
    const advancedLines = parseInsightLines(content, 'ADVANCED INSIGHTS')

    return {
      holder, accountType, status, period, currency, creditRisk, riskTier, reasoning,
      transactions, totalCredit, totalDebit, categories, topEntities,
      normalCount, anomalyCount, anomalies, advancedLines,
    }
  }, [content])

  const maxCategory = Math.max(...data.categories.map(c => c.total), 1)
  const maxEntity   = Math.max(...data.topEntities.map(e => e.value), 1)
  const catColors   = ['bg-blue-500', 'bg-amber-500', 'bg-violet-500', 'bg-emerald-500', 'bg-rose-500']
  const entColors   = ['bg-indigo-500', 'bg-teal-500', 'bg-orange-500', 'bg-pink-500', 'bg-cyan-500']
  const netFlow     = data.totalCredit - data.totalDebit

  return (
    <div className="space-y-5 pb-4">

      {/* ── Hero banner ── */}
      <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 text-white p-6 shadow-lg">
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-blue-400 blur-3xl" />
          <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-indigo-400 blur-3xl" />
        </div>
        <div className="relative flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Wallet className="h-4 w-4 text-blue-300" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-blue-300">Bank Analytical Profile</span>
            </div>
            <h2 className="text-2xl font-black text-white">{data.holder || 'N/A'}</h2>
            {data.accountType && <p className="text-sm text-blue-200/70 mt-1">{data.accountType}</p>}
            {data.period      && <p className="text-xs text-blue-300/60 mt-0.5">{data.period}</p>}
          </div>
          <div className="flex flex-col items-end gap-2">
            {data.status && (
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide ${
                data.status.toLowerCase() === 'regular'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-500/20 text-slate-300 border border-slate-500/30'
              }`}>
                {data.status}
              </span>
            )}
            {data.currency && <span className="text-xs text-blue-300/60 font-medium">{data.currency}</span>}
          </div>
        </div>
        {/* KPI row */}
        <div className="relative grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
          <KpiCard label="Total Credit"  value={fmt(data.totalCredit)} icon={ArrowUpCircle}   gradient="from-emerald-600 to-emerald-800" />
          <KpiCard label="Total Debit"   value={fmt(data.totalDebit)}  icon={ArrowDownCircle} gradient="from-rose-600 to-rose-800" />
          <KpiCard label="Net Flow"      value={fmt(Math.abs(netFlow))} sub={netFlow >= 0 ? 'Surplus' : 'Deficit'} icon={Activity} gradient={netFlow >= 0 ? 'from-blue-600 to-blue-800' : 'from-orange-600 to-orange-800'} />
          <KpiCard label="Risk Tier"     value={data.riskTier || '—'}  icon={ShieldAlert}     gradient="from-violet-600 to-violet-800" />
        </div>
      </div>

      {/* ── Credit vs Debit bar ── */}
      <SectionCard icon={Activity} title="Credit vs Debit Flow">
        {(() => {
          const total = (data.totalCredit + data.totalDebit) || 1
          const cp = Math.round((data.totalCredit / total) * 100)
          const dp = 100 - cp
          return (
            <div className="space-y-3">
              <div className="flex h-7 rounded-xl overflow-hidden shadow-inner text-[11px] font-bold">
                <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 flex items-center justify-center text-white transition-all" style={{ width: `${cp}%` }}>
                  {cp > 12 ? `${cp}%` : ''}
                </div>
                <div className="bg-gradient-to-r from-rose-500 to-rose-600 flex-1 flex items-center justify-center text-white">
                  {dp > 12 ? `${dp}%` : ''}
                </div>
              </div>
              <div className="flex justify-between text-xs">
                <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                  <ArrowUpCircle className="h-3.5 w-3.5" /> Credit: {fmt(data.totalCredit)}
                </span>
                <span className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400 font-medium">
                  <ArrowDownCircle className="h-3.5 w-3.5" /> Debit: {fmt(data.totalDebit)}
                </span>
              </div>
            </div>
          )
        })()}
      </SectionCard>

      {/* ── Category + Anomaly ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {data.categories.length > 0 && (
          <SectionCard icon={BarChart2} title="Category Distribution">
            {data.categories.map((c, i) => (
              <HBar key={i} label={c.name} value={c.total} max={maxCategory}
                color={catColors[i % catColors.length]} amount={fmt(c.total)} />
            ))}
          </SectionCard>
        )}

        <SectionCard icon={AlertTriangle} title="Anomaly Split" iconClass="text-amber-500">
          <DonutChart segments={[
            { label: 'Normal',  value: data.normalCount,  color: '#10b981' },
            { label: 'Anomaly', value: data.anomalyCount, color: '#f43f5e' },
          ]} />
          {data.anomalies.length > 0 && (
            <div className="mt-4 space-y-2 border-t pt-3">
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-2">High-Value Debits</p>
              {data.anomalies.map((tx, i) => (
                <div key={i} className="flex items-center gap-2 text-xs bg-rose-50 dark:bg-rose-950/20 rounded-lg px-2.5 py-1.5">
                  <AlertTriangle className="h-3 w-3 text-rose-500 shrink-0" />
                  <span className="flex-1 truncate text-muted-foreground">{tx.description}</span>
                  <span className="font-bold text-rose-600 dark:text-rose-400 shrink-0 tabular-nums">{fmt(tx.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      {/* ── Transaction ledger ── */}
      {data.transactions.length > 0 && (
        <SectionCard icon={TrendingDown} title="Transaction Ledger"
          badge={<Badge variant="secondary" className="text-[10px] font-bold">{data.transactions.length} txns</Badge>}>
          <div className="overflow-x-auto -mx-4 -mb-4">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-muted/40 border-b">
                  <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground whitespace-nowrap">Date</th>
                  <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground">Description</th>
                  <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground whitespace-nowrap">Type</th>
                  <th className="px-4 py-2.5 text-right font-semibold text-muted-foreground whitespace-nowrap">Amount</th>
                  <th className="px-4 py-2.5 text-left font-semibold text-muted-foreground whitespace-nowrap">Category</th>
                </tr>
              </thead>
              <tbody>
                {data.transactions.map((tx, i) => {
                  const isDebit = /debit/i.test(tx.type)
                  return (
                    <tr key={i} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-2.5 whitespace-nowrap text-muted-foreground tabular-nums">{tx.date}</td>
                      <td className="px-4 py-2.5 max-w-[180px] truncate" title={tx.description}>{tx.description}</td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          isDebit
                            ? 'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400'
                            : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400'
                        }`}>
                          {isDebit ? <ArrowDownCircle className="h-2.5 w-2.5" /> : <ArrowUpCircle className="h-2.5 w-2.5" />}
                          {tx.type}
                        </span>
                      </td>
                      <td className={`px-4 py-2.5 text-right font-bold whitespace-nowrap tabular-nums ${
                        isDebit ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'
                      }`}>
                        {isDebit ? '−' : '+'}{fmt(tx.amount)}
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">{tx.category}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}

      {/* ── Top entities ── */}
      {data.topEntities.length > 0 && (
        <SectionCard icon={Users} title="Top Entities by Volume">
          {data.topEntities.map((e, i) => (
            <HBar key={i} label={e.name} value={e.value} max={maxEntity}
              color={entColors[i % entColors.length]} amount={fmt(e.value)} />
          ))}
        </SectionCard>
      )}

      {/* ── Advanced insights ── */}
      {data.advancedLines.length > 0 && (
        <SectionCard icon={TrendingUp} title="Advanced Insights">
          <div className="space-y-2">
            {data.advancedLines.map((line, i) => (
              <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-blue-50/50 dark:bg-blue-950/10 border border-blue-100 dark:border-blue-900/30">
                <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center text-[10px] font-black shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <span className="text-xs leading-relaxed">{line}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Risk reasoning ── */}
      {data.reasoning && (
        <div className="rounded-xl border border-amber-200 dark:border-amber-800/50 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20 p-5 shadow-sm">
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center">
              <ShieldAlert className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200">Risk Assessment</h3>
              {data.creditRisk && <p className="text-[10px] text-amber-700 dark:text-amber-400">Score: {data.creditRisk}</p>}
            </div>
            {data.riskTier && (
              <Badge className="ml-auto bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-400/40 hover:bg-amber-500/30">
                {data.riskTier}
              </Badge>
            )}
          </div>
          <p className="text-sm text-amber-900/80 dark:text-amber-200/80 leading-relaxed">{data.reasoning}</p>
        </div>
      )}

    </div>
  )
}
