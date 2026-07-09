import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { api } from "./lib/api";
import { I18nProvider, useI18n } from "./i18n";
import { normalizeLanguage, type Language } from "./i18n/languages";
import type { AppConfig, Screen } from "./types";
import { WelcomeScreen } from "./screens/WelcomeScreen";
import { DockerSetupScreen } from "./screens/DockerSetupScreen";
import { EncryptionScreen } from "./screens/EncryptionScreen";
import { DashboardScreen } from "./screens/DashboardScreen";
import { LogsScreen } from "./screens/LogsScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { StartScreen } from "./screens/StartScreen";
import { ConfigErrorScreen } from "./screens/ConfigErrorScreen";
import { AppUpdateProvider, useAppUpdateContext } from "./contexts/AppUpdateContext";
import { UpdateBanner } from "./components/UpdateBanner";

function getInitialScreen(config: AppConfig, configLoadError: string | null): Screen {
  if (configLoadError) return "config-error";
  if (config.onboardingComplete && config.openNotebookDirectly && config.autoStartOnLaunch) {
    return "splash";
  }
  if (config.onboardingComplete) return "dashboard";
  return "welcome";
}

function isScreen(value: string): value is Screen {
  return [
    "welcome",
    "docker",
    "encryption",
    "splash",
    "dashboard",
    "logs",
    "settings",
    "config-error",
  ].includes(value);
}

interface AppRoutesProps {
  onLanguageChange: (language: Language) => void;
}

function AppShell({ onLanguageChange }: AppRoutesProps) {
  const {
    updateInfo,
    showBanner,
    installAndRestart,
    dismiss,
    openReleasePage,
  } = useAppUpdateContext();

  return (
    <div className="min-h-screen">
      {showBanner ? (
        <UpdateBanner
          latestVersion={updateInfo.latestVersion}
          notes={updateInfo.notes}
          managed={updateInfo.status === "managed"}
          onInstall={() => void installAndRestart()}
          onOpenRelease={() => void openReleasePage()}
          onDismiss={dismiss}
        />
      ) : null}
      <AppRoutes onLanguageChange={onLanguageChange} />
    </div>
  );
}

function AppRoutes({ onLanguageChange }: AppRoutesProps) {
  const { t } = useI18n();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configLoadError, setConfigLoadError] = useState<string | null>(null);
  const [screen, setScreen] = useState<Screen>("welcome");
  const [loading, setLoading] = useState(true);
  const [launchError, setLaunchError] = useState("");

  useEffect(() => {
    void (async () => {
      const loaded = await api.getConfig();
      const loadError = await api.getConfigLoadError();
      const normalized = {
        ...loaded,
        language: normalizeLanguage(loaded.language || (await api.detectSystemLanguage())),
        autoStartOnLaunch: loaded.autoStartOnLaunch ?? true,
        openNotebookDirectly: loaded.openNotebookDirectly ?? true,
      };
      setConfig(normalized);
      setConfigLoadError(loadError);
      onLanguageChange(normalizeLanguage(normalized.language));
      setScreen(getInitialScreen(normalized, loadError));
      setLoading(false);
    })();
  }, [onLanguageChange]);

  useEffect(() => {
    const unlistenNavigate = listen<string>("navigate-screen", (event) => {
      if (isScreen(event.payload)) {
        setScreen(event.payload);
      }
    });

    const unlistenError = listen<string>("launch-error", (event) => {
      setLaunchError(event.payload);
      setScreen("dashboard");
    });

    const unlistenComplete = listen("launch-complete", () => {
      setLaunchError("");
    });

    const unlistenConfigError = listen<string>("config-load-error", (event) => {
      setConfigLoadError(event.payload);
      setScreen("config-error");
    });

    return () => {
      void unlistenNavigate.then((unlisten) => unlisten());
      void unlistenError.then((unlisten) => unlisten());
      void unlistenComplete.then((unlisten) => unlisten());
      void unlistenConfigError.then((unlisten) => unlisten());
    };
  }, []);

  async function saveConfig(
    next: AppConfig,
    options?: { encryptionKey?: string; navigateAfterSave?: Screen },
  ) {
    const normalized = {
      ...next,
      language: normalizeLanguage(next.language),
      autoStartOnLaunch: next.autoStartOnLaunch ?? true,
      openNotebookDirectly: next.openNotebookDirectly ?? true,
    };
    await api.saveConfig(normalized, { encryptionKey: options?.encryptionKey });
    const refreshed = await api.getConfig();
    setConfig({
      ...refreshed,
      language: normalizeLanguage(refreshed.language),
      autoStartOnLaunch: refreshed.autoStartOnLaunch ?? true,
      openNotebookDirectly: refreshed.openNotebookDirectly ?? true,
    });
    onLanguageChange(normalizeLanguage(normalized.language));

    if (options?.navigateAfterSave) {
      setScreen(options.navigateAfterSave);
    }
  }

  async function updateLanguage(language: Language) {
    if (!config) return;
    await saveConfig({ ...config, language }, { navigateAfterSave: screen });
  }

  if (loading || !config) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-300">
        {t("common.loading")}
      </div>
    );
  }

  switch (screen) {
    case "config-error":
      return <ConfigErrorScreen message={configLoadError ?? t("configError.fallback")} />;
    case "welcome":
      return (
        <WelcomeScreen
          language={normalizeLanguage(config.language)}
          onLanguageChange={updateLanguage}
          onContinue={() => setScreen("docker")}
        />
      );
    case "docker":
      return (
        <DockerSetupScreen
          onBack={() => setScreen("welcome")}
          onContinue={() => setScreen("encryption")}
        />
      );
    case "encryption":
      return (
        <EncryptionScreen
          config={config}
          onSave={(next, encryptionKey) =>
            saveConfig(next, { encryptionKey, navigateAfterSave: "splash" })
          }
          onBack={() => setScreen("docker")}
        />
      );
    case "splash":
      return <StartScreen />;
    case "logs":
      return <LogsScreen onBack={() => setScreen("dashboard")} />;
    case "settings":
      return (
        <SettingsScreen
          config={config}
          onSave={(next) => saveConfig(next, { navigateAfterSave: "settings" })}
          onBack={() => setScreen("dashboard")}
        />
      );
    case "dashboard":
    default:
      return (
        <DashboardScreen
          launchError={launchError}
          onOpenLogs={() => setScreen("logs")}
          onOpenSettings={() => setScreen("settings")}
        />
      );
  }
}

function App() {
  const [language, setLanguage] = useState<Language>("en");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    void (async () => {
      const loaded = await api.getConfig();
      setLanguage(normalizeLanguage(loaded.language || (await api.detectSystemLanguage())));
      setReady(true);
    })();
  }, []);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-300">
        Loading...
      </div>
    );
  }

  return (
    <I18nProvider language={language}>
      <AppUpdateProvider>
        <AppShell onLanguageChange={setLanguage} />
      </AppUpdateProvider>
    </I18nProvider>
  );
}

export default App;
