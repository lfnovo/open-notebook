'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Play, Loader2 } from 'lucide-react'
import { Transformation } from '@/lib/types/transformations'
import { useExecuteTransformation } from '@/lib/hooks/use-transformations'
import { ModelSelector } from '@/components/common/ModelSelector'
import ReactMarkdown from 'react-markdown'

interface TransformationPlaygroundProps {
  transformations: Transformation[] | undefined
  selectedTransformation?: Transformation
}

export function TransformationPlayground({ transformations, selectedTransformation }: TransformationPlaygroundProps) {
  const [selectedId, setSelectedId] = useState(selectedTransformation?.id || '')
  const [inputText, setInputText] = useState('')
  const [modelId, setModelId] = useState('')
  const [output, setOutput] = useState('')
  
  const executeTransformation = useExecuteTransformation()

  const handleExecute = async () => {
    if (!selectedId || !modelId || !inputText.trim()) {
      return
    }

    const result = await executeTransformation.mutateAsync({
      transformation_id: selectedId,
      input_text: inputText,
      model_id: modelId
    })

    setOutput(result.output)
  }

  const canExecute = selectedId && modelId && inputText.trim() && !executeTransformation.isPending

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Playground</CardTitle>
          <CardDescription>
            Test your transformations on sample text before applying them to your sources
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="transformation">Transformation</Label>
              <Select value={selectedId} onValueChange={setSelectedId}>
                <SelectTrigger id="transformation">
                  <SelectValue placeholder="Select a transformation" />
                </SelectTrigger>
                <SelectContent>
                  {transformations?.map((transformation) => (
                    <SelectItem key={transformation.id} value={transformation.id}>
                      {transformation.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <ModelSelector
                label="Model"
                modelType="language"
                value={modelId}
                onChange={setModelId}
                placeholder="Select a model"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="input">Input Text</Label>
            <Textarea
              id="input"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter some text to transform..."
              rows={8}
              className="font-mono text-sm"
            />
          </div>

          <div className="flex justify-center">
            <Button 
              onClick={handleExecute}
              disabled={!canExecute}
              size="lg"
            >
              {executeTransformation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Run Transformation
                </>
              )}
            </Button>
          </div>

          {output && (
            <div className="space-y-2">
              <Label>Output</Label>
              <Card>
                <ScrollArea className="h-[400px]">
                  <CardContent className="pt-6">
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown>{output}</ReactMarkdown>
                    </div>
                  </CardContent>
                </ScrollArea>
              </Card>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}