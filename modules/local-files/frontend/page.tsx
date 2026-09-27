'use client'
import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useTranslation } from '@/lib/hooks/use-translation'
import SearchPanel from './SearchPanel'
export default function Page(){const {t}=useTranslation();const [query,setQuery]=useState('');const [submitted,setSubmitted]=useState('');return <AppShell><main className="mx-auto w-full max-w-5xl space-y-6 overflow-y-auto p-6"><h1 className="text-2xl font-semibold">{t('files.title')}</h1><form className="flex gap-2" onSubmit={e=>{e.preventDefault();setSubmitted(query.trim())}}><Input aria-label={t('files.title')} placeholder={t('files.hint')} value={query} onChange={e=>setQuery(e.target.value)}/><Button disabled={!query.trim()}>{t('files.search')}</Button></form><SearchPanel query={submitted}/></main></AppShell>}
