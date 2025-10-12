import SettingsLauncher from '@/components/settings/SettingsLauncher';

interface AppHeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

const AppHeader = ({ title = 'Open Notebook', subtitle, actions }: AppHeaderProps) => {
  return (
    <header className="flex w-full items-center justify-between border-b bg-card/60 px-6 py-4 backdrop-blur">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        {actions}
        <SettingsLauncher />
      </div>
    </header>
  );
};

export default AppHeader;
