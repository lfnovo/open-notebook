import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AddSourceDialog } from './AddSourceDialog'
import { getApiUrl } from '@/lib/config'
import { toast } from 'sonner'

vi.mock('@/lib/config', () => ({ getApiUrl: vi.fn() }))
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }))
vi.mock('@/lib/hooks/use-notebooks', () => ({ useNotebooks: () => ({ data: [], isLoading: false }) }))
vi.mock('@/lib/hooks/use-transformations', () => ({ useTransformations: () => ({ data: [], isLoading: false }) }))
vi.mock('@/lib/hooks/use-settings', () => ({ useSettings: () => ({ data: {} }) }))
const mutateAsync = vi.fn()
vi.mock('@/lib/hooks/use-sources', () => ({ useCreateSource: () => ({ mutateAsync, isPending: false }) }))

const mockGetApiUrl = vi.mocked(getApiUrl)
const mockToastError = vi.mocked(toast.error)

// jsdom has no FileList constructor; this passes the dialog's `instanceof FileList` checks like a real one.
function fileList(...files: File[]): FileList {
  const list = Object.fromEntries(files.map((f, i) => [i, f])) as Record<number, File>
  return Object.setPrototypeOf({ ...list, length: files.length, item: (i: number) => files[i] ?? null }, FileList.prototype)
}

function fileOfSize(name: string, bytes: number): File {
  const file = new File(['x'], name, { type: 'audio/mpeg' })
  Object.defineProperty(file, 'size', { value: bytes })
  return file
}

async function uploadAndSubmit(...files: File[]) {
  render(<AddSourceDialog open={true} onOpenChange={vi.fn()} defaultNotebookId="notebook:1" />)
  const uploadTab = screen.getByRole('tab', { name: /sources\.upload/ })
  fireEvent.mouseDown(uploadTab)
  fireEvent.click(uploadTab)
  const input = await waitFor(() => {
    const el = document.querySelector('input[type="file"]') as HTMLInputElement | null
    if (!el) throw new Error('no file input yet')
    return el
  })
  Object.defineProperty(input, 'files', { value: fileList(...files) })
  fireEvent.change(input)
  fireEvent.click(await screen.findByRole('button', { name: 'common.next' }))
  fireEvent.click(await screen.findByRole('button', { name: 'common.next' }))
  fireEvent.click(await screen.findByRole('button', { name: 'common.done' }))
}

describe('AddSourceDialog upload size check (#1477)', () => {
  const lecture = fileOfSize('lecture.mp3', 150 * 1024 * 1024)

  beforeEach(() => {
    vi.clearAllMocks()
    mutateAsync.mockResolvedValue({})
  })

  it("API_URL is the frontend's origin: explains the limit and sends nothing", async () => {
    mockGetApiUrl.mockResolvedValue(window.location.origin)
    await uploadAndSubmit(lecture)

    await waitFor(() => expect(mockToastError).toHaveBeenCalled())
    expect(mockToastError.mock.calls[0][0]).toBe('sources.fileTooLargeForProxy')
    expect(mutateAsync).not.toHaveBeenCalled()
  })

  it("batch upload through the rewrite: names every file over the limit and sends nothing", async () => {
    mockGetApiUrl.mockResolvedValue(window.location.origin)
    const second = fileOfSize('seminar.m4a', 120 * 1024 * 1024)
    await uploadAndSubmit(lecture, second, fileOfSize('notes.pdf', 2 * 1024 * 1024))

    await waitFor(() => expect(mockToastError).toHaveBeenCalled())
    expect(mockToastError.mock.calls[0][0]).toBe('sources.fileTooLargeForProxy')
    expect(mutateAsync).not.toHaveBeenCalled()
  })

  it('API called directly (the default: /config points the browser at <host>:5055): the file goes to the API, which applies its own limit', async () => {
    mockGetApiUrl.mockResolvedValue('http://localhost:5055')
    await uploadAndSubmit(lecture)

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
    expect(mutateAsync.mock.calls[0][0].file).toBe(lecture)
    expect(mockToastError).not.toHaveBeenCalled()
  })
})
