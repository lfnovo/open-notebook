import { render, screen } from '@testing-library/react'
import { useForm } from 'react-hook-form'
import { describe, expect, it } from 'vitest'

import { SourceTypeStep } from './SourceTypeStep'

type FormData = {
  type: 'link' | 'upload' | 'text' | 'external'
  title?: string
  url?: string
  content?: string
  file?: FileList | File
  notebooks?: string[]
  transformations?: string[]
  embed: boolean
  async_processing: boolean
  visibility: 'private' | 'public'
}

function SourceTypeStepHarness({ defaultType = 'link' }: { defaultType?: FormData['type'] }) {
  const form = useForm<FormData>({
    defaultValues: {
      type: defaultType,
      embed: true,
      async_processing: true,
      visibility: 'private',
    },
  })

  return (
    <SourceTypeStep
      control={form.control}
      register={form.register}
      setValue={form.setValue}
      errors={form.formState.errors}
      externalSourceContent={<div>Connected source panel</div>}
    />
  )
}

describe('SourceTypeStep', () => {
  it('does not repeat a standalone sources heading above the source type tabs', () => {
    render(<SourceTypeStepHarness />)

    expect(screen.queryByRole('heading', { name: /^Sources$/i })).not.toBeInTheDocument()
  })

  it('shows connected source as a peer source type tab', async () => {
    render(<SourceTypeStepHarness />)

    expect(screen.getByRole('tab', { name: /Add URL/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Upload File/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /Enter Text/i })).toBeInTheDocument()

    const connectedTab = screen.getByRole('tab', { name: /Deep Search/i })
    expect(connectedTab).toBeInTheDocument()

    render(<SourceTypeStepHarness defaultType="external" />)

    expect(screen.getByText('Connected source panel')).toBeInTheDocument()
  })
})
