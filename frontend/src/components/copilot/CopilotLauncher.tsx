import { useState } from "react";
import { Sparkles } from "lucide-react";

import CopilotPanel from "./CopilotPanel";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { ContextResponse } from "@/types/api";

interface CopilotLauncherProps {
  notebookId?: string;
  draft: string;
  onDraftUpdate?: (markdown: string) => void;
  context?: ContextResponse;
  disabled?: boolean;
}

const CopilotLauncher = ({
  notebookId,
  draft,
  onDraftUpdate,
  context,
  disabled,
}: CopilotLauncherProps) => {
  const [open, setOpen] = useState(false);
  const isDisabled = disabled || !notebookId;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={isDisabled}
          className="rounded-full border border-border/60 bg-background/80 text-muted-foreground hover:text-primary"
        >
          <Sparkles className="h-4 w-4" />
          <span className="sr-only">Toggle copilot</span>
        </Button>
      </SheetTrigger>
      <SheetContent className="flex w-full max-w-md flex-col bg-card/95 p-0">
        <SheetHeader className="border-b px-6 py-4 text-left">
          <SheetTitle className="flex items-center gap-2 text-lg font-semibold">
            <Sparkles className="h-4 w-4 text-primary" />
            Copilot
          </SheetTitle>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {notebookId && (
            <CopilotPanel
              notebookId={notebookId}
              draft={draft}
              onDraftUpdate={onDraftUpdate}
              context={context}
            />
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default CopilotLauncher;
