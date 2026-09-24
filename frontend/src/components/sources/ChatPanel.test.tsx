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
})

describe('ChatPanel RTL content', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  const renderChatWithMessages = (messages: Array<{ id: string; type: 'human' | 'ai'; content: string }>) => {
    return render(
      <ChatPanel
        messages={messages as SourceChatMessage[]}
        isStreaming={false}
        contextIndicators={null}
        onSendMessage={vi.fn()}
      />
    )
  }

  describe('Human messages', () => {
    it('renders Arabic only message with dir="auto"', () => {
      renderChatWithMessages([{ id: '1', type: 'human', content: 'مرحبا بالعالم' }])
      const message = screen.getByText('مرحبا بالعالم')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })

    it('renders English only message with dir="auto"', () => {
      renderChatWithMessages([{ id: '2', type: 'human', content: 'Hello world' }])
      const message = screen.getByText('Hello world')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })

    it('renders mixed Arabic and English message with dir="auto"', () => {
      renderChatWithMessages([{ id: '3', type: 'human', content: 'مرحبا hello world' }])
      const message = screen.getByText('مرحبا hello world')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })

    it('renders Arabic message with URL', () => {
      renderChatWithMessages([{ id: '4', type: 'human', content: 'رابط: https://example.com/path' }])
      const message = screen.getByText('رابط: https://example.com/path')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })

    it('renders Arabic message with email', () => {
      renderChatWithMessages([{ id: '5', type: 'human', content: 'بريد: user@example.com' }])
      const message = screen.getByText('بريد: user@example.com')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })

    it('renders Arabic message with inline code', () => {
      renderChatWithMessages([{ id: '6', type: 'human', content: 'الكود: `npm install`' }])
      const message = screen.getByText('الكود: `npm install`')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })

    it('renders Arabic message with numbers', () => {
      renderChatWithMessages([{ id: '7', type: 'human', content: 'العدد 123 والعدد 456' }])
      const message = screen.getByText('العدد 123 والعدد 456')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })

    it('renders Arabic message with quoted text', () => {
      renderChatWithMessages([{ id: '8', type: 'human', content: 'اقتباس: "نص مقتبس"' }])
      const message = screen.getByText('اقتباس: "نص مقتبس"')
      expect(message).toBeInTheDocument()
      expect(message).toHaveAttribute('dir', 'auto')
    })
  })

  describe('AI messages', () => {
    it('renders Arabic only AI message with dir="auto" on root', () => {
      renderChatWithMessages([{ id: '9', type: 'ai', content: 'مرحبا بالعالم' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
      expect(root?.textContent).toContain('مرحبا')
    })

    it('renders English only AI message with dir="auto" on root', () => {
      renderChatWithMessages([{ id: '10', type: 'ai', content: 'Hello world' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
      expect(root?.textContent).toContain('Hello world')
    })

    it('renders mixed Arabic and English AI message with dir="auto"', () => {
      renderChatWithMessages([{ id: '11', type: 'ai', content: 'مرحبا hello world بالعالم' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
    })

    it('renders Arabic AI message with URL and forces URL to LTR', () => {
      renderChatWithMessages([{ id: '12', type: 'ai', content: 'رابط: https://example.com/path' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
      const link = document.querySelector('a[dir="ltr"]')
      expect(link).toBeInTheDocument()
      expect(link?.getAttribute('href')).toBe('https://example.com/path')
    })

    it('renders Arabic AI message with email and forces email to LTR', () => {
      renderChatWithMessages([{ id: '13', type: 'ai', content: 'بريد: user@example.com' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
      const link = document.querySelector('a[dir="ltr"]')
      expect(link).toBeInTheDocument()
      expect(link?.getAttribute('href')).toBe('mailto:user@example.com')
    })

    it('renders Arabic AI message with inline code and forces code to LTR', () => {
      renderChatWithMessages([{ id: '14', type: 'ai', content: 'الكود: `npm install`' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
      const inlineCode = document.querySelector('code[dir="ltr"]')
      expect(inlineCode).toBeInTheDocument()
      expect(inlineCode?.textContent).toBe('npm install')
    })

    it('renders Arabic AI message with fenced code block and forces code block to LTR', () => {
      renderChatWithMessages([{ id: '15', type: 'ai', content: 'الكود:\n```js\nconst x = 1\n```' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
      const codeWrapper = document.querySelector('div[dir="ltr"]')
      expect(codeWrapper).toBeInTheDocument()
      expect(codeWrapper?.textContent).toContain('const x = 1')
    })

    it('renders Arabic AI message with numbers', () => {
      renderChatWithMessages([{ id: '16', type: 'ai', content: 'العدد 123 والعدد 456' }])
      const root = document.querySelector('[dir="auto"]')
      expect(root).toBeInTheDocument()
      expect(root?.textContent).toContain('123')
      expect(root?.textContent).toContain('456')
    })
  })

  describe('Message alignment', () => {
    it('preserves semantic alignment for human messages', () => {
      renderChatWithMessages([
        { id: '17', type: 'human', content: 'Hello' },
        { id: '18', type: 'ai', content: 'Hi there' },
      ])

      const humanMessage = screen.getByText('Hello').closest('div[class*="justify-end"]')
      const aiMessage = screen.getByText('Hi there').closest('div[class*="justify-start"]')

      expect(humanMessage).toBeInTheDocument()
      expect(aiMessage).toBeInTheDocument()
    })
  })
})
