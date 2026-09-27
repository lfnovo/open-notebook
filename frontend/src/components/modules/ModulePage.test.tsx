import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ModulePage } from './ModulePage'
import { useModules } from '@/lib/modules/hooks'

vi.mock('@/lib/modules/hooks', () => ({ useModules: vi.fn() }))
vi.mock('@/lib/modules/generated', () => ({ moduleEntries: { demo: { Page: () => <p>Optional feature mounted</p> } } }))
vi.mock('@/components/layout/AppShell', () => ({ AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }))

describe('Module host isolation', () => {
  it('does not mount a disabled module or call its feature hooks', () => {
    vi.mocked(useModules).mockReturnValue({ data: [{ id: 'demo', enabled: false }], isLoading: false } as ReturnType<typeof useModules>)
    render(<ModulePage id="demo" />)
    expect(screen.queryByText('Optional feature mounted')).not.toBeInTheDocument()
    expect(screen.getByText('modules.unavailable')).toBeInTheDocument()
  })
  it('mounts an enabled, installed module', () => {
    vi.mocked(useModules).mockReturnValue({ data: [{ id: 'demo', enabled: true }] } as ReturnType<typeof useModules>)
    render(<ModulePage id="demo" />)
    expect(screen.getByText('Optional feature mounted')).toBeInTheDocument()
  })
  it('fails closed if the module catalog is unavailable', () => {
    vi.mocked(useModules).mockReturnValue({ isError: true, refetch: vi.fn() } as unknown as ReturnType<typeof useModules>)
    render(<ModulePage id="demo" />)
    expect(screen.queryByText('Optional feature mounted')).not.toBeInTheDocument()
    expect(screen.getByText('modules.error')).toBeInTheDocument()
  })
})
