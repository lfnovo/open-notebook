import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { DirectionProvider } from '@radix-ui/react-direction'
import { useThemeStore } from '@/lib/stores/theme-store'
import { MarkdownEditor } from './markdown-editor'

vi.mock('next/dynamic', async () => {
  const { default: Editor } = await import('@uiw/react-md-editor')
  return { default: () => Editor }
})

afterEach(cleanup)

it('activates the editor RTL pane layout and restores it when direction changes', () => {
  useThemeStore.getState().setHasHydrated(true)
  const { container, rerender } = render(
    <DirectionProvider dir="rtl">
      <MarkdownEditor value="العربية — עברית — English" />
    </DirectionProvider>
  )
  const editor = container.querySelector('.w-md-editor')
  expect(editor).toHaveClass('w-md-editor-rtl')
  expect(container.querySelector('textarea')).toHaveValue('العربية — עברית — English')
  expect(container.querySelector('.w-md-editor-preview')).toHaveTextContent('العربية — עברית — English')

  rerender(
    <DirectionProvider dir="ltr">
      <MarkdownEditor value="العربية — עברית — English" />
    </DirectionProvider>
  )
  expect(container.querySelector('.w-md-editor')).toBe(editor)
  expect(editor).toHaveClass('w-md-editor-ltr')
  expect(editor).not.toHaveClass('w-md-editor-rtl')
})
