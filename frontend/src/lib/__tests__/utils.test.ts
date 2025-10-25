/**
 * @jest-environment jsdom
 */

import { cn } from '@/lib/utils'

describe('cn (className utility)', () => {
  it('should merge class names', () => {
    const result = cn('btn', 'btn-primary')
    expect(result).toBe('btn btn-primary')
  })

  it('should handle conditional classes', () => {
    const isActive = true
    const result = cn('btn', isActive && 'active')
    expect(result).toBe('btn active')
  })

  it('should filter out false values', () => {
    const result = cn('btn', false, 'enabled')
    expect(result).toBe('btn enabled')
  })

  it('should handle Tailwind class conflicts', () => {
    // twMerge should prioritize the last conflicting class
    const result = cn('p-4', 'p-8')
    expect(result).toBe('p-8')
  })

  it('should handle arrays of classes', () => {
    const result = cn(['btn', 'btn-primary'], 'active')
    expect(result).toBe('btn btn-primary active')
  })

  it('should handle objects with boolean values', () => {
    const result = cn({
      btn: true,
      'btn-primary': true,
      disabled: false,
    })
    expect(result).toBe('btn btn-primary')
  })

  it('should handle empty input', () => {
    const result = cn()
    expect(result).toBe('')
  })

  it('should handle undefined and null', () => {
    const result = cn('btn', undefined, null, 'active')
    expect(result).toBe('btn active')
  })

  it('should merge complex Tailwind classes correctly', () => {
    // Test that conflicting utility classes are handled properly
    const result = cn(
      'bg-red-500 hover:bg-red-700 text-white',
      'bg-blue-500 hover:bg-blue-700'
    )
    // The second set of bg classes should override the first
    expect(result).toContain('bg-blue-500')
    expect(result).toContain('hover:bg-blue-700')
    expect(result).not.toContain('bg-red-500')
    expect(result).not.toContain('hover:bg-red-700')
  })
})
