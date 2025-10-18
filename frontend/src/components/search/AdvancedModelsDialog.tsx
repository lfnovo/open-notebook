'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ModelSelector } from '@/components/common/ModelSelector'

interface AdvancedModelsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultModels: {
    strategy: string
    answer: string
    finalAnswer: string
  }
  onSave: (models: {
    strategy: string
    answer: string
    finalAnswer: string
  }) => void
}

export function AdvancedModelsDialog({
  open,
  onOpenChange,
  defaultModels,
  onSave
}: AdvancedModelsDialogProps) {
  const [strategyModel, setStrategyModel] = useState(defaultModels.strategy)
  const [answerModel, setAnswerModel] = useState(defaultModels.answer)
  const [finalAnswerModel, setFinalAnswerModel] = useState(defaultModels.finalAnswer)

  // Update local state when defaultModels change
  useEffect(() => {
    setStrategyModel(defaultModels.strategy)
    setAnswerModel(defaultModels.answer)
    setFinalAnswerModel(defaultModels.finalAnswer)
  }, [defaultModels])

  const handleSave = () => {
    onSave({
      strategy: strategyModel,
      answer: answerModel,
      finalAnswer: finalAnswerModel
    })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Advanced Model Selection</DialogTitle>
          <DialogDescription>
            Choose specific models for each stage of the Ask process
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <ModelSelector
            label="Strategy Model"
            modelType="language"
            value={strategyModel}
            onChange={setStrategyModel}
            placeholder="Select strategy model"
          />

          <ModelSelector
            label="Answer Model"
            modelType="language"
            value={answerModel}
            onChange={setAnswerModel}
            placeholder="Select answer model"
          />

          <ModelSelector
            label="Final Answer Model"
            modelType="language"
            value={finalAnswerModel}
            onChange={setFinalAnswerModel}
            placeholder="Select final answer model"
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
