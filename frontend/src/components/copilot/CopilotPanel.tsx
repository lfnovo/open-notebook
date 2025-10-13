import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2, Sparkles, Wand2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { apiClient } from '@/lib/api-client';
import type { AskResponse, ContextResponse, DefaultModelsResponse } from '@/types/api';

type CopilotMode = 'ask' | 'edit';

type CopilotMessage = {
  id: string;
  role: 'user' | 'assistant';
  mode: CopilotMode;
  content: string;
  createdAt: string;
};

const buildContextSummary = (context?: ContextResponse) => {
  if (!context) return 'No additional notebook context provided.';
  const sources = context.sources?.slice(0, 5) ?? [];
  const notes = context.notes?.slice(0, 5) ?? [];
  const sourcesText = sources
    .map((source, index) => `(${index + 1}) ${JSON.stringify(source)}`)
    .join('\n');
  const notesText = notes
    .map((note, index) => `(${index + 1}) ${JSON.stringify(note)}`)
    .join('\n');

  return `Sources:\n${sourcesText}\n\nNotes:\n${notesText}`;
};

interface CopilotPanelProps {
  notebookId: string;
  draft: string;
  onDraftUpdate?: (markdown: string) => void;
  context?: ContextResponse;
}

const CopilotPanel = ({ notebookId, draft, onDraftUpdate, context }: CopilotPanelProps) => {
  const [mode, setMode] = useState<CopilotMode>('ask');
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<CopilotMessage[]>([]);

  useEffect(() => {
    setPrompt('');
  }, [mode]);

  const defaultsQuery = useQuery<DefaultModelsResponse>({
    queryKey: ['model-defaults'],
    queryFn: () => apiClient.getDefaults(),
  });

  const defaultModels = defaultsQuery.data;
  const chatModelId = defaultModels?.default_chat_model ?? null;

  const contextSummary = useMemo(() => buildContextSummary(context), [context]);

  const askMutation = useMutation<AskResponse, Error, { prompt: string; mode: CopilotMode }>({
    mutationFn: async ({ prompt: promptText, mode: activeMode }) => {
      if (!chatModelId) {
        throw new Error('Configure a default chat model in settings.');
      }

      const baseQuestion =
        activeMode === 'ask'
          ? `You are assisting with research for notebook ${notebookId}. Answer the question using the draft and context when relevant.\n\nQuestion: ${promptText}\n\nCurrent draft markdown:\n${draft}\n\nNotebook context:\n${contextSummary}`
          : `You are an expert editor rewriting the notebook draft based on the instructions below.\n\nINSTRUCTIONS:\n${promptText}\n\nRewrite the draft and return ONLY the revised markdown, without commentary.\n\n---\n${draft}`;

      return apiClient.ask({
        question: baseQuestion,
        strategy_model: chatModelId,
        answer_model: chatModelId,
        final_answer_model: chatModelId,
      });
    },
    onSuccess: (response, variables) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-assistant`,
          role: 'assistant',
          mode: variables.mode,
          content: response.answer,
          createdAt: new Date().toISOString(),
        },
      ]);
      if (variables.mode === 'edit' && onDraftUpdate) {
        onDraftUpdate(response.answer);
      }
      setPrompt('');
    },
    onError: (error, variables) => {
      const message = error instanceof Error ? error.message : 'Copilot request failed.';
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-assistant-error`,
          role: 'assistant',
          mode: variables.mode,
          content: `⚠️ ${message}`,
          createdAt: new Date().toISOString(),
        },
      ]);
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!prompt.trim()) return;

    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-user`,
        role: 'user',
        mode,
        content: prompt.trim(),
        createdAt: new Date().toISOString(),
      },
    ]);

    askMutation.mutate({ prompt: prompt.trim(), mode });
  };

  const handlePromptChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setPrompt(event.target.value);
  };

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <div className="text-sm font-semibold">Copilot</div>
        <p className="text-xs text-muted-foreground">Ask questions or generate edits powered by your configured models.</p>
      </div>
      {!chatModelId && (
        <div className="rounded-md border border-amber-300/60 bg-amber-100/40 p-3 text-xs text-amber-900">
          No default chat model configured. Open the settings panel to select one before using the copilot.
        </div>
      )}
      <Tabs value={mode} onValueChange={(value) => setMode(value as CopilotMode)}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="ask" className="gap-1 text-xs">
            <Sparkles className="h-4 w-4" /> Ask
          </TabsTrigger>
          <TabsTrigger value="edit" className="gap-1 text-xs">
            <Wand2 className="h-4 w-4" /> Edit draft
          </TabsTrigger>
        </TabsList>
        <TabsContent value="ask" className="mt-3">
          <form className="space-y-3" onSubmit={handleSubmit}>
            <Textarea
              placeholder="What do you want to know?"
              value={prompt}
              onChange={handlePromptChange}
              rows={4}
              disabled={askMutation.isPending || !chatModelId}
            />
            <Button type="submit" className="w-full" disabled={askMutation.isPending || !prompt.trim() || !chatModelId}>
              {askMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
              Ask notebook
            </Button>
          </form>
        </TabsContent>
        <TabsContent value="edit" className="mt-3">
          <form className="space-y-3" onSubmit={handleSubmit}>
            <Textarea
              placeholder="Describe the edits to apply to the draft (tone, structure, sections to update, etc.)."
              value={prompt}
              onChange={handlePromptChange}
              rows={6}
              disabled={askMutation.isPending || !chatModelId}
            />
            <Button type="submit" className="w-full" disabled={askMutation.isPending || !prompt.trim() || !chatModelId}>
              {askMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
              Generate edits
            </Button>
          </form>
        </TabsContent>
      </Tabs>
      <div className="flex flex-col gap-2 text-xs text-muted-foreground">
        <div className="font-medium text-foreground">History</div>
        <ScrollArea className="max-h-60 flex-1 rounded-md border border-border/70 p-3">
          <div className="flex flex-col gap-3 pr-2">
            {messages.length === 0 && <p className="text-muted-foreground">No copilot exchanges yet.</p>}
            {messages.map((message) => (
              <div
                key={message.id}
                className={`rounded-md border p-3 text-xs ${message.role === 'user' ? 'border-primary/40 bg-primary/5 text-foreground' : 'border-secondary/50 bg-secondary/20 text-foreground'}`}
              >
                <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
                  <span>{message.role === 'user' ? 'You' : 'Copilot'} · {message.mode}</span>
                  <span>{new Date(message.createdAt).toLocaleTimeString()}</span>
                </div>
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{message.content}</div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
};

export default CopilotPanel;
