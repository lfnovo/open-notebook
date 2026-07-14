"use client"

import { useCallback, useState } from "react"
import { useTranslation } from "@/lib/hooks/use-translation"
import { useNotebooks } from "@/lib/hooks/use-notebooks"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import { ChevronDown, X } from "lucide-react"

interface NotebookMultiSelectProps {
  selectedIds: string[]
  onChange: (ids: string[]) => void
  disabled?: boolean
}

export function NotebookMultiSelect({
  selectedIds,
  onChange,
  disabled = false,
}: NotebookMultiSelectProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: notebooks, isLoading } = useNotebooks()

  const activeNotebooks = notebooks?.filter((n) => !n.archived) ?? []

  const toggleNotebook = useCallback(
    (id: string) => {
      if (selectedIds.includes(id)) {
        onChange(selectedIds.filter((sid) => sid !== id))
      } else {
        onChange([...selectedIds, id])
      }
    },
    [selectedIds, onChange]
  )

  const clearAll = useCallback(() => {
    onChange([])
  }, [onChange])

  const selectedLabels = activeNotebooks
    .filter((n) => selectedIds.includes(n.id))
    .map((n) => n.name)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled || isLoading}
          className={cn(
            "w-full justify-between h-auto min-h-9 py-1.5",
            !selectedIds.length && "text-muted-foreground"
          )}
        >
          <div className="flex flex-wrap gap-1 items-center flex-1">
            {selectedIds.length === 0 ? (
              <span className="text-sm">{t("searchPage.allNotebooks")}</span>
            ) : (
              selectedLabels.slice(0, 3).map((label) => (
                <Badge key={label} variant="secondary" className="text-xs">
                  {label}
                </Badge>
              ))
            )}
            {selectedIds.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{selectedIds.length - 3}
              </Badge>
            )}
          </div>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-50 ml-2" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command>
          <CommandInput placeholder={t("searchPage.searchNotebooks")} />
          <CommandEmpty>{t("notebooks.noNotebooksFound")}</CommandEmpty>
          <CommandList>
            <CommandGroup>
              {activeNotebooks.map((notebook) => (
                <CommandItem
                  key={notebook.id}
                  value={notebook.name}
                  onSelect={() => toggleNotebook(notebook.id)}
                  className="cursor-pointer"
                >
                  <Checkbox
                    checked={selectedIds.includes(notebook.id)}
                    className="mr-2"
                  />
                  {notebook.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
        {selectedIds.length > 0 && (
          <div className="border-t border-border p-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAll}
              className="w-full text-xs h-7"
            >
              <X className="h-3 w-3 mr-1" />
              {t("searchPage.clearFilter")}
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
