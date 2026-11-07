import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'

// Radix Select measures its trigger via ResizeObserver, which jsdom lacks.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

// Radix Select relies on pointer capture APIs that jsdom does not implement.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false
  Element.prototype.setPointerCapture = () => {}
  Element.prototype.releasePointerCapture = () => {}
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}

import { DiscoverForm } from './DiscoverForm'

// useTranslation is mocked globally in src/test/setup.ts (t returns the key)

const NOTEBOOKS = [
  { id: 'notebook:1', name: 'First notebook' },
  { id: 'notebook:2', name: 'Second notebook' },
]

function renderForm(overrides: Partial<React.ComponentProps<typeof DiscoverForm>> = {}) {
  const onSubmit = vi.fn()
  render(
    <DiscoverForm
      notebooks={NOTEBOOKS}
      submitting={false}
      onSubmit={onSubmit}
      {...overrides}
    />
  )
  return { onSubmit }
}

async function selectNotebook(name: string) {
  const trigger = screen.getByRole('combobox', { name: 'discover.notebookLabel' })
  // jsdom has no PointerEvent, so the mouse path of the Radix trigger cannot
  // run. The keyboard path (ArrowDown) opens the menu without any pointer.
  fireEvent.keyDown(trigger, { key: 'ArrowDown' })
  const option = await screen.findByRole('option', { name })
  fireEvent.click(option)
}

describe('DiscoverForm', () => {
  it('keeps submit disabled until a notebook is selected', () => {
    renderForm()

    const topic = screen.getByLabelText('discover.topicLabel')
    fireEvent.change(topic, { target: { value: 'MCP protocol' } })

    expect(screen.getByRole('button', { name: 'discover.submit' })).toBeDisabled()
  })

  it('keeps submit disabled while the topic is empty', () => {
    renderForm()

    expect(screen.getByRole('button', { name: 'discover.submit' })).toBeDisabled()
  })

  it('submits the topic, the selected notebook and the limit', async () => {
    const { onSubmit } = renderForm()

    fireEvent.change(screen.getByLabelText('discover.topicLabel'), {
      target: { value: 'MCP protocol' },
    })
    await selectNotebook('Second notebook')

    const submit = screen.getByRole('button', { name: 'discover.submit' })
    expect(submit).toBeEnabled()

    fireEvent.click(submit)

    expect(onSubmit).toHaveBeenCalledWith({
      query: 'MCP protocol',
      notebookId: 'notebook:2',
      limit: 5,
      dryRun: false,
    })
  })

  it('warns when there is no notebook to attach the sources to', () => {
    renderForm({ notebooks: [] })

    expect(screen.getByText('discover.noNotebooks')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'discover.submit' })).toBeDisabled()
  })
})
