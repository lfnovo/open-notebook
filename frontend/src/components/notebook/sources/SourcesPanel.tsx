import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { formatDateTime } from '@/lib/utils';
import AddSourceDialog from './AddSourceDialog';
import type { SourceListItem } from '@/types/api';

interface SourcesPanelProps {
  notebookId: string;
}

const SourcesPanel = ({ notebookId }: SourcesPanelProps) => {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading, isError } = useQuery<SourceListItem[]>({
    queryKey: ['sources', notebookId],
    queryFn: () => apiClient.getSources(notebookId),
    enabled: Boolean(notebookId),
  });

  const sources = data ?? [];

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold">Sources</div>
          <p className="text-xs text-muted-foreground">Documents linked to this research notebook.</p>
        </div>
        <Button size="sm" variant="ghost" onClick={() => setDialogOpen(true)}>
          <Plus className="mr-1 h-4 w-4" /> Add
        </Button>
      </div>
      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading sources…
        </div>
      )}
      {isError && !isLoading && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
          Failed to load sources. Verify that the API is reachable.
        </div>
      )}
      <ScrollArea className="flex-1  max-w-full">
        <div className="flex flex-col gap-3 pr-2">
          {sources.length === 0 && !isLoading && (
            <div className="rounded-md border border-dashed p-4 text-xs text-muted-foreground">
              No sources yet. Add links or text to ground the notebook.
            </div>
          )}
          {sources.map((source) => (
            <div key={source.id} className="rounded-md border border-border/70 bg-background p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 break-all text-sm font-medium leading-tight">
                  {source.title || 'Untitled source'}
                </div>
                <Badge variant="outline" className="max-w-[45%] truncate">{source.topics.length > 0 ? `${source.topics.length} topics` : 'No tags'}</Badge>
              </div>
              <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                <div>Updated {formatDateTime(source.updated)}</div>
                {source.asset?.url && (
                  <a
                    href={source.asset.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline"
                  >
                    Open link
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
      <AddSourceDialog
        open={dialogOpen}
        notebookId={notebookId}
        onOpenChange={setDialogOpen}
        onCreated={() => {
          queryClient.invalidateQueries({ queryKey: ['sources', notebookId] });
          queryClient.invalidateQueries({ queryKey: ['context', notebookId] });
        }}
      />
    </div>
  );
};

export default SourcesPanel;
