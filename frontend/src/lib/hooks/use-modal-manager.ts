'use client'

import { useCallback } from 'react'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'

export type ModalType = 'source' | 'note' | 'insight'

export function useModalManager() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  // Read current modal state from URL params
  const modalType = searchParams?.get('modal') as ModalType | null
  const modalId = searchParams?.get('id')

  /**
   * Open a modal by updating URL params without navigation
   * @param type - Type of modal to open (source, note, insight)
   * @param id - ID of the content to display
   */
  // Memoized so consumers can safely use it as a dependency (e.g. useCallback /
  // React.memo props) without re-creating handlers on every render.
  const openModal = useCallback((type: ModalType, id: string) => {
    const params = new URLSearchParams(searchParams?.toString() || '')
    params.set('modal', type)
    params.set('id', id)
    // Use scroll: false to prevent page from scrolling when modal state changes
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }, [router, searchParams, pathname])

  /**
   * Close the currently open modal by removing modal params from URL
   */
  const closeModal = useCallback(() => {
    const url = new URL(window.location.href)
    url.searchParams.delete('modal')
    url.searchParams.delete('id')
    // Next.js syncs useSearchParams with native history updates. Closing this
    // client-only UI state must not wait for an RSC navigation to finish.
    window.history.pushState(null, '', `${url.pathname}${url.search}${url.hash}`)
  }, [])

  return {
    modalType,
    modalId,
    openModal,
    closeModal,
    isOpen: !!modalType && !!modalId
  }
}
