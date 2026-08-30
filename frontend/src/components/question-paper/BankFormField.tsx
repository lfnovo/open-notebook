'use client'

import type { ReactNode } from 'react'
import { Label } from '@/components/ui/label'

export const BANK_FIELD_GRID_CLASS =
  'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-start'
export const BANK_FIELD_CONTROL_CLASS = 'h-9 w-full min-w-0'

export function bankFieldLabelId(id: string): string {
  return `${id}-label`
}

export function BankFormField({
  id,
  label,
  children,
}: {
  id: string
  label: string
  children: ReactNode
}) {
  return (
    <div className="flex min-w-0 w-full flex-col gap-1.5">
      <Label
        id={bankFieldLabelId(id)}
        htmlFor={id}
        className="block shrink-0 text-sm font-medium leading-5 text-foreground"
      >
        {label}
      </Label>
      {children}
    </div>
  )
}
