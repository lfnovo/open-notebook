import { describe, expect, it } from 'vitest'
import { getApiErrorMessage } from './error-handler'

const t = (key: string) => `t:${key}`

describe('getApiErrorMessage', () => {
  // Insight generation on a source with no text (#1394): the API's 400 detail
  // and the worker's failure message both map to one translated string.
  it.each(['Source has no text content', 'There is no text content to transform'])(
    'maps %j to the translated empty-source message',
    (detail) => {
      expect(getApiErrorMessage(detail, t, 'common.error')).toBe('t:apiErrors.sourceHasNoText')
    }
  )

  it('falls back to the given key when there is no server detail', () => {
    // SourceDetailContent passes '' for a network error with no response.
    expect(getApiErrorMessage('', t, 'common.error')).toBe('t:common.error')
  })

  it('returns an unmapped server detail as is', () => {
    expect(getApiErrorMessage('Something specific', t, 'common.error')).toBe('Something specific')
  })
})
