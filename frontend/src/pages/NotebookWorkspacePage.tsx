import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Save } from 'lucide-react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import AppShell from '@/components/layout/AppShell';
import MilkdownEditor from '@/components/editor/MilkdownEditor';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { formatDateTime } from '@/lib/utils';
import CopilotPanel from '@/features/copilot/components/CopilotPanel';
import SourcesPanel from '@/features/sources/components/SourcesPanel';
import type { ContextResponse, Notebook, Note } from '@/types/api';

const NotebookWorkspacePage = () => {
  const { notebookId } = useParams<{ notebookId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [activeNoteId, setActiveNoteId] = useState<string | null>(() => searchParams.get('note'));
  const [draft, setDraft] = useState('');

  const {
    data: notebook,
    isLoading: isNotebookLoading,
    isError: isNotebookError,
  } = useQuery<Notebook>({
    queryKey: ['notebook', notebookId],
    queryFn: () => apiClient.getNotebook(notebookId ?? ''),
    enabled: Boolean(notebookId),
  });

  const {
    data: notes,
    isLoading: isNotesLoading,
  } = useQuery<Note[]>({
    queryKey: ['notes', notebookId],
    queryFn: () => apiClient.getNotes(notebookId ?? ''),
    enabled: Boolean(notebookId),
  });

  const { data: contextData } = useQuery<ContextResponse>({
    queryKey: ['context', notebookId],
    queryFn: () => apiClient.getContext({ notebook_id: notebookId ?? '' }),
    enabled: Boolean(notebookId),
    staleTime: 1000 * 60 * 5,
  });

  const activeNote: Note | undefined = useMemo(() => {
    if (!notes || notes.length === 0) return undefined;
    const note = notes.find((item) => item.id === activeNoteId);
    return note ?? notes[0];
  }, [notes, activeNoteId]);

  const isDirty = useMemo(() => {
    if (!activeNote) return false;
    return draft !== (activeNote.content ?? '');
  }, [activeNote, draft]);

  useEffect(() => {
    if (!notes || notes.length === 0) {
      setActiveNoteId(null);
      setDraft('');
      return;
    }

    const note = notes.find((item) => item.id === activeNoteId) ?? notes[0];
    if (note && note.id !== activeNoteId) {
      setActiveNoteId(note.id);
      setSearchParams((prev) => {
        const params = new URLSearchParams(prev);
        params.set('note', note.id);
        return params;
      });
    }
    setDraft(note?.content ?? '');
  }, [notes, activeNoteId, setSearchParams]);

  const updateNoteMutation = useMutation<Note, Error, { noteId: string; content: string }>({
    mutationFn: ({ noteId, content }) => apiClient.updateNote(noteId, { content }),
    onSuccess: (result, variables) => {
      queryClient.setQueryData<Note[] | undefined>(['notes', notebookId], (prev) => {
        if (!prev) return prev;
        return prev.map((item) => (item.id === variables.noteId ? result : item));
      });
      setDraft(result.content ?? '');
      setSearchParams((prev) => {
        const params = new URLSearchParams(prev);
        params.set('note', variables.noteId);
        return params;
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', notebookId] });
    },
  });

  const handleSave = () => {
    if (!activeNote || !isDirty) return;
    updateNoteMutation.mutate({ noteId: activeNote.id, content: draft });
  };

  useEffect(() => {
    if (!notebookId || (!isNotebookError && notebook)) return;
    if (isNotebookError) {
      navigate('/', { replace: true });
    }
  }, [isNotebookError, navigate, notebook, notebookId]);

  return (
    <AppShell
      title={notebook?.name ?? 'Notebook'}
      subtitle={notebook ? `Updated ${formatDateTime(notebook.updated)}` : undefined}
      headerActions={
        <Button onClick={handleSave} disabled={!activeNote || !isDirty || updateNoteMutation.isPending}>
          {updateNoteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          <Save className="mr-2 h-4 w-4" /> Save draft
        </Button>
      }
    >
      <div className="flex h-[calc(100vh-72px)] flex-col divide-y">
        {(isNotebookLoading || isNotesLoading) && (
          <div className="flex h-12 items-center gap-2 px-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading notebook workspace…
          </div>
        )}
        <div className="flex min-h-0 flex-1 gap-4 px-6 py-4">
          <aside className="flex w-72 flex-col border border-border/80 bg-card/50 p-4">
            {notebookId && <SourcesPanel notebookId={notebookId} />}
          </aside>
          <section className="flex min-w-0 flex-1 flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Draft</h2>
                {activeNote && (
                  <p className="text-sm text-muted-foreground">
                    Last updated {formatDateTime(activeNote.updated)}
                  </p>
                )}
              </div>
            </div>
            <div className="flex min-h-0 flex-1 overflow-hidden rounded-lg border border-border bg-card">
              <MilkdownEditor value={draft} onChange={setDraft} className="h-full w-full" />
            </div>
          </section>
          <aside className="flex w-80 flex-col border border-border/80 bg-card/50 p-4">
            {notebookId && (
              <CopilotPanel
                notebookId={notebookId}
                draft={draft}
                onDraftUpdate={setDraft}
                context={contextData}
              />
            )}
          </aside>
        </div>
      </div>
    </AppShell>
  );
};

export default NotebookWorkspacePage;
