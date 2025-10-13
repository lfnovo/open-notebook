import { useState } from 'react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import type { Notebook } from '@/types/api';

interface CreateNotebookDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete: (payload: { notebook: Notebook }) => void;
}

const extractErrorMessage = (err: unknown): string | null => {
  const maybeError = err as { response?: { data?: unknown }; message?: string };
  const data = maybeError?.response?.data;

  if (typeof data === 'string') return data;
  if (data && typeof data === 'object') {
    const record = data as Record<string, unknown>;
    if (typeof record.message === 'string') return record.message;
    if (typeof record.error === 'string') return record.error;
  }
  if (maybeError?.message) return maybeError.message;
  return null;
};

const CreateNotebookDialog = ({ open, onOpenChange, onComplete }: CreateNotebookDialogProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setName('');
    setDescription('');
    setIsSubmitting(false);
    setError(null);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!name.trim()) {
      setError('Notebook name is required.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const notebook = await apiClient.createNotebook({
        name: name.trim(),
        description: description.trim(),
      });

      onOpenChange(false);
      reset();
      onComplete({ notebook });
    } catch (err) {
      console.error('createNotebook failed:', err);
      setError(extractErrorMessage(err) ?? 'Notebook creation failed unexpectedly.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value);
        if (!value) reset();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a new notebook</DialogTitle>
          <DialogDescription>
            Provide a notebook name and optional context. You can add sources and generate reports after creation.
          </DialogDescription>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="notebook-name">
              Notebook name
            </label>
            <Input
              id="notebook-name"
              placeholder="Exploring climate change impacts…"
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={isSubmitting}
              required
              aria-invalid={Boolean(error) && !name.trim()}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="notebook-description">
              Description (optional)
            </label>
            <Textarea
              id="notebook-description"
              placeholder="Add broader context or project goals…"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              disabled={isSubmitting}
              rows={3}
            />
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <div className="flex items-center justify-end gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                reset();
                onOpenChange(false);
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creating…' : 'Create notebook'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default CreateNotebookDialog;
