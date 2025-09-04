"use client"

import { Checkbox } from "@/components/ui/checkbox"
import { cn } from "@/lib/utils"

interface CheckboxListItem {
  id: string
  title: string
  description?: string
}

interface CheckboxListProps {
  items: CheckboxListItem[]
  selectedIds: string[]
  onToggle: (id: string) => void
  loading?: boolean
  emptyMessage?: string
  className?: string
}

export function CheckboxList({
  items,
  selectedIds,
  onToggle,
  loading = false,
  emptyMessage = "No items found.",
  className
}: CheckboxListProps) {
  if (loading) {
    return (
      <div className={cn("border rounded-md p-4 bg-gray-50", className)}>
        <div className="animate-pulse space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-4 h-4 bg-gray-200 rounded"></div>
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-1"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className={cn("border rounded-md p-4 bg-gray-50", className)}>
        <p className="text-sm text-gray-500">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={cn("border rounded-md bg-gray-50", className)}>
      <div className="max-h-48 overflow-y-auto p-4">
        <div className="space-y-3">
          {items.map((item) => (
            <label
              key={item.id}
              className="flex items-start gap-3 cursor-pointer hover:bg-gray-100 p-2 rounded-md -m-2"
            >
              <Checkbox
                checked={selectedIds.includes(item.id)}
                onCheckedChange={() => onToggle(item.id)}
                className="mt-0.5"
              />
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium block">
                  {item.title}
                </span>
                {item.description && (
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                    {item.description}
                  </p>
                )}
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}