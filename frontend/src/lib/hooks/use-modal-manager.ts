'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'

export type ModalType = 'source' | 'note' | 'insight'

export function useModalManager() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  // Read current modal state from URL params
  const modalType = searchParams.get('modal') as ModalType | null
  const modalId = searchParams.get('id')

  /**
   * Open a modal by updating URL params without navigation
   * @param type - Type of modal to open (source, note, insight)
   * @param id - ID of the content to display
   */
  const openModal = (type: ModalType, id: string) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('modal', type)
    params.set('id', id)
    // Use scroll: false to prevent page from scrolling when modal state changes
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }

  /**
   * Close the currently open modal by removing modal params from URL
   */
  const closeModal = () => {
    const params = new URLSearchParams(searchParams.toString())
    params.delete('modal')
    params.delete('id')
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }

  return {
    modalType,
    modalId,
    openModal,
    closeModal,
    isOpen: !!modalType && !!modalId
  }
}
