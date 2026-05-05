'use client'

import { useId } from 'react'
import { CheckCircle2 } from 'lucide-react'

interface OperationGuideProps {
  title: string
  description?: string
  steps: string[]
}

export function OperationGuide({ title, description, steps }: OperationGuideProps) {
  const headingId = useId()

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-md border bg-muted/20 p-4"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 id={headingId} className="text-sm font-semibold tracking-normal">
            {title}
          </h2>
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      <ol className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
        {steps.map((step, index) => (
          <li key={`${index}-${step}`} className="flex min-w-0 items-start gap-2">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="min-w-0">{step}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
