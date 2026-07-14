import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { getTypeIcon, getTypeColor, getTypeLabel } from './providers'

describe('model type presentation helpers', () => {
  it('maps known modalities to their icons', () => {
    const { container } = render(<>{getTypeIcon('language')}</>)
    expect(container.querySelector('svg')).toBeInTheDocument()
    expect(container.querySelector('.lucide-box')).not.toBeInTheDocument()
  })

  it('falls back to a generic icon for unknown modalities', () => {
    // Provider modalities are runtime data from GET /api/providers: a new
    // backend modality must still render instead of breaking the UI.
    const { container } = render(<>{getTypeIcon('holograms')}</>)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('renders different markup for known vs unknown modalities', () => {
    const known = render(<>{getTypeIcon('embedding')}</>)
    const unknown = render(<>{getTypeIcon('not-a-modality')}</>)
    expect(known.container.innerHTML).not.toEqual(unknown.container.innerHTML)
  })

  it('falls back to the raw modality name as label', () => {
    expect(getTypeLabel('language')).toBe('Language')
    expect(getTypeLabel('holograms')).toBe('holograms')
  })

  it('falls back to a neutral color for unknown modalities', () => {
    expect(getTypeColor('holograms')).toBeTruthy()
    expect(getTypeColor('holograms')).not.toEqual(getTypeColor('language'))
  })
})
