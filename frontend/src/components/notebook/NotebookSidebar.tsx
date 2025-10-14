import { Home, FileText, NotebookPen, Settings2 } from "lucide-react";

import SourcesPanel from "./sources/SourcesPanel";
import SettingsLauncher from "@/components/settings/SettingsLauncher";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { cn, formatDateTime } from "@/lib/utils";
import type { Notebook } from "@/types/api";

interface NotebookSidebarProps {
  notebookId?: string;
  notebook?: Notebook;
  isNotebookLoading?: boolean;
  onNavigateHome: () => void;
  onOpenReportDialog: () => void;
}

const NotebookSidebar = ({
  notebook,
  notebookId,
  isNotebookLoading,
  onNavigateHome,
  onOpenReportDialog,
}: NotebookSidebarProps) => {
  const { isCollapsed } = useSidebar();

  const notebookName =
    notebook?.name ??
    (isNotebookLoading ? "Loading notebook…" : "Notebook workspace");

  const notebookInitial = (notebook?.name?.[0] ?? "N").toUpperCase();

  return (
    <Sidebar className="bg-card/80">
      <SidebarHeader
        className={cn(
          "flex items-center gap-3",
          isCollapsed ? "justify-center py-5" : "flex-col items-start py-5"
        )}
      >
        <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-border/60 bg-background/80 text-base font-semibold">
          {isCollapsed ? (
            <NotebookPen className="h-5 w-5 text-primary" />
          ) : (
            notebookInitial
          )}
        </span>
        {!isCollapsed && (
          <div className="space-y-1">
            <p className="text-xs uppercase text-muted-foreground tracking-wide">
              Notebook
            </p>
            <h2 className="text-lg font-semibold leading-tight">
              {notebookName}
            </h2>
            {notebook && (
              <p className="text-xs text-muted-foreground">
                Updated {formatDateTime(notebook.updated)}
              </p>
            )}
          </div>
        )}
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  icon={<Home className="h-4 w-4" />}
                  onClick={onNavigateHome}
                  tooltip="Home"
                >
                  Home
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SettingsLauncher
                  trigger={
                    <SidebarMenuButton
                      icon={<Settings2 className="h-4 w-4" />}
                      tooltip="Settings"
                      type="button"
                    >
                      Settings
                    </SidebarMenuButton>
                  }
                />
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  icon={<FileText className="h-4 w-4" />}
                  onClick={onOpenReportDialog}
                  tooltip="Create report"
                  disabled={!notebookId}
                >
                  Create report
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>Sources</SidebarGroupLabel>
          <SidebarGroupContent>
            {!isCollapsed && notebookId ? (
              <div className="rounded-lg border border-border/70 bg-background/80 p-2">
                <SourcesPanel notebookId={notebookId} showHeader={false} />
              </div>
            ) : null}
            {!isCollapsed && !notebookId && (
              <p className="text-xs text-muted-foreground">
                Select a notebook to view sources.
              </p>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
};

export default NotebookSidebar;
