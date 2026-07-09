import type { DockerStatus } from "../types";

export type DockerSituation =
  | "ready"
  | "cli_missing"
  | "daemon_stopped"
  | "compose_missing"
  | "group_missing";

export type DockerPrimaryAction =
  | "continue"
  | "install_engine"
  | "install_desktop"
  | "start_daemon"
  | "refresh";

export interface DockerCheckItem {
  id: string;
  ok: boolean;
  label: string;
}

export interface DockerGuidance {
  situation: DockerSituation;
  stepNumber: number;
  totalSteps: number;
  headline: string;
  description: string;
  primaryAction: DockerPrimaryAction;
  primaryLabel: string;
  secondaryHint?: string;
  showAdvanced: boolean;
  checklist: DockerCheckItem[];
}

type Translate = (key: string, vars?: Record<string, string>) => string;

function buildChecklist(status: DockerStatus, t: Translate): DockerCheckItem[] {
  return [
    {
      id: "cli",
      ok: status.available,
      label: status.available ? t("docker.checklist.cliOk") : t("docker.checklist.cliMissing"),
    },
    {
      id: "daemon",
      ok: status.daemonRunning,
      label: status.daemonRunning
        ? t("docker.checklist.daemonOk")
        : t("docker.checklist.daemonMissing"),
    },
    {
      id: "compose",
      ok: status.composeAvailable,
      label: status.composeAvailable
        ? t("docker.checklist.composeOk")
        : t("docker.checklist.composeMissing"),
    },
    {
      id: "group",
      ok: status.userInDockerGroup,
      label: status.userInDockerGroup
        ? t("docker.checklist.groupOk")
        : t("docker.checklist.groupMissing"),
    },
  ];
}

function completedChecks(checklist: DockerCheckItem[]): number {
  return checklist.filter((item) => item.ok).length;
}

export function getDockerGuidance(status: DockerStatus, t: Translate): DockerGuidance {
  const checklist = buildChecklist(status, t);
  const done = completedChecks(checklist);

  if (
    status.available &&
    status.daemonRunning &&
    status.composeAvailable &&
    status.userInDockerGroup
  ) {
    return {
      situation: "ready",
      stepNumber: 4,
      totalSteps: 4,
      headline: t("docker.guidance.ready.headline"),
      description: t("docker.guidance.ready.description"),
      primaryAction: "continue",
      primaryLabel: t("docker.guidance.ready.action"),
      showAdvanced: false,
      checklist,
    };
  }

  if (!status.available) {
    return {
      situation: "cli_missing",
      stepNumber: Math.max(done, 0) + 1,
      totalSteps: 4,
      headline: t("docker.guidance.cliMissing.headline"),
      description: t("docker.guidance.cliMissing.description"),
      primaryAction: "install_engine",
      primaryLabel: t("docker.guidance.cliMissing.action"),
      secondaryHint: t("docker.guidance.cliMissing.hint"),
      showAdvanced: true,
      checklist,
    };
  }

  if (!status.daemonRunning) {
    return {
      situation: "daemon_stopped",
      stepNumber: Math.max(done, 1) + 1,
      totalSteps: 4,
      headline: t("docker.guidance.daemonStopped.headline"),
      description: t("docker.guidance.daemonStopped.description"),
      primaryAction: "start_daemon",
      primaryLabel: t("docker.guidance.daemonStopped.action"),
      secondaryHint: t("docker.guidance.daemonStopped.hint"),
      showAdvanced: true,
      checklist,
    };
  }

  if (!status.composeAvailable) {
    return {
      situation: "compose_missing",
      stepNumber: Math.max(done, 2) + 1,
      totalSteps: 4,
      headline: t("docker.guidance.composeMissing.headline"),
      description: t("docker.guidance.composeMissing.description"),
      primaryAction: "install_engine",
      primaryLabel: t("docker.guidance.composeMissing.action"),
      secondaryHint: t("docker.guidance.composeMissing.hint"),
      showAdvanced: true,
      checklist,
    };
  }

  return {
    situation: "group_missing",
    stepNumber: 4,
    totalSteps: 4,
    headline: t("docker.guidance.groupMissing.headline"),
    description: t("docker.guidance.groupMissing.description"),
    primaryAction: "refresh",
    primaryLabel: t("docker.guidance.groupMissing.action"),
    secondaryHint: t("docker.guidance.groupMissing.hint"),
    showAdvanced: true,
    checklist,
  };
}
