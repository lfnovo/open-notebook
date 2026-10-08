import { describe, it, expect } from 'vitest'
import { readChatImages, MAX_CHAT_IMAGE_BYTES } from './chat-images'

describe('chat image ingestion', () => {
  it('encodes image files and retains their filenames', async () => {
    const images = await readChatImages([new File(['pixels'], 'diagram.png', { type: 'image/png' })], 0)
    expect(images).toEqual([{ name: 'diagram.png', data_url: 'data:image/png;base64,cGl4ZWxz' }])
  })

  it('rejects more than four images, including the current draft', async () => {
    const file = new File(['pixels'], 'image.png', { type: 'image/png' })
    await expect(readChatImages([file, file], 3)).rejects.toThrow('chat.imageLimit')
    await expect(readChatImages(Array(5).fill(file), 0)).rejects.toThrow('chat.imageLimit')
  })

  it('rejects unsupported formats and oversized files before reading them', async () => {
    await expect(readChatImages([new File(['vector'], 'x.svg', { type: 'image/svg+xml' })], 0)).rejects.toThrow('chat.imageUnsupported')
    const large = new File(['pixels'], 'large.png', { type: 'image/png' })
    Object.defineProperty(large, 'size', { value: MAX_CHAT_IMAGE_BYTES + 1 })
    await expect(readChatImages([large], 0)).rejects.toThrow('chat.imageTooLarge')
  })
})
