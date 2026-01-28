'use client'

import { useState } from 'react'
import { ModuleResponse } from '@/lib/types/api'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useCoursesStore } from '@/lib/stores/courses-store'
import { useUpdateModule } from '@/lib/hooks/use-modules'
import { Plus, X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ModuleDetailsProps {
  module: ModuleResponse
}

export function ModuleDetails({ module }: ModuleDetailsProps) {
  const { t } = useTranslation()
  const updateModule = useUpdateModule()
  const { getModuleMetadata, updateModuleMetadata } = useCoursesStore()
  
  const metadata = getModuleMetadata(module.id)
  const [overview, setOverview] = useState(metadata.overview || '')
  const [dueDate, setDueDate] = useState(metadata.dueDate || '')
  const [prerequisites, setPrerequisites] = useState(metadata.prerequisites || '')
  const [learningGoals, setLearningGoals] = useState<string[]>(metadata.learningGoals || [])

  const handleSaveOverview = () => {
    updateModuleMetadata(module.id, { overview })
  }

  const handleSaveDueDate = () => {
    updateModuleMetadata(module.id, { dueDate })
  }

  const handleSavePrerequisites = () => {
    updateModuleMetadata(module.id, { prerequisites })
  }

  const handleAddLearningGoal = () => {
    const newGoals = [...learningGoals, '']
    setLearningGoals(newGoals)
  }

  const handleUpdateLearningGoal = (index: number, value: string) => {
    const newGoals = [...learningGoals]
    newGoals[index] = value
    setLearningGoals(newGoals)
    updateModuleMetadata(module.id, { learningGoals: newGoals })
  }

  const handleRemoveLearningGoal = (index: number) => {
    const newGoals = learningGoals.filter((_, i) => i !== index)
    setLearningGoals(newGoals)
    updateModuleMetadata(module.id, { learningGoals: newGoals })
  }

  return (
    <div className="space-y-6">
      {/* Module Information Section */}
      <Card>
        <CardHeader>
          <CardTitle>Module Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="module-name">Name</Label>
            <Input
              id="module-name"
              value={module.name}
              onChange={(e) => {
                updateModule.mutate({
                  id: module.id,
                  data: { name: e.target.value },
                })
              }}
              placeholder="Module name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="module-overview">Overview</Label>
            <Textarea
              id="module-overview"
              value={overview}
              onChange={(e) => setOverview(e.target.value)}
              onBlur={handleSaveOverview}
              placeholder="Enter module overview..."
              rows={6}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="module-due-date">Due Date</Label>
              <Input
                id="module-due-date"
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                onBlur={handleSaveDueDate}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="module-prerequisites">Prerequisites</Label>
              <Input
                id="module-prerequisites"
                value={prerequisites}
                onChange={(e) => setPrerequisites(e.target.value)}
                onBlur={handleSavePrerequisites}
                placeholder="e.g., CS 101, MATH 201"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Learning Goals Section */}
      <Card>
        <CardHeader>
          <CardTitle>Learning Goals</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {learningGoals.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No learning goals yet. Click &quot;Add Learning Goal&quot; to get started.
            </p>
          ) : (
            <div className="space-y-3">
              {learningGoals.map((goal, index) => (
                <div key={index} className="flex items-start gap-2">
                  <Input
                    value={goal}
                    onChange={(e) => handleUpdateLearningGoal(index, e.target.value)}
                    placeholder={`Learning goal ${index + 1}`}
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveLearningGoal(index)}
                    className="h-10 w-10 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
          <Button
            type="button"
            variant="outline"
            onClick={handleAddLearningGoal}
            className="w-full"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Learning Goal
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
