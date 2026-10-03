'use client'

import { ChevronLeft, ChevronRight, ArrowLeft, ArrowRight, Send, AlignLeft, AlignRight } from 'lucide-react'
import { useDirection } from '@radix-ui/react-direction'

/**
 * Current text direction ('ltr' | 'rtl') from the Radix direction context.
 * I18nProvider (PR #1367) is the single source of truth for direction;
 * components must be inside its DirectionProvider tree.
 */
export { useDirection }

/**
 * Chevron pointing to the "start" side (left in LTR, right in RTL).
 * Use for: back buttons, collapse sidebar, previous navigation.
 */
export function ChevronStart({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  const dir = useDirection()
  return dir === 'rtl' ? <ChevronRight className={className} {...props} /> : <ChevronLeft className={className} {...props} />
}

/**
 * Chevron pointing to the "end" side (right in LTR, left in RTL).
 * Use for: forward buttons, expand sidebar, next navigation, dropdown submenu indicators.
 */
export function ChevronEnd({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  const dir = useDirection()
  return dir === 'rtl' ? <ChevronLeft className={className} {...props} /> : <ChevronRight className={className} {...props} />
}

/**
 * Arrow pointing to the "start" side (left in LTR, right in RTL).
 * Use for: back navigation, breadcrumb separators pointing start.
 */
export function ArrowStart({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  const dir = useDirection()
  return dir === 'rtl' ? <ArrowRight className={className} {...props} /> : <ArrowLeft className={className} {...props} />
}

/**
 * Arrow pointing to the "end" side (right in LTR, left in RTL).
 * Use for: forward navigation, breadcrumb separators pointing end, "continue" actions.
 */
export function ArrowEnd({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  const dir = useDirection()
  return dir === 'rtl' ? <ArrowLeft className={className} {...props} /> : <ArrowRight className={className} {...props} />
}

/**
 * Send icon that points forward in the reading direction.
 * In RTL, this is mirrored to point left.
 */
export function SendDirectional({ className, ...props }: React.SVGProps<SVGSVGElement> & { className?: string }) {
  const dir = useDirection()
  const cn = [className, dir === 'rtl' ? 'scale-x-[-1]' : ''].filter(Boolean).join(' ')
  return <Send className={cn} {...props} />
}

/**
 * Text alignment icon representing text aligned to the start edge.
 * Uses AlignLeft in LTR and AlignRight in RTL.
 */
export function AlignStart({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  const dir = useDirection()
  return dir === 'rtl' ? <AlignRight className={className} {...props} /> : <AlignLeft className={className} {...props} />
}
