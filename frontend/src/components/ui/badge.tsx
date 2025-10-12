import * as React from 'react';

import { cn } from '@/lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline';
}

const Badge = ({ className, variant = 'default', ...props }: BadgeProps) => (
  <div
    className={cn(
      'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
      variant === 'default' && 'border-transparent bg-secondary text-secondary-foreground',
      variant === 'outline' && 'border-border text-foreground',
      className,
    )}
    {...props}
  />
);

export { Badge };
