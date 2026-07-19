import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ChatPanel } from './ChatPanel'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: () => ({ openModal: vi.fn() }),
}))

// Keep the message-content deps light for this composer-focused test.
vi.mock('@/components/sources/MessageActions', () => ({
  MessageActions: () => null,
}))

describe('ChatPanel composer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // jsdom does not implement scrollIntoView (used by the auto-scroll effect).
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  const getTextarea = () => screen.getByRole('textbox') as HTMLTextAreaElement

  it('sends the typed message and clears the input on send-button click', () => {
    const onSendMessage = vi.fn()
    render(
      <ChatPanel
        messages={[]}
        isStreaming={false}
        contextIndicators={null}
        onSendMessage={onSendMessage}
      />
    )

    const textarea = getTextarea()
    fireEvent.change(textarea, { target: { value: '  hello world  ' } })

    const sendButton = screen.getByRole('button')
    fireEvent.click(sendButton)

    expect(onSendMessage).toHaveBeenCalledTimes(1)
    expect(onSendMessage).toHaveBeenCalledWith('hello world', undefined)
    expect(textarea.value).toBe('')
  })

  it('sends on Ctrl/Cmd+Enter', () => {
    const onSendMessage = vi.fn()
    render(
      <ChatPanel
        messages={[]}
        isStreaming={false}
        contextIndicators={null}
        onSendMessage={onSendMessage}
      />
    )

    const textarea = getTextarea()
    fireEvent.change(textarea, { target: { value: 'via shortcut' } })
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true, metaKey: true })

    expect(onSendMessage).toHaveBeenCalledWith('via shortcut', undefined)
    expect(textarea.value).toBe('')
  })

  it('does not send while streaming', () => {
    const onSendMessage = vi.fn()
    render(
      <ChatPanel
        messages={[]}
        isStreaming={true}
        contextIndicators={null}
        onSendMessage={onSendMessage}
      />
    )

    const textarea = getTextarea()
    // Textarea is disabled while streaming, but the guard must also hold.
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true })

    expect(onSendMessage).not.toHaveBeenCalled()
  })
})
