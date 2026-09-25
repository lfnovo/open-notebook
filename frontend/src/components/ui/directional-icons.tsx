'use client'

import { ChevronLeft, ChevronRight, ArrowLeft, ArrowRight, Send, AlignLeft, AlignRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { i18nEvents, I18N_LANGUAGE_CHANGE_END } from '@/lib/i18n-events'

/**
 * Returns the current text direction ('ltr' | 'rtl').
 * Reads from document.documentElement.dir which is set by directionScript
 * and kept in sync by DirectionProvider.
 */
function getDirection(): 'ltr' | 'rtl' {
  if (typeof document === 'undefined') return 'ltr'
  return (document.documentElement.dir as 'ltr' | 'rtl') || 'ltr'
}

/**
 * Hook to get current text direction and subscribe to changes.
 * Direction changes only happen on language switch, which is rare,
 * so we listen to the i18n event target directly.
 */
export function useDirection(): 'ltr' | 'rtl' {
  const [dir, setDir] = useState<'ltr' | 'rtl'>(getDirection)

  useEffect(() => {
    const updateDir = () => setDir(getDirection())
    updateDir()

    const handleLanguageChange = () => {
      updateDir()
    }

    i18nEvents.addEventListener(I18N_LANGUAGE_CHANGE_END, handleLanguageChange)

    // Fallback: listen for direct dir attribute changes
    const observer = new MutationObserver(updateDir)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['dir'] })

    return () => {
      i18nEvents.removeEventListener(I18N_LANGUAGE_CHANGE_END, handleLanguageChange)
      observer.disconnect()
    }
  }, [])

  return dir
}

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
  // Need to dynamically import Send or just return an SVG that scales.
  // Actually, we can import Send at the top.
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
