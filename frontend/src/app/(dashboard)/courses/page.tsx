'use client'

import Link from 'next/link'

import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCoursesStore } from '@/lib/stores/courses-store'

export default function CoursesPage() {
  const { courses, createCourse } = useCoursesStore()

  const handleCreateCourse = () => {
    // For now create a simple untitled course; instructor can rename later
    const count = courses.length + 1
    createCourse(`New Course ${count}`)
  }

  const activeCourses = courses.filter((course) => !course.archived)

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Courses</h1>
              <p className="text-muted-foreground">
                Select a course to review modules and student understanding.
              </p>
            </div>
            <Button onClick={handleCreateCourse}>
              + Create New Course
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {activeCourses.map((course) => (
              <Link key={course.id} href={`/courses/${encodeURIComponent(course.id)}`}>
                <Card className="h-full cursor-pointer transition-colors hover:bg-muted">
                  <CardHeader>
                    <CardTitle className="text-lg">
                      {course.name}
                    </CardTitle>
                    {course.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {course.description}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">
                      Last updated {new Date(course.updatedAt).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}

            {activeCourses.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No courses yet. Use &quot;Create New Course&quot; to get started.
              </p>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}

