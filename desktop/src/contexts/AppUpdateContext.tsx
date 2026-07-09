import { createContext, useContext, type ReactNode } from "react";
import { useAppUpdate } from "../hooks/useAppUpdate";

type AppUpdateValue = ReturnType<typeof useAppUpdate>;

const AppUpdateContext = createContext<AppUpdateValue | null>(null);

export function AppUpdateProvider({ children }: { children: ReactNode }) {
  const value = useAppUpdate();
  return <AppUpdateContext.Provider value={value}>{children}</AppUpdateContext.Provider>;
}

export function useAppUpdateContext() {
  const context = useContext(AppUpdateContext);
  if (!context) {
    throw new Error("useAppUpdateContext must be used within AppUpdateProvider");
  }
  return context;
}
