import { describe, expect, it } from 'vitest'
import { SourceListResponse } from '@/lib/types/api'
import { canDeleteSource, deletableSourceIds } from '@/lib/utils/source-delete-eligibility'

const source = (
  overrides: Partial<SourceListResponse> = {}
): SourceListResponse => ({
  id: 'source:one',
  title: 'One',
  topics: [],
  asset: null,
  embedded: false,
  embedded_chunks: 0,
  kg_extracted: false,
  insights_count: 0,
  reference_count: 0,
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
  owner_id: 'app_user:owner',
  visibility: 'private',
  ...overrides,
})

describe('source delete eligibility', () => {
  it('allows only the owner to delete a source', () => {
    expect(canDeleteSource(source(), 'app_user:owner')).toBe(true)
    expect(canDeleteSource(source(), 'app_user:member')).toBe(false)
  })

  it('uses backend capabilities when present', () => {
    expect(
      canDeleteSource(
        source({
          owner_id: 'app_user:other',
          capabilities: {
            can_read: true,
            can_update: false,
            can_delete: true,
            can_share: false,
            can_manage: false,
            can_create_source: false,
            can_remove_source: false,
            can_create_note: false,
            can_process: false,
          },
        }),
        'app_user:member'
      )
    ).toBe(true)
  })

  it('blocks referenced public sources even for the owner', () => {
    expect(
      canDeleteSource(
        source({ visibility: 'public', reference_count: 1 }),
        'app_user:owner'
      )
    ).toBe(false)
  })

  it('returns only deletable source ids for bulk delete', () => {
    expect(
      deletableSourceIds(
        [
          source({ id: 'source:owned' }),
          source({ id: 'source:other', owner_id: 'app_user:other' }),
          source({ id: 'source:referenced', visibility: 'public', reference_count: 2 }),
        ],
        'app_user:owner'
      )
    ).toEqual(['source:owned'])
  })
})
