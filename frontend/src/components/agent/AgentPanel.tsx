'use client'

import React, { useState, useEffect, useRef } from 'react'
import { 
  Bot, 
  Send, 
  Loader2, 
  Wrench, 
  Brain, 
  CheckCircle, 
  XCircle,
  Trash2,
  Key,
  ChevronDown,
  ChevronRight,
  Sparkles,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'
import { useAgent, AgentStep, AgentConversationMessage } from '@/lib/hooks/useAgent'
import ReactMarkdown from 'react-markdown'

interface AgentPanelProps {
  notebookId?: string
  className?: string
}

// Step icon component
function StepIcon({ type }: { type: AgentStep['type'] }) {
  switch (type) {
    case 'thinking':
      return <Brain className="h-4 w-4 text-blue-500 animate-pulse" />
    case 'tool_call':
      return <Wrench className="h-4 w-4 text-orange-500" />
    case 'tool_result':
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case 'response':
      return <Sparkles className="h-4 w-4 text-purple-500" />
    case 'error':
      return <XCircle className="h-4 w-4 text-red-500" />
    default:
      return null
  }
}

// Step item component
function StepItem({ step, isLast }: { step: AgentStep; isLast: boolean }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className={cn(
      "flex gap-2 py-2",
      !isLast && "border-b border-muted"
    )}>
      <div className="flex-shrink-0 mt-0.5">
        <StepIcon type={step.type} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {step.type === 'thinking' && '思考中'}
            {step.type === 'tool_call' && `调用工具: ${step.tool}`}
            {step.type === 'tool_result' && `工具结果: ${step.tool}`}
            {step.type === 'response' && '生成回答'}
            {step.type === 'error' && '错误'}
          </span>
          <span className="text-xs text-muted-foreground">
            {step.timestamp.toLocaleTimeString()}
          </span>
        </div>
        
        {/* Tool input/output details */}
        {(step.toolInput || step.toolOutput) && (
          <Collapsible open={isOpen} onOpenChange={setIsOpen}>
            <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mt-1">
              {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              查看详情
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              {step.toolInput && (
                <div className="text-xs bg-muted rounded p-2 mb-1">
                  <div className="font-medium mb-1">输入:</div>
                  <pre className="whitespace-pre-wrap overflow-x-auto">
                    {JSON.stringify(step.toolInput, null, 2)}
                  </pre>
                </div>
              )}
              {step.toolOutput && (
                <div className="text-xs bg-muted rounded p-2">
                  <div className="font-medium mb-1">输出:</div>
                  <pre className="whitespace-pre-wrap overflow-x-auto max-h-40 overflow-y-auto">
                    {step.toolOutput}
                  </pre>
                </div>
              )}
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  )
}

// Message component
function MessageItem({ message }: { message: AgentConversationMessage }) {
  const [showSteps, setShowSteps] = useState(false)

  return (
    <div className={cn(
      "flex gap-3 py-4",
      message.role === 'user' ? "justify-end" : "justify-start"
    )}>
      {message.role === 'assistant' && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            <Bot className="h-5 w-5 text-primary" />
          </div>
        </div>
      )}
      
      <div className={cn(
        "max-w-[80%] rounded-lg px-4 py-2",
        message.role === 'user' 
          ? "bg-primary text-primary-foreground" 
          : "bg-muted"
      )}>
        {message.role === 'assistant' && message.steps && message.steps.length > 0 && (
          <Collapsible open={showSteps} onOpenChange={setShowSteps}>
            <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-2">
              {showSteps ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              执行步骤 ({message.steps.length})
            </CollapsibleTrigger>
            <CollapsibleContent className="mb-3 border-b pb-3">
              {message.steps.map((step, idx) => (
                <StepItem 
                  key={step.id} 
                  step={step} 
                  isLast={idx === message.steps!.length - 1}
                />
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
        
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        
        <div className="text-xs text-muted-foreground mt-2">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
      
      {message.role === 'user' && (
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
            <span className="text-sm font-medium">你</span>
          </div>
        </div>
      )}
    </div>
  )
}

// Current execution steps display
function CurrentSteps({ steps }: { steps: AgentStep[] }) {
  if (steps.length === 0) return null

  return (
    <Card className="mb-4 border-dashed border-primary/50">
      <CardHeader className="py-2 px-4">
        <CardTitle className="text-sm flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          执行中...
        </CardTitle>
      </CardHeader>
      <CardContent className="py-2 px-4">
        {steps.map((step, idx) => (
          <StepItem 
            key={step.id} 
            step={step} 
            isLast={idx === steps.length - 1}
          />
        ))}
      </CardContent>
    </Card>
  )
}

// Main Agent Panel component
export function AgentPanel({ notebookId, className }: AgentPanelProps) {
  const [input, setInput] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    currentSteps,
    isRunning,
    error,
    models,
    selectedModel,
    sendMessage,
    clearConversation,
    loadModels,
    setSelectedModel,
  } = useAgent({
    notebookId,
    apiKey: apiKey || undefined,
  })

  // Load models on mount
  useEffect(() => {
    loadModels()
  }, [loadModels])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentSteps])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isRunning) {
      sendMessage(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <span className="font-semibold">研究助手</span>
          <Badge variant="secondary" className="text-xs">Agent</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowApiKey(!showApiKey)}
            title="设置 API Key"
          >
            <Key className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearConversation}
            title="清空对话"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* API Key & Model Settings */}
      {showApiKey && (
        <div className="px-4 py-3 border-b bg-muted/50 space-y-2">
          <div className="flex gap-2">
            <Input
              type="password"
              placeholder="输入 API Key (DeepSeek / Qwen)"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="flex-1"
            />
          </div>
          <div className="flex gap-2 items-center">
            <span className="text-sm text-muted-foreground">模型:</span>
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="选择模型" />
              </SelectTrigger>
              <SelectContent>
                {models.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    <div className="flex items-center gap-2">
                      <span>{model.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {model.provider}
                      </Badge>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
            <Bot className="h-12 w-12 mb-4 opacity-50" />
            <h3 className="font-medium mb-2">研究助手</h3>
            <p className="text-sm max-w-sm">
              我可以帮你搜索知识库、分析来源、整理笔记。
              <br />
              试试说: "帮我搜索关于XXX的内容"
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))}
            
            {/* Current execution steps */}
            {isRunning && <CurrentSteps steps={currentSteps} />}
            
            <div ref={messagesEndRef} />
          </>
        )}

        {/* Error display */}
        {error && (
          <div className="flex items-center gap-2 text-red-500 text-sm mt-2">
            <XCircle className="h-4 w-4" />
            {error}
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="px-4 py-3 border-t">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            placeholder="输入研究任务..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[44px] max-h-32 resize-none"
            disabled={isRunning}
            rows={1}
          />
          <Button 
            type="submit" 
            disabled={!input.trim() || isRunning}
            className="self-end"
          >
            {isRunning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  )
}
