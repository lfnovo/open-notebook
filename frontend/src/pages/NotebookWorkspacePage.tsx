import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ChevronLeft, ChevronRight, FileText, Loader2, Save } from 'lucide-react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import AppShell from '@/components/layout/AppShell';
import MilkdownEditor from '@/components/editor/MilkdownEditor';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { cn, formatDateTime } from '@/lib/utils';
import CopilotPanel from '@/components/copilot/CopilotPanel';
import SourcesPanel from '@/components/notebook/sources/SourcesPanel';
import GenerateReportDialog from '@/features/notebooks/components/GenerateReportDialog';
import type { ContextResponse, Notebook, Note, ResearchResponse } from '@/types/api';

const NotebookWorkspacePage = () => {
  const { notebookId } = useParams<{ notebookId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [activeNoteId, setActiveNoteId] = useState<string | null>(() => searchParams.get('note'));
  const [draft, setDraft] = useState('');
  const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
  const [isReportDialogOpen, setIsReportDialogOpen] = useState(false);

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

  const handleReportCreated = ({ note }: { note: Note; research: ResearchResponse }) => {
    if (!notebookId) return;
    queryClient.setQueryData<Note[] | undefined>(['notes', notebookId], (prev) => {
      if (!prev) return [note];
      const existingIndex = prev.findIndex((item) => item.id === note.id);
      if (existingIndex === -1) {
        return [note, ...prev];
      }
      const next = [...prev];
      next[existingIndex] = note;
      return next;
    });
    setActiveNoteId(note.id);
    setDraft(note.content ?? '');
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set('note', note.id);
      return params;
    });
    queryClient.invalidateQueries({ queryKey: ['notes', notebookId] });
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
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate('/')}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to notebooks
          </Button>
          <Button type="button" onClick={() => setIsReportDialogOpen(true)} disabled={!notebookId}>
            <FileText className="mr-2 h-4 w-4" /> Create report from sources
          </Button>
          <Button onClick={handleSave} disabled={!activeNote || !isDirty || updateNoteMutation.isPending}>
            {updateNoteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <Save className="mr-2 h-4 w-4" /> Save draft
          </Button>
        </div>
      }
    >
      <div className="flex h-[calc(100vh-72px)] flex-col divide-y">
        {(isNotebookLoading || isNotesLoading) && (
          <div className="flex h-12 items-center gap-2 px-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading notebook workspace…
          </div>
        )}
        <div className="flex min-h-0 flex-1 gap-4 px-6 py-4">
          <div className="flex items-start gap-2">
            <aside
              id="sources-panel"
              className={cn(
                'flex h-full flex-col overflow-hidden border border-border/80 bg-card/50 transition-all duration-200 ease-in-out',
                isSourcesCollapsed
                  ? 'w-0 border-transparent bg-transparent p-0 opacity-0 pointer-events-none'
                  : 'w-72 p-4 opacity-100',
              )}
            >
              {!isSourcesCollapsed && notebookId && <SourcesPanel notebookId={notebookId} />}
            </aside>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setIsSourcesCollapsed((prev) => !prev)}
              aria-expanded={!isSourcesCollapsed}
              aria-controls="sources-panel"
              aria-label={isSourcesCollapsed ? 'Expand sources panel' : 'Collapse sources panel'}
              className="h-8 w-8 shrink-0 border border-border/70 bg-background/80 text-muted-foreground hover:bg-accent"
            >
              {isSourcesCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </Button>
          </div>
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
              <MilkdownEditor value={draft} onChange={setDraft} className="h-full" />
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
      {notebookId && (
        <GenerateReportDialog
          open={isReportDialogOpen}
          notebookId={notebookId}
          onOpenChange={setIsReportDialogOpen}
          onReportCreated={handleReportCreated}
        />
      )}
    </AppShell>
  );
};

export default NotebookWorkspacePage;
