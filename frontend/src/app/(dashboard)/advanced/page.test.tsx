import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useCanManageTeams } from '@/lib/hooks/use-teams'
import AdvancedPage from './page'

vi.mock('@/lib/hooks/use-teams', () => ({
  useCanManageTeams: vi.fn(() => false),
}))

vi.mock('./components/RebuildEmbeddings', () => ({
  RebuildEmbeddings: () => <div>Global rebuild tool</div>,
}))

vi.mock('./components/SystemInfo', () => ({
  SystemInfo: () => <div>System info</div>,
}))

describe('AdvancedPage permissions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ role: 'user' })
    vi.mocked(useCanManageTeams).mockReturnValue(false)
  })

  it('does not expose the global rebuild tool to team managers', () => {
    vi.mocked(useCanManageTeams).mockReturnValue(true)

    render(<AdvancedPage />)

    expect(screen.getByText('Team owner tools')).toBeInTheDocument()
    expect(screen.queryByText('Global rebuild tool')).not.toBeInTheDocument()
  })
})
