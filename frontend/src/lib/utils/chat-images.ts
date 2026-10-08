import type { ChatImage } from '@/lib/types/api'

export const MAX_CHAT_IMAGES = 4
export const MAX_CHAT_IMAGE_BYTES = 5 * 1024 * 1024
export const CHAT_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp']

export async function readChatImages(files: File[], existingCount: number): Promise<ChatImage[]> {
  if (files.length + existingCount > MAX_CHAT_IMAGES) throw new Error('chat.imageLimit')
  for (const file of files) {
    if (!CHAT_IMAGE_TYPES.includes(file.type)) throw new Error('chat.imageUnsupported')
    if (file.size > MAX_CHAT_IMAGE_BYTES) throw new Error('chat.imageTooLarge')
  }
  return Promise.all(files.map(file => new Promise<ChatImage>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result !== 'string') {
        reject(new Error('chat.imageReadFailed'))
        return
      }
      resolve({ name: file.name || 'image.png', data_url: reader.result })
    }
    reader.onerror = () => reject(new Error('chat.imageReadFailed'))
    reader.onabort = () => reject(new Error('chat.imageReadFailed'))
    reader.readAsDataURL(file)
  })))
}
