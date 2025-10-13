import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Loader2, PlusCircle, Trash2 } from "lucide-react";

import AppShell from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";
import { formatDateTime } from "@/lib/utils";
import type { Notebook } from "@/types/api";
import CreateNotebookDialog from "@/components/menu/CreateNotebookDialog";

const NotebookListPage = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deletingNotebookId, setDeletingNotebookId] = useState<string | null>(
    null
  );
  const [notebookToDelete, setNotebookToDelete] = useState<Notebook | null>(
    null
  );
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const deleteNotebookMutation = useMutation({
    mutationFn: (notebookId: string) => apiClient.deleteNotebook(notebookId),
    onMutate: (notebookId: string) => {
      setDeletingNotebookId(notebookId);
      setDeleteError(null);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      setNotebookToDelete(null);
    },
    onError: (error) => {
      console.error("Failed to delete notebook", error);
      setDeleteError("Failed to delete the notebook. Please try again.");
    },
    onSettled: () => {
      setDeletingNotebookId(null);
    },
  });

  const { data, isLoading, isError } = useQuery<Notebook[]>({
    queryKey: ["notebooks"],
    queryFn: () => apiClient.getNotebooks(),
  });

  const notebooks = [...(data ?? [])].sort((a, b) =>
    a.updated < b.updated ? 1 : -1
  );

  const handleNotebookCreated = (notebook: Notebook) => {
    queryClient.invalidateQueries({ queryKey: ["notebooks"] });
    navigate(`/notebooks/${notebook.id}`);
  };

  return (
    <AppShell
      title="Open Notebook"
      subtitle="Research notebooks backed by AI copilot"
      headerActions={
        <Button onClick={() => setDialogOpen(true)}>
          <PlusCircle className="mr-2 h-4 w-4" /> New Notebook
        </Button>
      }
    >
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-10">
        {isLoading && (
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading notebooks…</span>
          </div>
        )}
        {isError && !isLoading && (
          <div className="rounded-md border border-destructive/60 bg-destructive/10 p-4 text-sm text-destructive">
            Failed to load notebooks. Ensure the API is running.
          </div>
        )}
        {!isLoading && notebooks.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-12 text-center">
            <h2 className="text-xl font-semibold">No notebooks yet</h2>
            <p className="max-w-md text-sm text-muted-foreground">
              Create your first notebook to kick off a deep research workflow.
              Add sources and generate reports from the workspace when you’re
              ready.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              <PlusCircle className="mr-2 h-4 w-4" /> Create notebook
            </Button>
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          {notebooks.map((notebook) => (
            <Card
              key={notebook.id}
              className="relative flex h-full flex-col justify-between border-muted"
            >
              <button
                type="button"
                aria-label="Delete notebook"
                className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-black/40 text-white transition hover:bg-black/60 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={(event) => {
                  event.stopPropagation();
                  setNotebookToDelete(notebook);
                }}
                disabled={
                  deleteNotebookMutation.isPending &&
                  deletingNotebookId === notebook.id
                }
              >
                {deleteNotebookMutation.isPending &&
                deletingNotebookId === notebook.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </button>
              <CardHeader>
                <CardTitle className="text-lg">{notebook.name}</CardTitle>
                {notebook.description && (
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {notebook.description}
                  </p>
                )}
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                <div>Updated: {formatDateTime(notebook.updated)}</div>
                <div>Created: {formatDateTime(notebook.created)}</div>
              </CardContent>
              <CardFooter>
                <Button
                  variant="ghost"
                  className="ml-auto"
                  onClick={() => navigate(`/notebooks/${notebook.id}`)}
                >
                  Open <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
      <Dialog
        open={Boolean(notebookToDelete)}
        onOpenChange={(open) => {
          if (!open) {
            if (deleteNotebookMutation.isPending) {
              return;
            }
            setNotebookToDelete(null);
            setDeleteError(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete notebook</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{notebookToDelete?.name}
              &quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteError && (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {deleteError}
            </p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                if (deleteNotebookMutation.isPending) {
                  return;
                }
                setNotebookToDelete(null);
                setDeleteError(null);
              }}
              disabled={deleteNotebookMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (!notebookToDelete) {
                  return;
                }
                deleteNotebookMutation.mutate(notebookToDelete.id);
              }}
              disabled={!notebookToDelete || deleteNotebookMutation.isPending}
            >
              {deleteNotebookMutation.isPending &&
              deletingNotebookId === notebookToDelete?.id ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting…
                </>
              ) : (
                "Delete"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <CreateNotebookDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onComplete={({ notebook }) => handleNotebookCreated(notebook)}
      />
    </AppShell>
  );
};

export default NotebookListPage;
