import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Loader2 } from 'lucide-react';

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { apiClient } from '@/lib/api-client';
import type {
  DefaultModelsResponse,
  SettingsResponse,
  SourceCreatePayload,
  SourceCreateType,
  Transformation,
} from '@/types/api';

interface AddSourceDialogProps {
  notebookId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void;
}

type SourceTab = Extract<SourceCreateType, 'link' | 'upload' | 'text'>;

type FormState = {
  type: SourceTab;
  linkUrl: string;
  file: File | null;
  textTitle: string;
  textContent: string;
  embed: boolean;
  deleteAfter: boolean;
  selectedTransformations: string[];
};

const initialFormState: FormState = {
  type: 'link',
  linkUrl: '',
  file: null,
  textTitle: '',
  textContent: '',
  embed: false,
  deleteAfter: false,
  selectedTransformations: [],
};

const AddSourceDialog = ({ notebookId, open, onOpenChange, onCreated }: AddSourceDialogProps) => {
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [error, setError] = useState<string | null>(null);

  const transformationsQuery = useQuery<Transformation[]>({
    queryKey: ['transformations'],
    queryFn: () => apiClient.getTransformations(),
  });

  const settingsQuery = useQuery<SettingsResponse>({
    queryKey: ['settings'],
    queryFn: () => apiClient.getSettings(),
  });

  const defaultsQuery = useQuery<DefaultModelsResponse>({
    queryKey: ['model-defaults'],
    queryFn: () => apiClient.getDefaults(),
  });

  const createSourceMutation = useMutation({
    mutationFn: (payload: SourceCreatePayload) => apiClient.createSource(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', notebookId] });
      queryClient.invalidateQueries({ queryKey: ['context', notebookId] });
      onCreated?.();
      handleClose(false);
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploadSourceFile(file),
  });

  const transformations = useMemo(() => transformationsQuery.data ?? [], [transformationsQuery.data]);

  useEffect(() => {
    if (!transformations.length || !open) return;
    const defaults = transformations
      .filter((transformation) => transformation.apply_default)
      .map((item) => item.id);
    setFormState((prev) => ({
      ...prev,
      selectedTransformations: defaults,
    }));
  }, [transformations, open]);

  useEffect(() => {
    const embeddingOption = settingsQuery.data?.default_embedding_option;
    setFormState((prev) => ({
      ...prev,
      embed: embeddingOption === 'always' ? true : embeddingOption === 'ask' ? prev.embed : false,
      deleteAfter: settingsQuery.data?.auto_delete_files === 'yes',
    }));
  }, [settingsQuery.data?.default_embedding_option, settingsQuery.data?.auto_delete_files]);

  const handleClose = (value: boolean) => {
    onOpenChange(value);
    if (!value) {
      setFormState(initialFormState);
      setError(null);
    }
  };

  const handleAddTransformation = (id: string, checked: boolean | string) => {
    setFormState((prev) => {
      const current = new Set(prev.selectedTransformations);
      if (checked) {
        current.add(id);
      } else {
        current.delete(id);
      }
      return { ...prev, selectedTransformations: Array.from(current) };
    });
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (formState.type === 'link' && !formState.linkUrl.trim()) {
      setError('Provide a valid URL for the source.');
      return;
    }

    if (formState.type === 'text' && !formState.textContent.trim()) {
      setError('Provide content for the text source.');
      return;
    }

    if (formState.type === 'upload' && !formState.file) {
      setError('Select a file to upload.');
      return;
    }

    try {
      let filePath: string | undefined;

      if (formState.type === 'upload' && formState.file) {
        const uploadResult = await uploadMutation.mutateAsync(formState.file);
        filePath = uploadResult.file_path;
      }

      const payload: SourceCreatePayload = {
        notebook_id: notebookId,
        type: formState.type,
        transformations: formState.selectedTransformations,
        embed: formState.embed,
      };

      if (formState.type === 'link') {
        payload.url = formState.linkUrl.trim();
      } else if (formState.type === 'text') {
        payload.title = formState.textTitle.trim() || undefined;
        payload.content = formState.textContent.trim();
      } else if (formState.type === 'upload') {
        payload.file_path = filePath;
        payload.delete_source = formState.deleteAfter;
      }

      await createSourceMutation.mutateAsync(payload);
    } catch (err) {
      console.error(err);
      setError('Failed to process the source. Check server logs for details.');
    }
  };

  const embeddingOption = settingsQuery.data?.default_embedding_option ?? 'never';
  const requiresSpeechToText = defaultsQuery.data?.default_speech_to_text_model;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add a source</DialogTitle>
          <DialogDescription>
            Attach research material to the notebook either by pasting a link, uploading a file, or providing raw text.
          </DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <Tabs value={formState.type} onValueChange={(value) => setFormState((prev) => ({ ...prev, type: value as SourceTab }))}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="link">Link</TabsTrigger>
              <TabsTrigger value="upload">File upload</TabsTrigger>
              <TabsTrigger value="text">Text</TabsTrigger>
            </TabsList>
            <TabsContent value="link" className="mt-4 space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-link-url">
                  URL
                </label>
                <Input
                  id="source-link-url"
                  placeholder="https://example.com/article"
                  value={formState.linkUrl}
                  onChange={(event) => setFormState((prev) => ({ ...prev, linkUrl: event.target.value }))}
                  disabled={createSourceMutation.isPending || uploadMutation.isPending}
                  required
                />
              </div>
              <p className="text-xs text-muted-foreground">
                The backend agent will fetch and process the linked content, applying any selected transformations.
              </p>
            </TabsContent>
            <TabsContent value="upload" className="mt-4 space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-file">
                  File
                </label>
                <Input
                  id="source-file"
                  type="file"
                  onChange={(event) =>
                    setFormState((prev) => ({ ...prev, file: event.target.files?.[0] ?? null }))
                  }
                  disabled={createSourceMutation.isPending || uploadMutation.isPending}
                  required
                />
              </div>
              {!requiresSpeechToText && (
                <div className="flex items-start gap-2 rounded-md border border-amber-400/60 bg-amber-50 p-3 text-xs text-amber-900">
                  <AlertCircle className="mt-0.5 h-4 w-4" />
                  <span>
                    No speech-to-text model is configured. Audio and video uploads will not be transcribed automatically.
                  </span>
                </div>
              )}
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <Checkbox
                  checked={formState.deleteAfter}
                  onCheckedChange={(checked) =>
                    setFormState((prev) => ({ ...prev, deleteAfter: Boolean(checked) }))
                  }
                  disabled
                />
                Auto-delete after processing ({settingsQuery.data?.auto_delete_files ?? 'no'})
              </label>
            </TabsContent>
            <TabsContent value="text" className="mt-4 space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-text-title">
                  Title (optional)
                </label>
                <Input
                  id="source-text-title"
                  placeholder="Source title"
                  value={formState.textTitle}
                  onChange={(event) => setFormState((prev) => ({ ...prev, textTitle: event.target.value }))}
                  disabled={createSourceMutation.isPending}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="source-text-content">
                  Raw content
                </label>
                <Textarea
                  id="source-text-content"
                  placeholder="Paste or type the source content here."
                  value={formState.textContent}
                  onChange={(event) => setFormState((prev) => ({ ...prev, textContent: event.target.value }))}
                  disabled={createSourceMutation.isPending}
                  rows={8}
                  required
                />
              </div>
            </TabsContent>
          </Tabs>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Transformations</span>
              {transformationsQuery.isLoading && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
            </div>
            <ScrollArea className="h-48 w-full rounded-md border border-border/70">
              <div className="flex flex-col gap-2 p-3 pr-4">
                {transformations.length === 0 && (
                  <p className="text-xs text-muted-foreground">No transformations configured.</p>
                )}
                {transformations.map((transformation) => (
                  <label key={transformation.id} className="flex items-start gap-3 text-sm">
                    <Checkbox
                      checked={formState.selectedTransformations.includes(transformation.id)}
                      onCheckedChange={(checked) => handleAddTransformation(transformation.id, Boolean(checked))}
                    />
                    <span>
                      <span className="font-medium">{transformation.title}</span>
                      <br />
                      <span className="text-xs text-muted-foreground">{transformation.description}</span>
                    </span>
                  </label>
                ))}
              </div>
            </ScrollArea>
          </div>

          {embeddingOption === 'ask' && (
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={formState.embed}
                onCheckedChange={(checked) => setFormState((prev) => ({ ...prev, embed: Boolean(checked) }))}
              />
              Embed content for vector search
            </label>
          )}
          {embeddingOption === 'always' && (
            <p className="text-xs text-muted-foreground">Embedding enabled automatically based on workspace settings.</p>
          )}
          {embeddingOption !== 'always' && embeddingOption !== 'ask' && (
            <p className="text-xs text-muted-foreground">Embedding disabled by default. You can embed later from the source details.</p>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex items-center justify-end gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => handleClose(false)}
              disabled={createSourceMutation.isPending || uploadMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createSourceMutation.isPending || uploadMutation.isPending}>
              {(createSourceMutation.isPending || uploadMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Add source
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default AddSourceDialog;
