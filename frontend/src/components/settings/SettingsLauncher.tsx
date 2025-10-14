import { ReactNode, useState } from 'react';
import { Settings2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import SettingsPanel from './SettingsPanel';

interface SettingsLauncherProps {
  trigger?: ReactNode;
}

const SettingsLauncher = ({ trigger }: SettingsLauncherProps) => {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button variant="outline" size="icon">
            <Settings2 className="h-4 w-4" />
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="flex h-[90vh] max-w-5xl flex-col overflow-hidden p-0">
        <DialogHeader className="border-b px-6 py-4 text-left">
          <DialogTitle>Workspace settings</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-hidden px-6 pb-6 pt-4">
          <SettingsPanel onClose={() => setOpen(false)} />
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default SettingsLauncher;
