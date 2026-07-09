import { invoke } from "@tauri-apps/api/core";
import type { AppConfig, DistroInfo, DockerStatus, InstallContext, StackStatus } from "../types";

export const api = {
  getConfig: () => invoke<AppConfig>("get_config"),
  saveConfig: (config: AppConfig) => invoke<void>("save_app_config", { config }),
  detectSystemLanguage: () => invoke<string>("detect_system_language"),
  getInstallContext: () => invoke<InstallContext>("get_install_context_cmd"),
  openReleasePage: () => invoke<void>("open_release_page"),
  generateKey: () => invoke<string>("generate_key"),
  checkDocker: () => invoke<DockerStatus>("check_docker"),
  detectDistro: () => invoke<DistroInfo>("detect_linux_distro"),
  getInstallInstructions: () => invoke<string>("get_install_instructions"),
  installEngine: () => invoke<string>("install_engine"),
  installDesktop: () => invoke<string>("install_desktop"),
  verifyDockerInstall: () => invoke<string>("verify_docker_install"),
  startDockerDaemon: () => invoke<string>("start_docker_daemon"),
  openDockerDocs: () => invoke<void>("open_docker_docs"),
  getStackStatus: () => invoke<StackStatus>("get_stack_status"),
  initializeStack: () => invoke<string>("initialize_stack"),
  startStack: () => invoke<string>("start_stack"),
  stopStack: () => invoke<string>("stop_stack"),
  restartStack: () => invoke<string>("restart_stack"),
  fetchLogs: (tail?: number) => invoke<string>("fetch_logs", { tail }),
  waitForAppReady: (timeoutSecs?: number) =>
    invoke<boolean>("wait_for_app_ready", { timeoutSecs }),
  openNotebookWindow: () => invoke<void>("open_notebook_window"),
};
