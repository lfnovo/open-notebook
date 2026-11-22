import { describe, expect, it } from 'vitest'
import { resources } from './index'

describe('Source deletion notifications (#1471)', () => {
  it.each(Object.entries(resources))(
    '%s confirms deletion without instructions about file storage settings',
    (_code, { translation }) => {
      expect(translation.sources.deleteSuccess.replace(/[.。।]$/u, '')).toBe(
        translation.sources.sourceDeletedSuccess,
      )
    },
  )
})
