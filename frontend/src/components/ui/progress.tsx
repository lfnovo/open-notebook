"use client"

import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"

import { cn } from "@/lib/utils"
import { useDirection } from "@/components/ui/directional-icons"

function Progress({
  className,
  value,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  const isRTL = useDirection() === 'rtl'

  const max = props.max || 100
  const clampedValue = Math.min(Math.max(value || 0, 0), max)
  const percentage = (clampedValue / max) * 100

  // In LTR: fill left-to-right (translateX from -100% to 0%)
  // In RTL: fill right-to-left (translateX from +100% to 0%)
  const transform = isRTL
    ? `translateX(${100 - percentage}%)`
    : `translateX(-${100 - percentage}%)`

  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn(
        "bg-primary/20 relative h-2 w-full overflow-hidden rounded-full",
        className
      )}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="bg-primary h-full w-full flex-1 transition-all"
        style={{ transform }}
      />
    </ProgressPrimitive.Root>
  )
}

export { Progress }
