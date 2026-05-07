import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SessionManager } from './SessionManager'

vi.mock('@/lib/hooks/use-models', () => ({
  useModels: () => ({ data: [] }),
}))

const baseSession = {
  id: 'chat_session:test',
  title: 'Team discussion',
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
}

describe('SessionManager', () => {
  it('disables edit and delete controls when the session capabilities deny them', () => {
    render(
      <SessionManager
        sessions={[
          {
            ...baseSession,
            capabilities: {
              can_read: true,
              can_update: false,
              can_delete: false,
              can_share: false,
              can_manage: false,
              can_create_source: false,
              can_remove_source: false,
              can_create_note: false,
              can_process: false,
            },
          },
        ]}
        currentSessionId={null}
        onCreateSession={vi.fn()}
        onSelectSession={vi.fn()}
        onUpdateSession={vi.fn()}
        onDeleteSession={vi.fn()}
        loadingSessions={false}
      />
    )

    const sessionCard = screen.getByText('Team discussion').closest('div')
    expect(sessionCard).not.toBeNull()
    expect(within(sessionCard as HTMLElement).getByRole('button', { name: 'Edit' })).toBeDisabled()
    expect(within(sessionCard as HTMLElement).getByRole('button', { name: 'Delete' })).toBeDisabled()
  })
})
