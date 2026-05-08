'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useCanManageTeams } from '@/lib/hooks/use-teams'
import { useAuthStore } from '@/lib/stores/auth-store'

export default function AdvancedPage() {
  const { t } = useTranslation()
  const role = useAuthStore((state) => state.role)
  const canManageTeams = useCanManageTeams()

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle>{t.advanced.teamOwnerOnlyTitle}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {role === 'admin' || !canManageTeams
                  ? t.advanced.teamOwnerOnlyDesc
                  : t.advanced.teamOwnerAdvancedDesc}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
