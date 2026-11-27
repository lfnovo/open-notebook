'use client'

import { useState } from 'react'

import { ArtifactForm, ArtifactFormValues } from '@/components/artifacts/ArtifactForm'
import { ArtifactList } from '@/components/artifacts/ArtifactList'
import { AppShell } from '@/components/layout/AppShell'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useArtifacts,
  useDeleteArtifact,
  useGenerateArtifact,
} from '@/lib/hooks/use-artifacts'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useTranslation } from '@/lib/hooks/use-translation'

export default function ArtifactsPage() {
  const { t } = useTranslation()
  const { data: notebooks } = useNotebooks()
  const [notebookId, setNotebookId] = useState<string | undefined>(undefined)
  const { artifacts } = useArtifacts({ notebookId })
  const generate = useGenerateArtifact()
  const remove = useDeleteArtifact()

  function handleSubmit(values: ArtifactFormValues) {
    setNotebookId(values.notebookId)
    generate.mutate({
      notebook_id: values.notebookId,
      kind: values.kind,
      variant: values.variant,
      title: values.title || undefined,
      formats: values.formats,
      language: values.language,
      sections: values.sections,
    })
  }

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-4xl flex-1 overflow-y-auto space-y-6 p-6">
        <header className="space-y-1">
          <h1 className="font-display text-2xl font-semibold">
            {t('artifacts.title')}
          </h1>
          <p className="text-sm text-muted-foreground">{t('artifacts.subtitle')}</p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>{t('artifacts.formTitle')}</CardTitle>
          </CardHeader>
          <CardContent>
            <ArtifactForm
              notebooks={(notebooks ?? []).map((notebook) => ({
                id: notebook.id,
                name: notebook.name,
              }))}
              submitting={generate.isPending}
              onSubmit={handleSubmit}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('artifacts.listTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <ArtifactList
              artifacts={artifacts}
              onDelete={(artifactId) => remove.mutate(artifactId)}
              deletingId={remove.isPending ? (remove.variables ?? null) : null}
            />
          </CardContent>
        </Card>
      </div>
    </AppShell>
  )
}
