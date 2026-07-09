import type { StackStatus } from "../types";

export type StackPhase = "loading" | "missing" | "stopped" | "starting" | "ready";

export function getStackPhase(status: StackStatus | null): StackPhase {
  if (!status) return "loading";
  if (status.healthy) return "ready";
  if (status.running) return "starting";
  if (status.containers.some((container) => container.state === "missing")) {
    return "missing";
  }
  return "stopped";
}

export function needsInitialize(status: StackStatus): boolean {
  return status.containers.some((container) => container.state === "missing");
}

export function getContainerLabel(
  name: string,
  t: (key: string) => string,
): string {
  if (name.includes("surrealdb")) return t("dashboard.containers.surrealdb");
  if (name.includes("app")) return t("dashboard.containers.app");
  return name;
}
