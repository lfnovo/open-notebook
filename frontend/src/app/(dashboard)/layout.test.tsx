import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DashboardLayout from './layout'

const dashboardDir = path.dirname(fileURLToPath(import.meta.url))

function findPageFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const fullPath = path.join(dir, entry)
    if (statSync(fullPath).isDirectory()) {
      return findPageFiles(fullPath)
    }
    return entry === 'page.tsx' ? [fullPath] : []
  })
}

vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-shell">{children}</div>
  ),
}))

vi.mock('@/components/providers/ModalProvider', () => ({
  ModalProvider: () => null,
}))

vi.mock('@/components/common/CommandPalette', () => ({
  CommandPalette: () => null,
}))

vi.mock('@/lib/hooks/use-create-dialogs', () => ({
  CreateDialogsProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('DashboardLayout', () => {
  it('renders authenticated dashboard pages inside the app shell sidebar layout', async () => {
    render(
      <DashboardLayout>
        <div>Dashboard content</div>
      </DashboardLayout>
    )

    await waitFor(() => {
      expect(screen.getByTestId('app-shell')).toBeInTheDocument()
    })
    expect(screen.getByText('Dashboard content')).toBeInTheDocument()
  })

  it('keeps AppShell ownership centralized in the dashboard layout', () => {
    const pageFilesWithAppShell = findPageFiles(dashboardDir).filter((file) => {
      const source = readFileSync(file, 'utf8')
      return source.includes('@/components/layout/AppShell') || source.includes('<AppShell')
    })

    expect(pageFilesWithAppShell.map((file) => path.relative(dashboardDir, file))).toEqual([])
  })
})
