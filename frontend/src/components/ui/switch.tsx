'use client'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

/** Keyboard-native toggle with a 44px target and a text label supplied by the host. */
export function Switch({ checked, onCheckedChange, className, disabled, ...props }: Omit<ComponentProps<'button'>, 'onChange' | 'onClick' | 'role'> & { checked: boolean; onCheckedChange: (checked: boolean) => void }) {
  return <button {...props} type="button" role="switch" aria-checked={checked} disabled={disabled} onClick={() => onCheckedChange(!checked)} className={cn('inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50', className)}><span aria-hidden className={cn('flex h-6 w-11 items-center rounded-full border px-0.5 transition-colors motion-reduce:transition-none', checked ? 'border-primary bg-primary' : 'border-border bg-muted')}><span className={cn('size-4 rounded-full shadow-sm transition-transform motion-reduce:transition-none', checked ? 'translate-x-5 bg-primary-foreground' : 'translate-x-0 bg-muted-foreground')} /></span></button>
}
