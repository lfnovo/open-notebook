import { describe, expect, it } from 'vitest'
import { formatApiError, getApiErrorMessage } from './error-handler'

describe('formatApiError', () => {
  it('returns FastAPI validation array messages instead of a blank generic string', () => {
    const error = {
      response: {
        data: {
          detail: [
            {
              type: 'missing',
              loc: ['body', 'model_id'],
              msg: 'Field required',
              input: {},
            },
          ],
        },
      },
      message: 'Request failed with status code 422',
    }

    expect(formatApiError(error)).toBe('Field required')
    expect(getApiErrorMessage(error, (key) => key)).toBe('Field required')
  })

  it('still returns plain string detail messages', () => {
    expect(
      formatApiError({
        response: { data: { detail: 'Transformation not found' } },
      })
    ).toBe('Transformation not found')
  })
})
