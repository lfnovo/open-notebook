'use client'

import { useState, useRef, useEffect, type RefObject } from 'react'
import { cn } from '@/lib/utils'
import { useTranslation } from '@/lib/hooks/use-translation'

interface InlineEditProps {
  value: string
  onSave: (value: string) => void | Promise<void>
  className?: string
  inputClassName?: string
  placeholder?: string
  multiline?: boolean
  emptyText?: string
  id?: string
  name?: string
}

export function InlineEdit({
  value,
  onSave,
  className,
  inputClassName,
  placeholder,
  multiline = false,
  emptyText,
  id,
  name
}: InlineEditProps) {
  const { t } = useTranslation()
  const defaultEmptyText = emptyText || t.common.clickToEdit
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(value)
  const [isSaving, setIsSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null)

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  useEffect(() => {
    setEditValue(value)
  }, [value])

  const handleSave = async () => {
    if (editValue.trim() === value.trim()) {
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    try {
      await onSave(editValue.trim())
      setIsEditing(false)
    } catch {
      // Reset on error
      setEditValue(value)
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setEditValue(value)
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !multiline) {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      handleCancel()
    }
  }

  if (!isEditing) {
    return (
      <button
        type="button"
        className={cn(
          "cursor-pointer hover:bg-muted/50 rounded px-2 py-1 -mx-2 -my-1 transition-colors text-left w-full",
          className
        )}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setIsEditing(true)
        }}
      >
        {value || <span className="text-muted-foreground">{defaultEmptyText}</span>}
      </button>
    )
  }

  if (multiline) {
    return (
      <textarea
        ref={inputRef as RefObject<HTMLTextAreaElement>}
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (!isSaving && editValue.trim() !== value.trim()) {
            handleSave()
          } else if (editValue.trim() === value.trim()) {
            setIsEditing(false)
          }
        }}
        className={cn(
          "px-2 py-1 bg-background border rounded focus:outline-none focus:ring-2 focus:ring-primary w-full",
          "min-h-[60px] resize-none",
          inputClassName
        )}
        placeholder={placeholder}
        disabled={isSaving}
        id={id}
        name={name}
      />
    )
  }

  return (
    <input
      ref={inputRef as RefObject<HTMLInputElement>}
      value={editValue}
      onChange={(e) => setEditValue(e.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={() => {
        if (!isSaving && editValue.trim() !== value.trim()) {
          handleSave()
        } else if (editValue.trim() === value.trim()) {
          setIsEditing(false)
        }
      }}
      className={cn(
        "px-2 py-1 bg-background border rounded focus:outline-none focus:ring-2 focus:ring-primary w-full",
        inputClassName
      )}
      placeholder={placeholder}
      disabled={isSaving}
      id={id}
      name={name}
    />
  )
}
