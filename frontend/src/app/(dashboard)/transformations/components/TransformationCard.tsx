'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ChevronDown, ChevronRight, MoreHorizontal, Trash2, Wand2 } from 'lucide-react'
import { Transformation } from '@/lib/types/transformations'
import { useUpdateTransformation, useDeleteTransformation } from '@/lib/hooks/use-transformations'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'

interface TransformationCardProps {
  transformation: Transformation
  isExpanded: boolean
  onPlayground?: () => void
}

export function TransformationCard({ transformation, isExpanded: initialExpanded, onPlayground }: TransformationCardProps) {
  const [isExpanded, setIsExpanded] = useState(initialExpanded)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  
  const [name, setName] = useState(transformation.name)
  const [title, setTitle] = useState(transformation.title)
  const [description, setDescription] = useState(transformation.description)
  const [prompt, setPrompt] = useState(transformation.prompt)
  const [applyDefault, setApplyDefault] = useState(transformation.apply_default)
  
  const updateTransformation = useUpdateTransformation()
  const deleteTransformation = useDeleteTransformation()

  const handleSave = () => {
    updateTransformation.mutate({
      id: transformation.id,
      data: {
        name,
        title,
        description,
        prompt,
        apply_default: applyDefault
      }
    })
  }

  const handleDelete = () => {
    deleteTransformation.mutate(transformation.id)
    setShowDeleteDialog(false)
  }

  const hasChanges = 
    name !== transformation.name ||
    title !== transformation.title ||
    description !== transformation.description ||
    prompt !== transformation.prompt ||
    applyDefault !== transformation.apply_default

  return (
    <>
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CollapsibleTrigger className="flex-1 cursor-pointer text-left">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    {isExpanded ? (
                      <ChevronDown className="h-5 w-5" />
                    ) : (
                      <ChevronRight className="h-5 w-5" />
                    )}
                    <span className="font-semibold">{transformation.name}</span>
                    {transformation.apply_default && (
                      <Badge variant="secondary">default</Badge>
                    )}
                  </div>
                  {!isExpanded && transformation.description && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {transformation.description}
                    </p>
                  )}
                </div>
              </CollapsibleTrigger>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="ghost" size="sm">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="end" className="w-48">
                  <div className="space-y-1">
                    {onPlayground && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => {
                          onPlayground()
                          setIsExpanded(false)
                        }}
                      >
                        <Wand2 className="h-4 w-4 mr-2" />
                        Use in Playground
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start text-red-600 hover:text-red-700"
                      onClick={() => setShowDeleteDialog(true)}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </CardHeader>
          
          <CollapsibleContent>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor={`${transformation.id}-name`}>Transformation Name</Label>
                <Input
                  id={`${transformation.id}-name`}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter transformation name"
                />
              </div>

              <div>
                <Label htmlFor={`${transformation.id}-title`}>
                  Card Title
                  <span className="text-sm text-muted-foreground ml-2">
                    (title of cards created by this transformation)
                  </span>
                </Label>
                <Input
                  id={`${transformation.id}-title`}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., 'Key Topics'"
                />
              </div>

              <div>
                <Label htmlFor={`${transformation.id}-description`}>
                  Description
                  <span className="text-sm text-muted-foreground ml-2">
                    (displayed as a hint in the UI)
                  </span>
                </Label>
                <Textarea
                  id={`${transformation.id}-description`}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe what this transformation does..."
                  rows={2}
                />
              </div>

              <div>
                <Label htmlFor={`${transformation.id}-prompt`}>Prompt</Label>
                <Textarea
                  id={`${transformation.id}-prompt`}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Enter your transformation prompt..."
                  rows={8}
                  className="font-mono text-sm"
                />
                <p className="text-sm text-muted-foreground mt-2">
                  You can use the prompt to summarize, expand, extract insights and much more. 
                  Example: `Translate this text to French`. For inspiration, check out this{' '}
                  <a 
                    href="https://github.com/danielmiessler/fabric/tree/main/patterns"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    great resource
                  </a>.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id={`${transformation.id}-apply-default`}
                  checked={applyDefault}
                  onCheckedChange={(checked) => setApplyDefault(checked as boolean)}
                />
                <Label 
                  htmlFor={`${transformation.id}-apply-default`}
                  className="text-sm font-normal cursor-pointer"
                >
                  Suggest by default on new sources
                </Label>
              </div>

              <div className="flex justify-end">
                <Button 
                  onClick={handleSave}
                  disabled={!hasChanges || updateTransformation.isPending}
                >
                  {updateTransformation.isPending ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Transformation"
        description={`Are you sure you want to delete "${transformation.name}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmVariant="destructive"
        onConfirm={handleDelete}
      />
    </>
  )
}