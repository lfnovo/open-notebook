import ThemeToggle from '@/components/theme/ThemeToggle';
import { SidebarTrigger } from '@/components/ui/sidebar';

interface AppHeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

const AppHeader = ({ title = 'Open Notebook', subtitle, actions }: AppHeaderProps) => {
  return (
    <header className="flex h-14 w-full items-center justify-between border-b bg-card/70 px-4 backdrop-blur">
      <div className="flex flex-1 items-center gap-3">
        <SidebarTrigger />
        {(title || subtitle) && (
          <div className="min-w-0">
            {title && <h1 className="truncate text-lg font-semibold">{title}</h1>}
            {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2">
        {actions}
        <ThemeToggle />
      </div>
    </header>
  );
};

export default AppHeader;
