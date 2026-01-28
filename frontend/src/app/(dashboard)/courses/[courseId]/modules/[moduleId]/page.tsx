'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'

import { AppShell } from '@/components/layout/AppShell'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useModule } from '@/lib/hooks/use-modules'
import { AddSourceDialog } from '@/components/sources/AddSourceDialog'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import Link from 'next/link'

function buildPlaceholderOverview(moduleName: string) {
  return {
    summary: `This module introduces the core ideas of ${moduleName} and prepares students for deeper application and assessment.`,
    takeaways: [
      'Students can explain the high-level motivation for the topic in their own words.',
      'Students can connect the new concepts to prior material from the course.',
      'Students can identify common pitfalls or misconceptions related to this module.',
    ],
    competencies: [
      'Conceptual understanding of the main ideas and vocabulary.',
      'Ability to apply the concepts to small, concrete examples.',
      'Readiness to move on to more open-ended or project-based work.',
    ],
  }
}

export default function CourseModuleOverviewPage() {
  const params = useParams()
  const courseId = params?.courseId ? decodeURIComponent(params.courseId as string) : ''
  const moduleId = params?.moduleId ? decodeURIComponent(params.moduleId as string) : ''

  const { data: module, isLoading } = useModule(moduleId)
  const [uploadOpen, setUploadOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!module) {
    return (
      <AppShell>
        <div className="p-6">
          <h1 className="text-2xl font-bold mb-2">Module not found</h1>
          <p className="text-muted-foreground mb-4">
            This module could not be loaded. It may have been deleted or is unavailable.
          </p>
          <Button asChild>
            <Link href={`/courses/${encodeURIComponent(courseId)}`}>Back to course</Link>
          </Button>
        </div>
      </AppShell>
    )
  }

  const overview = buildPlaceholderOverview(module.name)

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">{module.name}</h1>
              {module.description && (
                <p className="text-muted-foreground">{module.description}</p>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" asChild>
                <Link href={`/courses/${encodeURIComponent(courseId)}`}>Back to course</Link>
              </Button>
              <Button onClick={() => setUploadOpen(true)}>
                Upload documents
              </Button>
            </div>
          </div>

          {/* Overview card */}
          <Card>
            <CardHeader>
              <CardTitle>Module Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{overview.summary}</p>
            </CardContent>
          </Card>

          {/* Learning goals */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Key Takeaways</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc pl-5 space-y-2 text-sm">
                  {overview.takeaways.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Competencies</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc pl-5 space-y-2 text-sm">
                  {overview.competencies.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          {/* Placeholder for future metrics/insights */}
          <Card>
            <CardHeader>
              <CardTitle>Student Understanding</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                AI-generated metrics and insights about student understanding will appear here once
                the evaluation pipeline is wired up.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      <AddSourceDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        defaultModuleId={moduleId}
      />
    </AppShell>
  )
}

