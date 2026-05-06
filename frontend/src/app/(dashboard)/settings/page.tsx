'use client'

import { SettingsForm } from './components/SettingsForm'
import { useSettings } from '@/lib/hooks/use-settings'
import { useUpdateWorkspaceSystemPolicy, useWorkspaceSystemPolicy } from '@/lib/hooks/use-workspaces'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { RefreshCw, ShieldCheck } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { WorkspacePermissionPolicy } from '@/lib/api/workspaces'

type WorkspacePolicyKey = keyof WorkspacePermissionPolicy

export default function SettingsPage() {
  const { t } = useTranslation()
  const { refetch } = useSettings()

  return (
          <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <div className="max-w-4xl">
            <div className="flex items-center gap-4 mb-6">
              <h1 className="text-2xl font-bold">{t.navigation.settings}</h1>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-6">
              <SettingsForm />
              <WorkspaceSystemPolicyPanel />
            </div>
          </div>
        </div>
      </div>
  )
}

function WorkspaceSystemPolicyPanel() {
  const { t } = useTranslation()
  const { data, isLoading } = useWorkspaceSystemPolicy()
  const updatePolicy = useUpdateWorkspaceSystemPolicy()
  const policy = data?.policy

  const policyItems: Array<{
    key: WorkspacePolicyKey
    label: string
    description: string
  }> = [
    {
      key: 'member_can_read',
      label: t.settings.policyReadWorkspace,
      description: t.settings.policyReadWorkspaceDesc,
    },
    {
      key: 'member_can_create_source',
      label: t.teams.policyCreateSource,
      description: t.teams.policyCreateSourceDesc,
    },
    {
      key: 'member_can_update_own_source',
      label: t.teams.policyUpdateOwnSource,
      description: t.teams.policyUpdateOwnSourceDesc,
    },
    {
      key: 'member_can_process_own_source',
      label: t.teams.policyProcessOwnSource,
      description: t.teams.policyProcessOwnSourceDesc,
    },
    {
      key: 'member_can_delete_own_source',
      label: t.settings.policyDeleteOwnSource,
      description: t.settings.policyDeleteOwnSourceDesc,
    },
    {
      key: 'member_can_remove_source',
      label: t.teams.policyRemoveSource,
      description: t.teams.policyRemoveSourceDesc,
    },
    {
      key: 'member_can_create_note',
      label: t.teams.policyCreateNote,
      description: t.teams.policyCreateNoteDesc,
    },
    {
      key: 'member_can_update_own_note',
      label: t.teams.policyUpdateOwnNote,
      description: t.teams.policyUpdateOwnNoteDesc,
    },
    {
      key: 'member_can_delete_own_note',
      label: t.teams.policyDeleteOwnNote,
      description: t.teams.policyDeleteOwnNoteDesc,
    },
    {
      key: 'member_can_delete_chat',
      label: t.settings.policyDeleteOwnChat,
      description: t.settings.policyDeleteOwnChatDesc,
    },
    {
      key: 'member_can_update_notebook',
      label: t.teams.policyUpdateNotebook,
      description: t.teams.policyUpdateNotebookDesc,
    },
  ]

  const togglePolicy = (key: WorkspacePolicyKey, checked: boolean) => {
    if (!policy) return
    updatePolicy.mutate({
      ...policy,
      [key]: checked,
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start gap-2">
          <ShieldCheck className="mt-1 h-5 w-5 text-muted-foreground" />
          <div>
            <CardTitle>{t.settings.workspaceSystemPolicy}</CardTitle>
            <CardDescription>{t.settings.workspaceSystemPolicyDesc}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex min-h-24 items-center justify-center rounded-md border">
            <LoadingSpinner />
          </div>
        ) : !policy ? (
          <div className="rounded-md border p-4 text-sm text-muted-foreground">
            {t.settings.workspaceSystemPolicyUnavailable}
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {policyItems.map((item) => {
              const inputId = `workspace-system-policy-${item.key}`
              return (
                <div key={item.key} className="rounded-md border p-3">
                  <div className="flex items-start gap-3">
                    <Checkbox
                      id={inputId}
                      checked={policy[item.key]}
                      disabled={updatePolicy.isPending}
                      onCheckedChange={(checked) => togglePolicy(item.key, Boolean(checked))}
                    />
                    <div className="min-w-0">
                      <Label htmlFor={inputId} className="cursor-pointer text-sm font-medium">
                        {item.label}
                      </Label>
                      <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
