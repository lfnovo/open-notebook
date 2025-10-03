"use client"

import { ReactNode } from "react"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

interface FormSectionProps {
  title: string
  description?: string
  children: ReactNode
  className?: string
}

export function FormSection({
  title,
  description,
  children,
  className
}: FormSectionProps) {
  return (
    <div className={cn("mb-6 last:mb-0", className)}>
      <div className="mb-4">
        <Label className="text-base font-medium block mb-1">
          {title}
        </Label>
        {description && (
          <p className="text-sm text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  )
}
