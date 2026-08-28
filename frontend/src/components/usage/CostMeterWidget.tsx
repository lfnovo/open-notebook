'use client'

import { useMemo, useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'

import { useUsageSummary } from '@/lib/hooks/use-usage'
import { useTranslation } from '@/lib/hooks/use-translation'
import { UsagePeriod } from '@/lib/types/usage'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'

function formatUsd(value: number, digits = 4) {
  return `$${value.toFixed(digits)}`
}

type ThresholdLevel = 'ok' | 'warn' | 'over'

function levelFor(percent: number): ThresholdLevel {
  if (percent >= 90) return 'over'
  if (percent >= 60) return 'warn'
  return 'ok'
}

const LEVEL_INDICATOR_CLASS: Record<ThresholdLevel, string> = {
  ok: 'bg-fern',
  warn: 'bg-warn',
  over: 'bg-destructive',
}

const LEVEL_TEXT_CLASS: Record<ThresholdLevel, string> = {
  ok: 'text-fern',
  warn: 'text-warn',
  over: 'text-destructive',
}

interface CostMeterWidgetProps {
  /** Renders a slim, single-line version with no breakdown (for a persistent header/sidebar spot). */
  compact?: boolean
  className?: string
}

export function CostMeterWidget({ compact = false, className }: CostMeterWidgetProps) {
  const { t } = useTranslation()
  const [period, setPeriod] = useState<UsagePeriod>('month')
  const { data, isLoading, isError } = useUsageSummary(period)

  const percent = useMemo(() => {
    if (!data || data.budget_usd <= 0) return 0
    return Math.min(100, (data.total_cost_usd / data.budget_usd) * 100)
  }, [data])

  const level = levelFor(percent)

  const breakdown = useMemo(() => {
    if (!data) return []
    return Object.entries(data.by_task_type)
      .filter(([, cost]) => cost > 0)
      .sort((a, b) => b[1] - a[1])
  }, [data])

  if (compact) {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center justify-between text-[11px] text-sidebar-foreground/60">
          <span>{t('usage.costMeter')}</span>
          {isLoading ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : data ? (
            <span className={cn('font-mono font-medium', LEVEL_TEXT_CLASS[level])}>
              {formatUsd(data.total_cost_usd, 2)} / {formatUsd(data.budget_usd, 2)}
            </span>
          ) : null}
        </div>
        {!isLoading && data ? (
          <Progress
            value={percent}
            indicatorClassName={LEVEL_INDICATOR_CLASS[level]}
            className="h-1.5"
            aria-label={t('usage.costMeter')}
          />
        ) : null}
      </div>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <div>
            <CardTitle>{t('usage.costMeter')}</CardTitle>
            <CardDescription>{t('usage.costMeterDesc')}</CardDescription>
          </div>
          <Tabs value={period} onValueChange={(value) => setPeriod(value as UsagePeriod)}>
            <TabsList>
              <TabsTrigger value="month">{t('usage.periodMonth')}</TabsTrigger>
              <TabsTrigger value="year">{t('usage.periodYear')}</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isError ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{t('usage.loadError')}</AlertDescription>
          </Alert>
        ) : isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('common.loading')}
          </div>
        ) : data ? (
          <>
            <div className="space-y-2">
              <div className="flex items-baseline justify-between">
                <span className={cn('text-lg font-semibold font-mono', LEVEL_TEXT_CLASS[level])}>
                  {formatUsd(data.total_cost_usd)}
                </span>
                <span className="text-sm text-muted-foreground">
                  {t('usage.usedOfBudget', { budget: formatUsd(data.budget_usd, 2) })}
                </span>
              </div>
              <Progress
                value={percent}
                indicatorClassName={LEVEL_INDICATOR_CLASS[level]}
                aria-label={t('usage.costMeter')}
              />
              <p className="text-xs text-muted-foreground">
                {t('usage.percentUsed', { percent: percent.toFixed(1) })}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
              <div>
                <p className="text-muted-foreground">{t('usage.inputTokens')}</p>
                <p className="font-mono text-sm text-foreground">{data.input_tokens.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-muted-foreground">{t('usage.outputTokens')}</p>
                <p className="font-mono text-sm text-foreground">{data.output_tokens.toLocaleString()}</p>
              </div>
            </div>

            {breakdown.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t('usage.byTaskType')}
                </p>
                <div className="space-y-1.5">
                  {breakdown.map(([taskType, cost]) => (
                    <div key={taskType} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{taskType}</span>
                      <span className="font-mono text-foreground">{formatUsd(cost)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">{t('usage.noUsageYet')}</p>
            )}
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}
