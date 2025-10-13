import AppHeader from './AppHeader';

interface AppShellProps {
  title?: string;
  subtitle?: string;
  headerActions?: React.ReactNode;
  children: React.ReactNode;
}

const AppShell = ({ title, subtitle, headerActions, children }: AppShellProps) => {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <AppHeader title={title} subtitle={subtitle} actions={headerActions} />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
};

export default AppShell;
