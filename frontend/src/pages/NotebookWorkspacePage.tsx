import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Save } from "lucide-react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import AppShell from "@/components/layout/AppShell";
import MilkdownEditor from "@/components/editor/MilkdownEditor";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { formatDateTime } from "@/lib/utils";
import GenerateReportDialog from "@/components/notebook/GenerateReportDialog";
import CopilotLauncher from "@/components/copilot/CopilotLauncher";
import NotebookSidebar from "@/components/notebook/NotebookSidebar";
import type {
  ContextResponse,
  Notebook,
  Note,
  ResearchResponse,
} from "@/types/api";

const NotebookWorkspacePage = () => {
  const { notebookId } = useParams<{ notebookId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [activeNoteId, setActiveNoteId] = useState<string | null>(() =>
    searchParams.get("note")
  );
  const [draft, setDraft] = useState("");
  const [isReportDialogOpen, setIsReportDialogOpen] = useState(false);

  const {
    data: notebook,
    isLoading: isNotebookLoading,
    isError: isNotebookError,
  } = useQuery<Notebook>({
    queryKey: ["notebook", notebookId],
    queryFn: () => apiClient.getNotebook(notebookId ?? ""),
    enabled: Boolean(notebookId),
  });

  const { data: notes, isLoading: isNotesLoading } = useQuery<Note[]>({
    queryKey: ["notes", notebookId],
    queryFn: () => apiClient.getNotes(notebookId ?? ""),
    enabled: Boolean(notebookId),
  });

  const { data: contextData } = useQuery<ContextResponse>({
    queryKey: ["context", notebookId],
    queryFn: () => apiClient.getContext({ notebook_id: notebookId ?? "" }),
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
    return draft !== (activeNote.content ?? "");
  }, [activeNote, draft]);

  useEffect(() => {
    if (!notes || notes.length === 0) {
      setActiveNoteId(null);
      setDraft("");
      return;
    }

    const note = notes.find((item) => item.id === activeNoteId) ?? notes[0];
    if (note && note.id !== activeNoteId) {
      setActiveNoteId(note.id);
      setSearchParams((prev) => {
        const params = new URLSearchParams(prev);
        params.set("note", note.id);
        return params;
      });
    }
    setDraft(note?.content ?? "");
  }, [notes, activeNoteId, setSearchParams]);

  const updateNoteMutation = useMutation<
    Note,
    Error,
    { noteId: string; content: string }
  >({
    mutationFn: ({ noteId, content }) =>
      apiClient.updateNote(noteId, { content }),
    onSuccess: (result, variables) => {
      queryClient.setQueryData<Note[] | undefined>(
        ["notes", notebookId],
        (prev) => {
          if (!prev) return prev;
          return prev.map((item) =>
            item.id === variables.noteId ? result : item
          );
        }
      );
      setDraft(result.content ?? "");
      setSearchParams((prev) => {
        const params = new URLSearchParams(prev);
        params.set("note", variables.noteId);
        return params;
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["notes", notebookId] });
    },
  });

  const handleSave = () => {
    if (!activeNote || !isDirty) return;
    updateNoteMutation.mutate({ noteId: activeNote.id, content: draft });
  };

  const handleReportCreated = ({
    note,
  }: {
    note: Note;
    research: ResearchResponse;
  }) => {
    if (!notebookId) return;
    queryClient.setQueryData<Note[] | undefined>(
      ["notes", notebookId],
      (prev) => {
        if (!prev) return [note];
        const existingIndex = prev.findIndex((item) => item.id === note.id);
        if (existingIndex === -1) {
          return [note, ...prev];
        }
        const next = [...prev];
        next[existingIndex] = note;
        return next;
      }
    );
    setActiveNoteId(note.id);
    setDraft(note.content ?? "");
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("note", note.id);
      return params;
    });
    queryClient.invalidateQueries({ queryKey: ["notes", notebookId] });
  };

  useEffect(() => {
    if (!notebookId || (!isNotebookError && notebook)) return;
    if (isNotebookError) {
      navigate("/", { replace: true });
    }
  }, [isNotebookError, navigate, notebook, notebookId]);

  return (
    <AppShell
      title="Open Notebook"
      sidebar={
        <NotebookSidebar
          notebook={notebook}
          notebookId={notebookId}
          isNotebookLoading={isNotebookLoading}
          onNavigateHome={() => navigate("/")}
          onOpenReportDialog={() => setIsReportDialogOpen(true)}
        />
      }
      headerActions={
        <div className="flex items-center gap-2">
          <CopilotLauncher
            notebookId={notebookId ?? undefined}
            draft={draft}
            onDraftUpdate={setDraft}
            context={contextData}
            disabled={!notebookId}
          />
          <Button
            onClick={handleSave}
            disabled={!activeNote || !isDirty || updateNoteMutation.isPending}
          >
            {updateNoteMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            <Save className="mr-2 h-4 w-4" /> Save draft
          </Button>
        </div>
      }
    >
      <div className="flex h-full flex-col">
        {(isNotebookLoading || isNotesLoading) && (
          <div className="flex h-10 items-center gap-2 border-b border-border/60 bg-card/50 px-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading notebook
            workspace…
          </div>
        )}
        <section className="flex min-h-0 flex-1 flex-col gap-4 px-6 py-4">
          {activeNote && (
            <p className="text-sm text-muted-foreground">
              Last updated {formatDateTime(activeNote.updated)}
            </p>
          )}
          <div className="flex min-h-0 flex-1 overflow-hidden rounded-lg border border-border bg-card">
            <MilkdownEditor
              value={draft}
              onChange={setDraft}
              className="h-full"
            />
          </div>
        </section>
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
