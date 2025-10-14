import AppHeader from './AppHeader';
import { SidebarProvider } from '@/components/ui/sidebar';

interface AppShellProps {
  title?: string;
  subtitle?: string;
  headerActions?: React.ReactNode;
  sidebar?: React.ReactNode;
  children: React.ReactNode;
}

const AppShell = ({
  title,
  subtitle,
  headerActions,
  sidebar,
  children,
}: AppShellProps) => {
  if (sidebar) {
    return (
      <SidebarProvider>
        <div className="flex min-h-screen bg-background text-foreground">
          {sidebar}
          <div className="flex min-h-screen flex-1 flex-col">
            <AppHeader title={title} subtitle={subtitle} actions={headerActions} />
            <main className="flex-1 overflow-hidden">{children}</main>
          </div>
        </div>
      </SidebarProvider>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <AppHeader title={title} subtitle={subtitle} actions={headerActions} />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
};

export default AppShell;
