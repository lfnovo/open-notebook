/* eslint-disable @typescript-eslint/no-explicit-any */
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useModalManager } from './use-modal-manager'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(),
  useSearchParams: vi.fn(),
  usePathname: vi.fn(),
}))

describe('useModalManager', () => {
  const pushMock = vi.fn()
  const pathnameMock = '/test-path'
  
  beforeEach(() => {
    vi.mocked(useRouter).mockReturnValue({ push: pushMock } as any)
    vi.mocked(usePathname).mockReturnValue(pathnameMock)
    pushMock.mockClear()
    window.history.replaceState(null, '', pathnameMock)
  })

  it('should return null modal state when no params present', () => {
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any)
    const { result } = renderHook(() => useModalManager())
    
    expect(result.current.modalType).toBeNull()
    expect(result.current.modalId).toBeNull()
    expect(result.current.isOpen).toBe(false)
  })

  it('should read modal state from URL params', () => {
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams('modal=note&id=123') as any)
    const { result } = renderHook(() => useModalManager())
    
    expect(result.current.modalType).toBe('note')
    expect(result.current.modalId).toBe('123')
    expect(result.current.isOpen).toBe(true)
  })

  it('should call router.push when opening a modal', () => {
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any)
    const { result } = renderHook(() => useModalManager())
    
    act(() => {
      result.current.openModal('source', 'abc')
    })
    
    expect(pushMock).toHaveBeenCalledWith('/test-path?modal=source&id=abc', { scroll: false })
  })

  it('closes a modal without leaving an empty query string', () => {
    window.history.replaceState(null, '', '/test-path?modal=note&id=123')
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams('modal=note&id=123') as any)
    const { result } = renderHook(() => useModalManager())
    
    act(() => {
      result.current.closeModal()
    })
    
    expect(window.location.href).toBe(`${window.location.origin}/test-path`)
  })

  it('preserves other query parameters and the fragment when closing', () => {
    window.history.replaceState(null, '', '/test-path?keep=one&modal=source&id=123&keep=two#section')
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams(window.location.search) as any)
    const { result } = renderHook(() => useModalManager())

    act(() => {
      result.current.closeModal()
    })

    expect(window.location.href).toBe(`${window.location.origin}/test-path?keep=one&keep=two#section`)
  })

  it('uses the current address when another URL update preceded the close', () => {
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams('modal=source&id=old') as any)
    const { result } = renderHook(() => useModalManager())
    window.history.replaceState(null, '', '/new-path?filter=recent&modal=insight&id=new#latest')

    act(() => {
      result.current.closeModal()
    })

    expect(window.location.href).toBe(`${window.location.origin}/new-path?filter=recent#latest`)
  })
})
