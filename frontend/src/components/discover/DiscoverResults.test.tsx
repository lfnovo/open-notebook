import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { DiscoverResults } from './DiscoverResults'
import type { DiscoveredSource } from '@/lib/types/discover'

// useTranslation is mocked globally in src/test/setup.ts (t returns the key)

function makeSource(overrides: Partial<DiscoveredSource> = {}): DiscoveredSource {
  return {
    title: 'Example page',
    url: 'https://example.com/article',
    snippet: 'excerpt',
    score: 0.75,
    source_id: null,
    status: 'created',
    error: null,
    ...overrides,
  }
}

describe('DiscoverResults', () => {
  it('renders one row per hit with title, host, score and status badge', () => {
    render(
      <DiscoverResults
        results={[makeSource()]}
        createdCount={1}
        skippedCount={0}
        notebookId="notebook:1"
      />
    )

    expect(screen.getByText('Example page')).toBeInTheDocument()
    expect(screen.getByText('example.com')).toBeInTheDocument()
    expect(screen.getByText('0.75')).toBeInTheDocument()
    expect(screen.getByText('discover.statusCreated')).toBeInTheDocument()
  })

  it('marks a skipped hit and exposes the reason as a tooltip', () => {
    render(
      <DiscoverResults
        results={[
          makeSource({
            status: 'skipped',
            error: 'Already a source in this notebook',
          }),
        ]}
        createdCount={0}
        skippedCount={1}
        notebookId="notebook:1"
      />
    )

    const badge = screen.getByText('discover.statusSkipped')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveAttribute('title', 'Already a source in this notebook')
  })

  it('shows the empty state when there are no results', () => {
    render(
      <DiscoverResults
        results={[]}
        createdCount={0}
        skippedCount={0}
        notebookId="notebook:1"
      />
    )

    expect(screen.getByText('discover.emptyState')).toBeInTheDocument()
  })

  it('renders the summary and a link to the notebook', () => {
    render(
      <DiscoverResults
        results={[makeSource()]}
        createdCount={2}
        skippedCount={3}
        notebookId="notebook:7"
      />
    )

    expect(screen.getByText('discover.summary')).toBeInTheDocument()
    expect(screen.getByText('discover.openNotebook')).toHaveAttribute(
      'href',
      '/notebooks/notebook:7'
    )
  })
})
