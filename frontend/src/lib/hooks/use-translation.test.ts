import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
// Ensure we are testing the real implementation
vi.unmock('@/lib/hooks/use-translation') 
import { useTranslation } from './use-translation'
import { useTranslation as useI18nTranslation } from 'react-i18next'

// Mock react-i18next is already done in setup.ts, 
// but we might need to control it per test
vi.mock('react-i18next', () => ({
  useTranslation: vi.fn()
}))

describe('useTranslation Hook', () => {
  const changeLanguageMock = vi.fn()
  
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useI18nTranslation as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      t: (key: string) => {
        if (key === 'common') return { appName: 'Open Notebook' }
        if (key === 'common.appName') return 'Open Notebook'
        return key
      },
      i18n: {
        language: 'en-US',
        changeLanguage: changeLanguageMock,
      },
    })
  })

  it('should return initial translations via proxy', () => {
    const { result } = renderHook(() => useTranslation())
    expect(result.current.language).toBe('en-US')
    // Test the proxy behavior t.common.appName -> t("common.appName")
    expect(result.current.t.common.appName).toBe('Open Notebook')
  })

  it('should allow changing language via i18n.changeLanguage', () => {
    const { result } = renderHook(() => useTranslation())
    
    act(() => {
      result.current.setLanguage('zh-CN')
    })
    
    expect(changeLanguageMock).toHaveBeenCalledWith('zh-CN')
  })
})
