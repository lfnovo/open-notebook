import { useState } from 'react';

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import type { Notebook, Note, ResearchResponse } from '@/types/api';

interface CreateNotebookDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete: (payload: {
    notebook: Notebook;
    note: Note;
    research: ResearchResponse;
  }) => void;
}

const CreateNotebookDialog = ({ open, onOpenChange, onComplete }: CreateNotebookDialogProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [question, setQuestion] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setName('');
    setDescription('');
    setQuestion('');
    setError(null);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !question.trim()) {
      setError('Notebook name and research prompt are required.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const notebook = await apiClient.createNotebook({
        name: name.trim(),
        description: description.trim(),
      });

      const research = await apiClient.runResearch({
        question: question.trim(),
        notebook_id: notebook.id,
      });

      const note = await apiClient.createNote({
        notebook_id: notebook.id,
        content: research.final_report,
        note_type: 'ai',
        title: 'Research Draft',
      });

      onOpenChange(false);
      reset();
      onComplete({ notebook, note, research });
    } catch (err: unknown) {
      console.error(err);
      setError('Failed to create notebook or fetch research. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(value) => { onOpenChange(value); if (!value) reset(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a new Notebook</DialogTitle>
          <DialogDescription>
            Provide a descriptive name, optional context, and the research objective to generate the first draft automatically.
          </DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="notebook-name">
              Notebook name
            </label>
            <Input
              id="notebook-name"
              placeholder="Exploring climate change impacts..."
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={isSubmitting}
              required
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="notebook-description">
              Description (optional)
            </label>
            <Textarea
              id="notebook-description"
              placeholder="Add broader context or project goals..."
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              disabled={isSubmitting}
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="notebook-question">
              Research prompt
            </label>
            <Textarea
              id="notebook-question"
              placeholder="What should the deep research agent investigate?"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              disabled={isSubmitting}
              rows={4}
              required
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
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
              {isSubmitting ? 'Generating draft…' : 'Create & Research'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default CreateNotebookDialog;
