import type { ComponentProps } from 'react'
import { render, screen } from '@testing-library/react'
import { useForm, type Control } from 'react-hook-form'
import { describe, expect, it } from 'vitest'
import { SourceTypeStep } from './SourceTypeStep'

// The form shape SourceTypeStep expects (its interface isn't exported)
type FormValues = ComponentProps<typeof SourceTypeStep>['control'] extends Control<infer T> ? T : never

function UploadStep() {
  const { control, register, setValue, formState: { errors } } = useForm<FormValues>({
    defaultValues: { type: 'upload', embed: false, async_processing: false },
  })
  return <SourceTypeStep control={control} register={register} setValue={setValue} errors={errors} />
}

describe('SourceTypeStep', () => {
  it('does not offer archive files in the upload picker', () => {
    render(<UploadStep />)

    const accept = screen.getByLabelText('sources.fileLabel').getAttribute('accept') ?? ''
    const extensions = accept.split(',')

    expect(extensions).not.toContain('.zip')
    expect(extensions).not.toContain('.tar')
    expect(extensions).not.toContain('.gz')
    expect(extensions).toContain('.pdf')
  })
})
