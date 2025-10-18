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

  // Load the selected note's content into the editor, but don't overwrite local edits.
  useEffect(() => {
    if (!notes || notes.length === 0) {
      setActiveNoteId(null);
      setDraft("");
      return;
    }

    const chosen = notes.find((item) => item.id === activeNoteId) ?? notes[0];

    // Ensure URL param reflects the chosen note
    if (chosen && chosen.id !== activeNoteId) {
      setActiveNoteId(chosen.id);
      setSearchParams((prev) => {
        const params = new URLSearchParams(prev);
        params.set("note", chosen.id);
        return params;
      });
    }

    // Only sync server content into the editor when we don't have local changes.
    if (!isDirty) {
      setDraft(chosen?.content ?? "");
    }
  }, [notes, activeNoteId, setSearchParams, isDirty]);

  const updateNoteMutation = useMutation<
    Note,
    Error,
    { noteId: string; content: string }
  >({
    mutationFn: ({ noteId, content }) =>
      apiClient.updateNote(noteId, { content }),
    onSuccess: (result, variables) => {
      // Optimistically update cache for a smoother UX
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
      // Keep cache fresh
      queryClient.invalidateQueries({ queryKey: ["notes", notebookId] });
    },
  });

  const handleSave = () => {
    if (!activeNote || !isDirty) return;
    updateNoteMutation.mutate({ noteId: activeNote.id, content: draft });
  };

  // ⬇️ NEW: take the ODR research and write it straight to the Milkdown editor
  const handleReportCreated = ({
    research,
  }: {
    research: ResearchResponse;
  }) => {
    if (!research) return;

    const md = `

---

## Research Report

${research.final_report ?? ""}

`;

    // Append into the current editor draft (Milkdown is controlled by `draft`)
    setDraft((prev) => (prev ?? "") + md);

    // Close the dialog if it's still open
    setIsReportDialogOpen(false);
  };

  // Redirect home if notebook fetch fails
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
            type="button"
            variant="ghost"
            size="icon"
            onClick={handleSave}
            disabled={!activeNote || !isDirty || updateNoteMutation.isPending}
            className="rounded-full bg-background/70 text-muted-foreground hover:bg-accent/60 hover:text-primary"
          >
            {updateNoteMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            <span className="sr-only">Save draft</span>
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
