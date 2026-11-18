import { beforeEach, describe, it, expect, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'

import { useThemeStore } from '@/lib/stores/theme-store'

import { MarkdownRenderer } from './markdown-renderer'

// useTranslation is mocked globally in setup.ts (t returns the key string).
// jsdom cannot lay out SVG, so Mermaid itself is mocked.
const mermaidMock = vi.hoisted(() => ({
  initialize: vi.fn(),
  parse: vi.fn(),
  render: vi.fn(),
}))
vi.mock('mermaid', () => ({ default: mermaidMock }))

const DIAGRAM = '```mermaid\ngraph TD\n  A --> B\n```'

describe('MarkdownRenderer', () => {
  it('renders basic markdown', () => {
    const { container } = render(<MarkdownRenderer>{'# Title\n\nSome **bold** text'}</MarkdownRenderer>)
    expect(container.querySelector('h1')?.textContent).toBe('Title')
    expect(container.querySelector('strong')?.textContent).toBe('bold')
  })

  it('highlights fenced code blocks for registered languages', () => {
    const { container } = render(
      <MarkdownRenderer>{'```python\ndef hello():\n    return 42\n```'}</MarkdownRenderer>
    )
    // PrismLight emits token spans when the grammar is registered; a plain
    // fallback would leave the code block without any token markup.
    expect(container.querySelectorAll('span[class*="token"]').length).toBeGreaterThan(0)
  })

  it('falls back to plain text for unknown languages without crashing', () => {
    const { container } = render(
      <MarkdownRenderer>{'```notalanguage\nsome content\n```'}</MarkdownRenderer>
    )
    expect(container.textContent).toContain('some content')
  })

  it.each([
    ['Korean', '**요일(일)**입니다', '요일(일)'],
    ['Chinese', '**注意：**请先备份数据。', '注意：'],
    ['Japanese', '**この文は強調されます。**次の文。', 'この文は強調されます。'],
  ])('bolds %s text when ** sits between punctuation and a CJK letter', (_, source, bold) => {
    const { container } = render(<MarkdownRenderer>{source}</MarkdownRenderer>)
    expect(container.querySelector('strong')?.textContent).toBe(bold)
  })

  it('renders inline code without a highlighter block', () => {
    const { container } = render(<MarkdownRenderer>{'Use `npm ci` here'}</MarkdownRenderer>)
    expect(container.querySelector('code')?.textContent).toBe('npm ci')
    expect(container.querySelectorAll('span[class*="token"]').length).toBe(0)
  })
})

describe('MarkdownRenderer mermaid blocks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mermaidMock.parse.mockResolvedValue(true)
    mermaidMock.render.mockResolvedValue({ svg: '<svg data-testid="fake-svg"></svg>' })
  })

  it('shows the code first, then the diagram once it renders', async () => {
    render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)
    expect(screen.getByText(/A --> B/)).toBeInTheDocument()
    expect(screen.queryByTestId('mermaid-diagram')).not.toBeInTheDocument()

    expect(await screen.findByTestId('mermaid-diagram')).toBeInTheDocument()
    expect(screen.getByTestId('fake-svg')).toBeInTheDocument()
  })

  it('initialises Mermaid in strict security mode', async () => {
    render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)
    await screen.findByTestId('mermaid-diagram')
    expect(mermaidMock.initialize).toHaveBeenCalledWith(
      expect.objectContaining({ securityLevel: 'strict', htmlLabels: false, startOnLoad: false })
    )
  })

  it('renders the SVG at its natural width so wide diagrams scroll', async () => {
    mermaidMock.render.mockResolvedValue({
      svg: '<svg width="100%" style="max-width: 4392px;" viewBox="4 4 4392 76.5"></svg>',
    })
    render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)

    const svg = (await screen.findByTestId('mermaid-diagram')).querySelector('svg')
    expect(svg).toHaveAttribute('width', '4392')
    expect(svg?.getAttribute('style') ?? '').not.toContain('max-width')
  })

  it('toggles between the diagram and the raw code', async () => {
    render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)
    await screen.findByTestId('mermaid-diagram')

    fireEvent.click(screen.getByRole('button', { name: 'common.showCode' }))
    expect(screen.queryByTestId('mermaid-diagram')).not.toBeInTheDocument()
    expect(screen.getByText(/A --> B/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'common.showDiagram' }))
    expect(screen.getByTestId('mermaid-diagram')).toBeInTheDocument()
  })

  it('keeps the code block when the syntax is invalid', async () => {
    mermaidMock.parse.mockResolvedValue(false)
    render(<MarkdownRenderer>{'```mermaid\nnot a diagram\n```'}</MarkdownRenderer>)

    await waitFor(() => expect(mermaidMock.parse).toHaveBeenCalled())
    expect(mermaidMock.render).not.toHaveBeenCalled()
    expect(screen.getByText(/not a diagram/)).toBeInTheDocument()
    expect(screen.queryByTestId('mermaid-diagram')).not.toBeInTheDocument()
  })

  it('keeps the code block when rendering throws', async () => {
    mermaidMock.render.mockRejectedValue(new Error('boom'))
    render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)

    await waitFor(() => expect(mermaidMock.render).toHaveBeenCalled())
    expect(screen.getByText(/A --> B/)).toBeInTheDocument()
    expect(screen.queryByTestId('mermaid-diagram')).not.toBeInTheDocument()
  })

  it('does not load Mermaid for other languages', async () => {
    render(<MarkdownRenderer>{'```python\nprint(1)\n```'}</MarkdownRenderer>)
    await new Promise((resolve) => setTimeout(resolve, 400))
    expect(mermaidMock.parse).not.toHaveBeenCalled()
  })

  it('protects its security options from an %%{init}%% directive in the diagram', async () => {
    render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)
    await screen.findByTestId('mermaid-diagram')

    const config = mermaidMock.initialize.mock.calls[0][0]
    expect(config.secure).toEqual(expect.arrayContaining(['securityLevel', 'htmlLabels', 'themeCSS']))
  })

  it('keeps an unfinished block as code until its closing fence arrives', async () => {
    const { rerender } = render(<MarkdownRenderer>{'```mermaid\ngraph TD\n  A --> B'}</MarkdownRenderer>)
    await new Promise((resolve) => setTimeout(resolve, 500))
    expect(mermaidMock.parse).not.toHaveBeenCalled()
    expect(screen.queryByTestId('mermaid-diagram')).not.toBeInTheDocument()

    rerender(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)
    expect(await screen.findByTestId('mermaid-diagram')).toBeInTheDocument()
  })

  it('parses once when the source changes rapidly', async () => {
    const { rerender } = render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)
    rerender(<MarkdownRenderer>{DIAGRAM.replace('B', 'C')}</MarkdownRenderer>)
    rerender(<MarkdownRenderer>{DIAGRAM.replace('B', 'D')}</MarkdownRenderer>)

    await screen.findByTestId('mermaid-diagram')
    expect(mermaidMock.parse).toHaveBeenCalledTimes(1)
    expect(mermaidMock.parse).toHaveBeenCalledWith('graph TD\n  A --> D', expect.anything())
  })

  it('re-renders with the matching theme when the app theme changes', async () => {
    act(() => useThemeStore.getState().setTheme('light'))
    render(<MarkdownRenderer>{DIAGRAM}</MarkdownRenderer>)
    await screen.findByTestId('mermaid-diagram')
    expect(mermaidMock.initialize).toHaveBeenLastCalledWith(expect.objectContaining({ theme: 'default' }))

    act(() => useThemeStore.getState().setTheme('dark'))
    await waitFor(() =>
      expect(mermaidMock.initialize).toHaveBeenLastCalledWith(expect.objectContaining({ theme: 'dark' }))
    )
  })
})
