import * as React from "react";
import { PanelLeftOpen, PanelRightOpen } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type SidebarContextValue = {
  isCollapsed: boolean;
  toggleCollapsed: () => void;
  setCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
};

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

interface SidebarProviderProps {
  defaultCollapsed?: boolean;
  children: React.ReactNode;
}

const SidebarProvider = ({
  defaultCollapsed = false,
  children,
}: SidebarProviderProps) => {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

  const toggleCollapsed = React.useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  const value = React.useMemo(
    () => ({
      isCollapsed,
      toggleCollapsed,
      setCollapsed: setIsCollapsed,
    }),
    [isCollapsed, toggleCollapsed]
  );

  return (
    <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>
  );
};

const useSidebar = () => {
  const context = React.useContext(SidebarContext);
  if (!context) {
    return {
      isCollapsed: false,
      toggleCollapsed: () => {
        if (process.env.NODE_ENV !== "production") {
          console.warn("useSidebar must be used within a <SidebarProvider>.");
        }
      },
      setCollapsed: () => {
        if (process.env.NODE_ENV !== "production") {
          console.warn("useSidebar must be used within a <SidebarProvider>.");
        }
      },
    };
  }
  return context;
};

const Sidebar = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  const { isCollapsed } = useSidebar();

  return (
    <aside
      ref={ref}
      className={cn(
        "group/sidebar relative flex min-h-screen flex-col border-r bg-card/80 pb-4 text-sm backdrop-blur transition-[width] duration-200 ease-in-out",
        isCollapsed ? "w-16" : "w-72",
        className
      )}
      {...props}
    />
  );
});
Sidebar.displayName = "Sidebar";

const SidebarHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("border-b px-4 py-4", className)}
    {...props}
  />
));
SidebarHeader.displayName = "SidebarHeader";

const SidebarContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex-1 space-y-6 overflow-y-auto px-3 py-4 scrollbar-thin",
      className
    )}
    {...props}
  />
));
SidebarContent.displayName = "SidebarContent";

const SidebarGroup = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("space-y-2", className)} {...props} />
));
SidebarGroup.displayName = "SidebarGroup";

const SidebarGroupLabel = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  const { isCollapsed } = useSidebar();
  return (
    <div
      ref={ref}
      className={cn(
        "px-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground",
        isCollapsed && "sr-only",
        className
      )}
      {...props}
    />
  );
});
SidebarGroupLabel.displayName = "SidebarGroupLabel";

const SidebarGroupContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("space-y-2", className)} {...props} />
));
SidebarGroupContent.displayName = "SidebarGroupContent";

const SidebarMenu = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <nav
    ref={ref}
    className={cn("flex flex-col gap-2 text-sm", className)}
    {...props}
  />
));
SidebarMenu.displayName = "SidebarMenu";

const SidebarMenuItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("flex", className)} {...props} />
));
SidebarMenuItem.displayName = "SidebarMenuItem";

interface SidebarMenuButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  tooltip?: string;
  isActive?: boolean;
}

const SidebarMenuButton = React.forwardRef<
  HTMLButtonElement,
  SidebarMenuButtonProps
>(({ className, icon, tooltip, isActive, children, ...props }, ref) => {
  const { isCollapsed } = useSidebar();

  const button = (
    <button
      ref={ref}
      className={cn(
        "inline-flex h-10 w-full items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        isCollapsed ? "justify-center px-0" : "justify-start",
        isActive
          ? "bg-accent text-accent-foreground shadow-sm"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        className
      )}
      {...props}
    >
      {icon && (
        <span className="flex h-8 w-8 items-center justify-center rounded-md border border-border/60 bg-background/70 text-base">
          {icon}
        </span>
      )}
      {!isCollapsed && (
        <span className="truncate text-sm font-medium">{children}</span>
      )}
    </button>
  );

  if (isCollapsed && tooltip) {
    return (
      <TooltipProvider delayDuration={150}>
        <Tooltip>
          <TooltipTrigger asChild>{button}</TooltipTrigger>
          <TooltipContent side="right">{tooltip}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return button;
});
SidebarMenuButton.displayName = "SidebarMenuButton";

const SidebarFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("mt-auto border-t px-3 py-3", className)} {...props} />
));
SidebarFooter.displayName = "SidebarFooter";

interface SidebarTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

const SidebarTrigger = React.forwardRef<HTMLButtonElement, SidebarTriggerProps>(
  ({ className, onClick, ...props }, ref) => {
    const context = React.useContext(SidebarContext);
    if (!context) {
      return null;
    }

    const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      onClick?.(event);
      if (!event.defaultPrevented) {
        context.toggleCollapsed();
      }
    };

    return (
      <button
        ref={ref}
        type="button"
        className={cn(
          "inline-flex h-9 w-9 items-center justify-center rounded-md border border-border/60 bg-background/70 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          className
        )}
        onClick={handleClick}
        {...props}
      >
        {context.isCollapsed ? (
          <PanelRightOpen className="h-4 w-4" />
        ) : (
          <PanelLeftOpen className="h-4 w-4" />
        )}
        <span className="sr-only">Toggle sidebar</span>
      </button>
    );
  }
);
SidebarTrigger.displayName = "SidebarTrigger";

export {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
};
