import type { DockerStatus, StackStatus } from "../types";

type Translate = (key: string, vars?: Record<string, string>) => string;

export function getDockerStatusMessage(status: DockerStatus, t: Translate): string {
  if (!status.available) return t("docker.status.cliMissing");
  if (!status.daemonRunning) return t("docker.status.daemonStopped");
  if (!status.composeAvailable) return t("docker.status.composeMissing");
  if (!status.userInDockerGroup) return t("docker.status.groupMissing");
  return t("docker.status.ready");
}

export function getStackStatusMessage(status: StackStatus, t: Translate): string {
  if (status.running && status.healthy) return t("dashboard.status.running");
  if (status.running) return t("dashboard.status.starting");
  return t("dashboard.status.stopped");
}

export function getInstallInstructions(family: string, t: Translate): string {
  if (family === "debian" || family === "fedora" || family === "arch") {
    return t(`docker.install.${family}`);
  }
  return t("docker.install.unknown");
}
