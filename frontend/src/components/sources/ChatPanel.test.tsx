import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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

    const sendButton = screen.getByRole('button', { name: 'chat.sendMessage' })
    fireEvent.click(sendButton)

    expect(onSendMessage).toHaveBeenCalledTimes(1)
    expect(onSendMessage).toHaveBeenCalledWith('hello world', undefined)
    expect(textarea.value).toBe('')
  })

  it('sends on Cmd+Enter on macOS', () => {
    const uaSpy = vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    )
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
    fireEvent.change(textarea, { target: { value: 'via cmd' } })
    fireEvent.keyDown(textarea, { key: 'Enter', metaKey: true, ctrlKey: false })

    expect(onSendMessage).toHaveBeenCalledWith('via cmd', undefined)
    expect(textarea.value).toBe('')
    uaSpy.mockRestore()
  })

  it('sends on Ctrl+Enter on non-macOS', () => {
    const uaSpy = vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    )
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
    fireEvent.change(textarea, { target: { value: 'via ctrl' } })
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true, metaKey: false })

    expect(onSendMessage).toHaveBeenCalledWith('via ctrl', undefined)
    expect(textarea.value).toBe('')
    uaSpy.mockRestore()
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

  const mount = (onSendMessage = vi.fn()) => {
    render(<ChatPanel messages={[]} isStreaming={false} contextIndicators={null} onSendMessage={onSendMessage} />)
    return {
      onSendMessage,
      fileInput: screen.getByLabelText('chat.attachImages', { selector: 'input' }),
      sendButton: screen.getByRole('button', { name: 'chat.sendMessage' }),
    }
  }

  it('previews an attached image, sends it without text and clears it on success', async () => {
    const { fileInput, sendButton, onSendMessage } = mount()
    fireEvent.change(fileInput, { target: { files: [new File(['pixels'], 'chart.png', { type: 'image/png' })] } })
    await screen.findByAltText('chart.png')
    fireEvent.click(sendButton)
    expect(onSendMessage).toHaveBeenCalledWith('', undefined, [{ name: 'chart.png', data_url: expect.stringContaining('data:image/png;base64,') }])
    expect(screen.queryByAltText('chart.png')).not.toBeInTheDocument()
  })

  it('keeps the image and text when sending fails, allowing a retry', async () => {
    const { fileInput, sendButton, onSendMessage } = mount(vi.fn().mockResolvedValue(false))
    fireEvent.change(fileInput, { target: { files: [new File(['pixels'], 'chart.png', { type: 'image/png' })] } })
    await screen.findByAltText('chart.png')
    fireEvent.change(getTextarea(), { target: { value: 'Explain this chart' } })
    fireEvent.click(sendButton)
    await waitFor(() => expect(sendButton).not.toBeDisabled())
    expect(onSendMessage).toHaveBeenCalledTimes(1)
    expect(getTextarea().value).toBe('Explain this chart')
    expect(screen.getByAltText('chart.png')).toBeInTheDocument()
  })

  it('can remove an image before sending', async () => {
    const { fileInput, sendButton } = mount()
    fireEvent.change(fileInput, { target: { files: [new File(['pixels'], 'chart.png', { type: 'image/png' })] } })
    await screen.findByAltText('chart.png')
    fireEvent.click(screen.getByRole('button', { name: 'chat.removeImage' }))
    expect(screen.queryByAltText('chart.png')).not.toBeInTheDocument()
    expect(sendButton).toBeDisabled()
  })

  it('accepts pasted and dropped images', async () => {
    mount()
    fireEvent.paste(getTextarea(), { clipboardData: { files: [new File(['pixels'], 'paste.png', { type: 'image/png' })] } })
    await screen.findByAltText('paste.png')
    fireEvent.drop(getTextarea(), { dataTransfer: { files: [new File(['pixels'], 'drop.webp', { type: 'image/webp' })] } })
    await screen.findByAltText('drop.webp')
    expect(screen.getAllByRole('img')).toHaveLength(2)
  })

  it('renders image attachments restored from history', () => {
    render(<ChatPanel messages={[{ id: 'one', type: 'human', content: '', images: [{ name: 'saved.png', data_url: 'data:image/png;base64,aGVsbG8=' }] }]}
      isStreaming={false} contextIndicators={null} onSendMessage={vi.fn()} />)
    expect(screen.getByAltText('saved.png')).toBeInTheDocument()
  })
  it('sends the visual mode flag explicitly', () => {
    const { onSendMessage, sendButton } = mount()
    fireEvent.click(screen.getByRole('checkbox', { name: 'chat.visualResponses' }))
    fireEvent.change(getTextarea(), { target: { value: 'Show a source crop' } })
    fireEvent.click(sendButton)
    expect(onSendMessage).toHaveBeenCalledWith('Show a source crop', undefined, [], true)
  })

  it('renders generated images and source provenance in AI answers', () => {
    render(<ChatPanel messages={[{ id: 'visual', type: 'ai', content: 'An explanation', images: [
      { name: 'Generated diagram', data_url: 'data:image/png;base64,aGVsbG8=', kind: 'generated' },
      { name: 'Source crop', data_url: 'data:image/png;base64,aGVsbG8=', kind: 'source', source_id: 'source:one', source_title: 'PDF', page: 3 },
    ] }]} isStreaming={false} contextIndicators={null} onSendMessage={vi.fn()} />)
    expect(screen.getByAltText('Generated diagram')).toBeInTheDocument()
    expect(screen.getByText('chat.generatedImage')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'chat.sourceImage' })).toHaveAttribute('href', '/sources/source%3Aone')
  })

})
