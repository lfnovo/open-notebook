export interface AppConfig {
  dataDir: string;
  encryptionKey: string;
  stopOnExit: boolean;
  onboardingComplete: boolean;
  uiPort: number;
  apiPort: number;
  language: string;
  autoStartOnLaunch: boolean;
  openNotebookDirectly: boolean;
}

export interface DockerStatus {
  available: boolean;
  daemonRunning: boolean;
  version: string | null;
  composeAvailable: boolean;
  userInDockerGroup: boolean;
  message: string;
}

export interface ContainerInfo {
  name: string;
  state: string;
  status: string;
  running: boolean;
}

export interface StackStatus {
  running: boolean;
  healthy: boolean;
  containers: ContainerInfo[];
  message: string;
}

export interface DistroInfo {
  id: string;
  name: string;
  versionId: string | null;
  family: string;
}

export interface InstallContext {
  channel: string;
  currentVersion: string;
  canSelfUpdate: boolean;
  releasePageUrl: string;
  isDevelopment: boolean;
}

export type UpdateStatus =
  | "idle"
  | "checking"
  | "uptodate"
  | "available"
  | "managed"
  | "downloading"
  | "ready_restart"
  | "error"
  | "unsupported";

export interface UpdateInfo {
  status: UpdateStatus;
  currentVersion: string;
  latestVersion?: string;
  notes?: string;
  progress?: number;
  error?: string;
  dismissed?: boolean;
}

export type Screen =
  | "welcome"
  | "docker"
  | "encryption"
  | "splash"
  | "dashboard"
  | "logs"
  | "settings";

export type LaunchPhase =
  | "checkingDocker"
  | "checkingStack"
  | "pullingImages"
  | "startingStack"
  | "containersStarting"
  | "waitingUi"
  | "opening"
  | "ready";

export interface LaunchProgress {
  percent: number;
  phase: LaunchPhase | string;
}
