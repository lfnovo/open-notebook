/* eslint-disable @typescript-eslint/no-explicit-any */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

import { SidebarSections } from './SidebarSections'
import { useSidebarStore } from '@/lib/stores/sidebar-store'

const sections = vi.hoisted(() => ({ data: [] as { id: string; name: string }[] }))
vi.mock('@/lib/hooks/use-sections', () => ({
  useSections: () => ({ data: sections.data }),
}))

const toggleSections = vi.fn()
const setHidden = (sectionsHidden: boolean) =>
  vi.mocked(useSidebarStore).mockReturnValue({ sectionsHidden, toggleSections } as any)

describe('SidebarSections', () => {
  beforeEach(() => {
    sections.data = [
      { id: 'section:1', name: 'Personal' },
      { id: 'section:2', name: 'Work' },
    ]
    toggleSections.mockClear()
    setHidden(false)
  })

  it('renders nothing when there are no sections', () => {
    sections.data = []
    const { container } = render(<SidebarSections />)
    expect(container).toBeEmptyDOMElement()
  })

  it('lists sections as links to the filtered notebooks page', () => {
    render(<SidebarSections />)
    expect(screen.getByText('Personal').closest('a')).toHaveAttribute(
      'href',
      '/notebooks?section=section%3A1'
    )
    expect(screen.getByText('Work')).toBeInTheDocument()
  })

  it('shows a hide toggle while the list is visible', () => {
    render(<SidebarSections />)
    const toggle = screen.getByRole('button', { name: 'sections.hideInSidebar' })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(toggle)
    expect(toggleSections).toHaveBeenCalledTimes(1)
  })

  it('keeps only the header, with a show toggle, while hidden', () => {
    setHidden(true)
    render(<SidebarSections />)

    expect(screen.queryByText('Personal')).toBeNull()
    expect(screen.getByRole('button', { name: 'sections.showInSidebar' })).toHaveAttribute(
      'aria-expanded',
      'false'
    )
  })
})
