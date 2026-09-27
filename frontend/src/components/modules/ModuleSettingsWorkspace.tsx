'use client'

import { useState } from 'react'
import { AlertCircle, ArrowUpRight, AudioLines, Boxes, Check, ChevronRight, Circle, Download, HardDrive, Layers, Loader2, Palette, Puzzle, RotateCcw, Save, Search, Telescope } from 'lucide-react'
import { isAxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useModules } from '@/lib/modules/hooks'
import { useModuleSettings } from '@/lib/modules/use-module-settings'
import { moduleRepository } from '@/lib/modules/repository'
import type { ModuleInfo, SettingSpec, SettingValue } from '@/lib/modules/types'
import { cn } from '@/lib/utils'

const icons: Record<string, typeof Puzzle> = { 'multi-model-research': Telescope, 'account-models': Boxes, 'local-audio': AudioLines, 'natural-voice': AudioLines, 'local-embeddings': Layers, 'local-workspace': Palette, 'local-processing': Layers, 'local-deployment': HardDrive }

function ModuleState({ module }: { module: ModuleInfo }) {
  const { t } = useTranslation()
  const pending = module.pending_build
  return <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium', pending ? 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300' : module.enabled ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : 'text-muted-foreground')}>
    {pending ? <RotateCcw aria-hidden className="size-3" /> : module.enabled ? <Check aria-hidden className="size-3" /> : <Circle aria-hidden className="size-3" />}
    {t(pending ? 'modules.pendingBuild' : module.enabled ? 'modules.enabled' : 'modules.disabled')}
  </span>
}

function SettingControl({ moduleId, field, value, disabled, onChange }: { moduleId: string; field: SettingSpec; value: SettingValue; disabled: boolean; onChange: (value: SettingValue) => void }) {
  const { t } = useTranslation()
  const id = `module-${moduleId}-${field.key}`
  return <div className={cn('flex gap-5 py-5', field.kind === 'boolean' ? 'items-center justify-between' : 'flex-col gap-3 sm:flex-row sm:justify-between')}>
    <div className="max-w-md space-y-1.5"><Label htmlFor={id} className="text-sm font-medium">{t(field.label_key)}</Label><p id={`${id}-help`} className="text-xs leading-relaxed text-muted-foreground">{t(field.help_key)}</p></div>
    {field.kind === 'boolean' ? <Switch id={id} checked={Boolean(value)} onCheckedChange={onChange} disabled={disabled} aria-describedby={`${id}-help`} />
      : field.kind === 'choice' ? <select id={id} aria-describedby={`${id}-help`} value={String(value)} disabled={disabled} onChange={event => onChange(event.target.value)} className="h-11 w-full rounded-lg border bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:w-44">
        {field.options.map(option => <option key={option} value={option}>{t('modules.options.' + option)}</option>)}
      </select> : <Input id={id} aria-describedby={`${id}-help`} type={field.kind === 'integer' ? 'number' : 'text'} value={typeof value === 'number' && Number.isNaN(value) ? '' : String(value)} min={field.minimum ?? undefined} max={field.maximum ?? undefined} step={field.kind === 'integer' ? 1 : undefined} maxLength={field.kind === 'text' ? 120 : undefined} disabled={disabled} onChange={event => onChange(field.kind === 'integer' ? event.target.valueAsNumber : event.target.value)} className="h-11 w-full sm:w-44" />}
  </div>
}

function ModuleSettingsPanel({ module, catalog }: { module: ModuleInfo; catalog: ModuleInfo[] }) {
  const { t } = useTranslation()
  const vm = useModuleSettings(module)
  const Icon = icons[module.id] ?? Puzzle
  const dependents = catalog.filter(other => other.enabled && other.dependencies.includes(module.id))
  const missing = module.dependencies.filter(id => !catalog.some(other => other.id === id && other.enabled))
  const blocked = module.enabled ? dependents.length > 0 : missing.length > 0
  const dependencyNames = (module.enabled ? dependents.map(item => item.id) : missing).map(id => t('modules.names.' + id, { defaultValue: catalog.find(item => item.id === id)?.name ?? id })).join(', ')
  const available = module.installed || module.activation === 'build'
  const error = isAxiosError(vm.error) && typeof vm.error.response?.data?.detail === 'string' ? vm.error.response.data.detail : t('modules.operationError')
  return <section className="min-w-0 overflow-hidden rounded-2xl border bg-card shadow-sm" aria-label={t('modules.names.' + module.id, { defaultValue: module.name })}>
    <header className="space-y-5 border-b bg-muted/20 p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><div className="flex items-center gap-3"><span className="flex size-11 items-center justify-center rounded-xl border bg-background text-primary"><Icon aria-hidden className="size-5" /></span><div><p className="text-xs text-muted-foreground">{t('modules.configuration')}</p><h2 className="mt-1 text-lg font-semibold tracking-tight">{t('modules.names.' + module.id, { defaultValue: module.name })}</h2></div></div><ModuleState module={module} /></div>
      <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">{t('modules.descriptions.' + module.id, { defaultValue: module.description })}</p>
      <div className="flex items-center justify-between gap-5 rounded-xl border bg-background p-4"><div><Label htmlFor={`enabled-${module.id}`} className="font-medium">{t('modules.useModule')}</Label><p className="mt-1 text-xs text-muted-foreground">{t(module.activation === 'build' ? 'modules.buildSwitchHelp' : 'modules.runtimeSwitchHelp')}</p></div><Switch id={`enabled-${module.id}`} checked={module.enabled} onCheckedChange={vm.toggle} disabled={!available || blocked || vm.pending || vm.draft.dirty} aria-describedby={`module-dependencies-${module.id}`} /></div>
      <div id={`module-dependencies-${module.id}`} className="text-xs leading-relaxed text-muted-foreground">
        {blocked ? t(module.enabled ? 'modules.disableDependencies' : 'modules.enableDependencies', { names: dependencyNames }) : !available ? t('modules.installHelp') : vm.draft.dirty ? t('modules.saveBeforeToggle') : t('modules.dataRetained')}
      </div>
    </header>
    <div className="space-y-4 p-5 sm:p-6">
      {module.pending_build && <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm"><p className="font-medium">{t('modules.pendingBuild')}</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{t('modules.pendingBuildHelp', { current: t(module.active ? 'modules.enabled' : 'modules.disabled') })}</p></div>}
      {!module.enabled && !module.pending_build && <p className="rounded-xl bg-muted/40 p-3 text-xs text-muted-foreground">{t('modules.disabledHelp')}</p>}
      <form onSubmit={event => { event.preventDefault(); if (vm.draft.valid && !vm.conflict) vm.save() }}>
        <div className="flex items-center justify-between gap-2"><h3 className="text-sm font-semibold">{t('modules.preferences')}</h3><Button type="button" variant="ghost" size="sm" disabled={!available || vm.pending} onClick={vm.defaults} className="min-h-11"><RotateCcw aria-hidden className="size-3.5" />{t('modules.defaults')}</Button></div>
        <div className="divide-y">{module.settings_schema?.map(field => <SettingControl key={field.key} moduleId={module.id} field={field} value={vm.draft.values[field.key]} disabled={!available || vm.pending} onChange={value => vm.change(field.key, value)} />)}</div>
        <div aria-live="polite" className="space-y-3">
          {vm.conflict && <p role="alert" className="rounded-lg border border-amber-500/30 p-3 text-sm">{t('modules.conflict')}</p>}
          {vm.draft.dirty && !vm.draft.valid && <p role="alert" className="text-sm text-destructive">{t('modules.invalid')}</p>}
          {vm.error && <p role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm"><AlertCircle aria-hidden className="mt-0.5 size-4 shrink-0" />{error}</p>}
          {vm.saved && <p role="status" className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-300"><Check aria-hidden className="size-4" />{t('modules.saved')}</p>}
        </div>
        <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-5"><p className="text-xs text-muted-foreground">{t(vm.draft.dirty ? 'modules.unsaved' : 'modules.upToDate')}</p><div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row"><Button type="button" variant="outline" className="min-h-11" disabled={vm.pending || (!vm.draft.dirty && !vm.error)} onClick={vm.discard}>{t('modules.discard')}</Button><Button type="submit" className="min-h-11" disabled={!available || !vm.draft.dirty || !vm.draft.valid || vm.conflict || vm.pending}>{vm.pending ? <Loader2 aria-hidden className="size-4 animate-spin" /> : <Save aria-hidden className="size-4" />}{t('modules.save')}</Button></div></footer>
      </form>
      <details className="border-t pt-4 text-xs text-muted-foreground"><summary className="min-h-8 cursor-pointer font-medium">{t('modules.details')}</summary><dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2"><dt>{t('modules.version')}</dt><dd>{module.version}</dd><dt>{t('modules.dependencies')}</dt><dd>{module.dependencies.map(id => t('modules.names.' + id, { defaultValue: id })).join(', ') || t('modules.noDependencies')}</dd><dt>{t('modules.application')}</dt><dd>{t(module.activation === 'build' ? 'modules.build' : 'modules.onNextRequest')}</dd></dl></details>
      {module.enabled && module.frontend && <Button asChild variant="outline" className="min-h-11"><a href={module.frontend.route}>{t('modules.openModule')}<ArrowUpRight aria-hidden className="size-4" /></a></Button>}
    </div>
  </section>
}

export function ModuleSettingsWorkspace() {
  const { t } = useTranslation()
  const query = useModules()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState('multi-model-research')
  const [exportError, setExportError] = useState(false)
  const catalog = query.data ?? []
  const visible = catalog.filter(item => `${t('modules.names.' + item.id, { defaultValue: item.name })} ${item.id}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
  const current = catalog.find(item => item.id === selected) ?? catalog[0]
  const count = catalog.filter(item => item.active ?? item.enabled).length
  async function exportConfiguration() {
    try {
      const data = await moduleRepository.exportConfiguration()
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a'); link.href = url; link.download = 'open-notebook-modules.json'; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000); setExportError(false)
    } catch { setExportError(true) }
  }
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">{t('modules.yourModules')}</h2><p className="mt-1 text-sm text-muted-foreground">{t('modules.activeCount', { count, total: catalog.length })}</p></div><Button variant="outline" className="min-h-11" onClick={exportConfiguration} disabled={!query.data}><Download aria-hidden className="size-4" />{t('modules.export')}</Button></div>
    {exportError && <p role="alert" className="text-sm text-destructive">{t('modules.operationError')}</p>}
    {query.isLoading && <p role="status" className="flex items-center gap-2 p-6 text-sm"><Loader2 aria-hidden className="size-4 animate-spin" />{t('common.loading')}</p>}
    {query.isError && <div role="alert" className="rounded-xl border border-destructive/30 p-4">{t('modules.error')} <Button variant="outline" onClick={() => query.refetch()}>{t('modules.retry')}</Button></div>}
    {query.data && <div className="grid items-start gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="space-y-3 lg:sticky lg:top-4"><div className="relative hidden sm:block"><Search aria-hidden className="absolute left-3 top-3.5 size-4 text-muted-foreground" /><Input aria-label={t('modules.search')} placeholder={t('modules.search')} value={search} onChange={event => setSearch(event.target.value)} className="h-11 pl-9" /></div>
        <div className="space-y-2 sm:hidden"><Label htmlFor="mobile-module-select">{t('modules.chooseModule')}</Label><select id="mobile-module-select" value={current?.id ?? ''} onChange={event => setSelected(event.target.value)} className="h-11 w-full rounded-lg border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{catalog.map(item => <option key={item.id} value={item.id}>{t('modules.names.' + item.id, { defaultValue: item.name })}</option>)}</select></div>
        <nav aria-label={t('modules.title')} className="hidden gap-1.5 sm:grid sm:grid-cols-2 lg:grid-cols-1">{visible.map(item => { const Icon = icons[item.id] ?? Puzzle; return <button key={item.id} type="button" aria-current={current?.id === item.id ? 'true' : undefined} onClick={() => setSelected(item.id)} className={cn('group flex min-h-20 w-full items-center gap-3 rounded-xl border p-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', current?.id === item.id ? 'border-primary/40 bg-primary/5 shadow-sm' : 'border-transparent hover:border-border hover:bg-muted/40')}><Icon aria-hidden className={cn('size-5 shrink-0', current?.id === item.id ? 'text-primary' : 'text-muted-foreground')} /><span className="min-w-0 flex-1 space-y-1.5"><span className="block text-sm font-medium">{t('modules.names.' + item.id, { defaultValue: item.name })}</span><ModuleState module={item} /></span><ChevronRight aria-hidden className="size-4 shrink-0 text-muted-foreground" /></button> })}</nav>
        {!visible.length && <p className="p-4 text-sm text-muted-foreground">{t('modules.noResults')}</p>}
        <p className="hidden px-3 pt-2 text-xs leading-relaxed text-muted-foreground sm:block">{t('modules.catalogHelp')}</p>
      </aside>
      <div className="min-w-0">{catalog.map(item => <div key={item.id} hidden={current?.id !== item.id}><ModuleSettingsPanel module={item} catalog={catalog} /></div>)}</div>
    </div>}
  </div>
}
