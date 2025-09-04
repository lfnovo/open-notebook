"use client"

import { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface WizardStep {
  number: number
  title: string
  description: string
}

interface WizardContainerProps {
  children: ReactNode
  currentStep: number
  steps: readonly WizardStep[]
  onStepClick?: (step: number) => void
  className?: string
}

function StepIndicator({ currentStep, steps, onStepClick }: {
  currentStep: number
  steps: readonly WizardStep[]
  onStepClick?: (step: number) => void
}) {
  return (
    <div className="flex items-center justify-between px-6 py-4 border-b bg-gray-50">
      {steps.map((step, index) => {
        const isCompleted = currentStep > step.number
        const isCurrent = currentStep === step.number
        const isClickable = step.number <= currentStep && onStepClick
        
        return (
          <div key={step.number} className="flex items-center flex-1">
            <div 
              className={`flex items-center ${isClickable ? 'cursor-pointer' : ''}`}
              onClick={isClickable ? () => onStepClick(step.number) : undefined}
            >
              <div
                className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-full border-2 text-sm font-medium transition-colors",
                  isCompleted 
                    ? "bg-blue-600 border-blue-600 text-white" 
                    : isCurrent 
                      ? "border-blue-600 text-blue-600 bg-blue-50"
                      : "border-gray-300 text-gray-400 bg-white"
                )}
              >
                {isCompleted ? "✓" : step.number}
              </div>
              <div className="ml-3 min-w-0">
                <p className={cn(
                  "text-sm font-medium",
                  isCurrent ? "text-gray-900" : "text-gray-500"
                )}>
                  {step.title}
                </p>
                <p className={cn(
                  "text-xs",
                  isCurrent ? "text-gray-600" : "text-gray-400"
                )}>
                  {step.description}
                </p>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div 
                className={cn(
                  "flex-1 border-t-2 mx-4 transition-colors",
                  isCompleted ? "border-blue-600" : "border-gray-300"
                )} 
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export function WizardContainer({
  children,
  currentStep,
  steps,
  onStepClick,
  className
}: WizardContainerProps) {
  return (
    <div className={cn("flex flex-col h-[500px] bg-white rounded-lg border", className)}>
      <StepIndicator 
        currentStep={currentStep}
        steps={steps}
        onStepClick={onStepClick}
      />
      
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto px-6 py-4">
          {children}
        </div>
      </div>
    </div>
  )
}

export type { WizardStep }