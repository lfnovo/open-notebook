import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2, PlusCircle } from 'lucide-react';

import AppShell from '@/components/layout/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';
import { formatDateTime } from '@/lib/utils';
import type { Notebook, Note } from '@/types/api';
import CreateNotebookDialog from '@/components/menu/CreateNotebookDialog';

const NotebookListPage = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading, isError } = useQuery<Notebook[]>({
    queryKey: ['notebooks'],
    queryFn: () => apiClient.getNotebooks(),
  });

  const notebooks = [...(data ?? [])].sort((a, b) => (a.updated < b.updated ? 1 : -1));

  const handleNotebookCreated = ({ notebook, note }: { notebook: Notebook; note: Pick<Note, 'id'> }) => {
    queryClient.invalidateQueries({ queryKey: ['notebooks'] });
    navigate(`/notebooks/${notebook.id}?note=${note.id}`);
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
              Create your first notebook to kick off a deep research workflow and generate an initial draft automatically.
            </p>
            <Button onClick={() => setDialogOpen(true)}>
              <PlusCircle className="mr-2 h-4 w-4" /> Create notebook
            </Button>
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          {notebooks.map((notebook) => (
            <Card key={notebook.id} className="flex h-full flex-col justify-between border-muted">
              <CardHeader>
                <CardTitle className="text-lg">{notebook.name}</CardTitle>
                {notebook.description && (
                  <p className="text-sm text-muted-foreground line-clamp-3">{notebook.description}</p>
                )}
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                <div>Updated: {formatDateTime(notebook.updated)}</div>
                <div>Created: {formatDateTime(notebook.created)}</div>
              </CardContent>
              <CardFooter>
                <Button variant="ghost" className="ml-auto" onClick={() => navigate(`/notebooks/${notebook.id}`)}>
                  Open <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
      <CreateNotebookDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onComplete={({ notebook, note }) => handleNotebookCreated({ notebook, note })}
      />
    </AppShell>
  );
};

export default NotebookListPage;
