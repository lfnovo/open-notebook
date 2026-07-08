import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RepoBrowseButton, joinRepoPath } from './RepoBrowseButton'

function selectFolder(fileInput: HTMLInputElement, relativePath: string) {
  const file = new File(['content'], relativePath.split('/').pop() as string)
  Object.defineProperty(file, 'webkitRelativePath', { value: relativePath })
  fireEvent.change(fileInput, { target: { files: [file] } })
}

describe('joinRepoPath', () => {
  it('joins a root and folder name with exactly one slash', () => {
    expect(joinRepoPath('/data/repos', 'my-project')).toBe('/data/repos/my-project')
    expect(joinRepoPath('/data/repos/', 'my-project')).toBe('/data/repos/my-project')
  })
})

describe('RepoBrowseButton', () => {
  it('does not show a root selector with a single allowed root', () => {
    render(<RepoBrowseButton allowedRoots={['/data/repos']} onPick={vi.fn()} />)
    expect(screen.queryByText('reviewPage.repoPathBrowseRoot')).not.toBeInTheDocument()
  })

  it('joins the picked folder name with the single allowed root', () => {
    const onPick = vi.fn()
    render(<RepoBrowseButton allowedRoots={['/data/repos']} onPick={onPick} />)

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    selectFolder(fileInput, 'my-project/src/app.py')

    expect(onPick).toHaveBeenCalledWith('/data/repos/my-project')
  })

  it('shows a root selector defaulting to the first root when multiple roots are configured', () => {
    const onPick = vi.fn()
    render(<RepoBrowseButton allowedRoots={['/data/repos', '/data/work']} onPick={onPick} />)

    expect(screen.getByText('/data/repos')).toBeInTheDocument()

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    selectFolder(fileInput, 'my-project/src/app.py')

    expect(onPick).toHaveBeenCalledWith('/data/repos/my-project')
  })
})
