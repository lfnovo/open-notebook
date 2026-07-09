import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { getContainerLabel, getStackPhase, needsInitialize, type StackPhase } from "../lib/stackPhase";
import { truncateError } from "../lib/validation";
import { useI18n } from "../i18n";
import type { StackStatus } from "../types";
import { Button, Card, GuidanceCard, ScreenShell, StatusBadge } from "../components/ui";

type BusyKind = "initialize" | "start" | "restart" | "stop" | "open";

interface DashboardScreenProps {
  onOpenLogs: () => void;
  onOpenSettings: () => void;
  launchError?: string;
}

function Spinner() {
  return (
    <div
      className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-sky-300/30 border-t-sky-300"
      aria-hidden
    />
  );
}

export function DashboardScreen({
  onOpenLogs,
  onOpenSettings,
  launchError,
}: DashboardScreenProps) {
  const { t } = useI18n();
  const [status, setStatus] = useState<StackStatus | null>(null);
  const [error, setError] = useState(launchError ?? "");
  const [busy, setBusy] = useState<BusyKind | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [info, setInfo] = useState("");

  useEffect(() => {
    if (launchError) {
      setError(launchError);
    }
  }, [launchError]);

  const phase = getStackPhase(status);

  const refresh = useCallback(async () => {
    try {
      const stack = await api.getStackStatus();
      setStatus(stack);
      setError("");
    } catch (err) {
      setError(truncateError(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const intervalMs = busy ? 2000 : 5000;
    const timer = window.setInterval(() => void refresh(), intervalMs);
    return () => window.clearInterval(timer);
  }, [refresh, busy]);

  const runAction = useCallback(
    async (kind: BusyKind, action: () => Promise<string>, progressKey: string) => {
      setBusy(kind);
      setError("");
      setInfo(t(progressKey));
      try {
        const result = await action();
        setInfo(result || t("common.success"));
        await refresh();
        return true;
      } catch (err) {
        setError(truncateError(err));
        setInfo("");
        return false;
      } finally {
        setBusy(null);
      }
    },
    [refresh, t],
  );

  const startStack = useCallback(async () => {
    if (!status) return false;
    if (needsInitialize(status)) {
      return runAction("initialize", () => api.initializeStack(), "dashboard.progress.initialize");
    }
    return runAction("start", () => api.startStack(), "dashboard.progress.start");
  }, [runAction, status]);

  const openApp = useCallback(async () => {
    setBusy("open");
    setError("");
    setInfo(t("dashboard.waitForApp"));
    try {
      const ready = await api.waitForAppReady(60);
      if (!ready) {
        throw new Error(t("dashboard.appNotResponding"));
      }
      await api.openNotebookWindow();
      setInfo(t("dashboard.appOpened"));
      return true;
    } catch (err) {
      setError(String(err));
      return false;
    } finally {
      setBusy(null);
    }
  }, [t]);

  function getGuidance(phase: StackPhase) {
    switch (phase) {
      case "ready":
        return {
          ready: true,
          headline: t("dashboard.guidance.readyTitle"),
          description: t("dashboard.guidance.readyDescription"),
          hint: t("dashboard.readyHint"),
        };
      case "starting":
        return {
          headline: t("dashboard.guidance.startingTitle"),
          description: t("dashboard.guidance.startingDescription"),
          hint: t("dashboard.startingHint"),
        };
      case "missing":
        return {
          headline: t("dashboard.guidance.missingTitle"),
          description: t("dashboard.guidance.missingDescription"),
          hint: t("dashboard.missingHint"),
        };
      case "stopped":
        return {
          headline: t("dashboard.guidance.stoppedTitle"),
          description: t("dashboard.guidance.stoppedDescription"),
          hint: t("dashboard.stoppedHint"),
        };
      default:
        return {
          headline: t("dashboard.guidance.loadingTitle"),
          description: t("dashboard.guidance.loadingDescription"),
        };
    }
  }

  const guidance = getGuidance(phase);
  const isBusy = busy !== null;

  function getPrimaryLabel() {
    if (phase === "ready") return t("dashboard.primaryOpen");
    if (error) return t("dashboard.primaryRetry");
    return t("dashboard.primaryStart");
  }

  async function handlePrimaryAction() {
    if (phase === "ready") {
      await openApp();
      return;
    }
    await startStack();
  }

  function getBusyMessage() {
    switch (busy) {
      case "initialize":
        return { title: t("dashboard.progress.initialize"), hint: t("dashboard.pullHint") };
      case "start":
        return { title: t("dashboard.progress.start"), hint: t("dashboard.startingHint") };
      case "restart":
        return { title: t("dashboard.progress.restart"), hint: t("dashboard.startingHint") };
      case "stop":
        return { title: t("dashboard.progress.stop"), hint: undefined };
      case "open":
        return { title: t("dashboard.waitForApp"), hint: undefined };
      default:
        return null;
    }
  }

  const busyMessage = getBusyMessage();

  return (
    <ScreenShell
      title={t("dashboard.title")}
      subtitle={t("dashboard.managementSubtitle")}
      actions={
        <div className="flex gap-2">
          <Button variant="secondary" onClick={onOpenLogs}>
            {t("dashboard.logs")}
          </Button>
          <Button variant="secondary" onClick={onOpenSettings}>
            {t("dashboard.settings")}
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        <Card className="border-white/10 bg-black/20 p-4 text-sm text-slate-400">
          {t("dashboard.menuHint")}
        </Card>

        <GuidanceCard {...guidance}>
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge
              ok={!!status?.running}
              label={status?.running ? t("dashboard.stackRunning") : t("dashboard.stackStopped")}
            />
            <StatusBadge
              ok={!!status?.healthy}
              label={status?.healthy ? t("dashboard.uiOnline") : t("dashboard.uiOffline")}
            />
          </div>
          <Button
            className="mt-2 px-6 py-3 text-base"
            disabled={isBusy || phase === "loading"}
            onClick={() => void handlePrimaryAction()}
          >
            {getPrimaryLabel()}
          </Button>
        </GuidanceCard>

        {isBusy && busyMessage ? (
          <Card className="flex items-start gap-4 border-sky-400/20 bg-sky-500/5">
            <Spinner />
            <div>
              <p className="font-medium text-sky-100">{busyMessage.title}</p>
              {busyMessage.hint ? (
                <p className="mt-1 text-sm text-slate-400">{busyMessage.hint}</p>
              ) : null}
            </div>
          </Card>
        ) : null}

        {status ? (
          <Card className="space-y-4">
            <h3 className="text-sm font-medium uppercase tracking-[0.15em] text-slate-400">
              {t("dashboard.servicesTitle")}
            </h3>
            <div className="grid gap-3 md:grid-cols-2">
              {status.containers.map((container) => (
                <div
                  key={container.name}
                  className="rounded-xl border border-white/10 bg-black/20 p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-white">
                      {getContainerLabel(container.name, t)}
                    </p>
                    <StatusBadge
                      ok={container.running}
                      label={
                        container.running
                          ? t("dashboard.serviceRunning")
                          : container.state === "missing"
                            ? t("dashboard.serviceMissing")
                            : t("dashboard.serviceStopped")
                      }
                    />
                  </div>
                  {container.state !== "missing" ? (
                    <p className="mt-2 text-xs text-slate-500">{container.status}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </Card>
        ) : (
          <Card className="flex items-center gap-3 text-slate-300">
            <Spinner />
            {t("dashboard.loadingStatus")}
          </Card>
        )}

        <Card className="space-y-3">
          <button
            type="button"
            className="flex w-full items-center justify-between text-left text-sm font-medium text-slate-300 hover:text-white"
            onClick={() => setShowAdvanced((open) => !open)}
          >
            <span>{t("dashboard.advancedTitle")}</span>
            <span className="text-slate-500">
              {showAdvanced ? t("dashboard.advancedHide") : t("dashboard.advancedShow")}
            </span>
          </button>

          {showAdvanced ? (
            <div className="flex flex-wrap gap-3 border-t border-white/10 pt-4">
              <Button
                variant="secondary"
                disabled={isBusy}
                onClick={() =>
                  void runAction("restart", () => api.restartStack(), "dashboard.progress.restart")
                }
              >
                {t("dashboard.restart")}
              </Button>
              <Button
                variant="danger"
                disabled={isBusy || !status?.running}
                onClick={() =>
                  void runAction("stop", () => api.stopStack(), "dashboard.progress.stop")
                }
              >
                {t("dashboard.stop")}
              </Button>
              <Button
                variant="secondary"
                disabled={isBusy}
                onClick={() =>
                  void runAction(
                    "initialize",
                    () => api.initializeStack(),
                    "dashboard.progress.initialize",
                  )
                }
              >
                {t("dashboard.reinitialize")}
              </Button>
            </div>
          ) : null}
        </Card>

        {error ? (
          <Card className="border-rose-400/20 bg-rose-500/10">
            <p className="text-sm text-rose-200">{error}</p>
          </Card>
        ) : null}

        {info && !error ? (
          <Card className="border-emerald-400/20 bg-emerald-500/5">
            <p className="text-sm text-emerald-200">{info}</p>
          </Card>
        ) : null}
      </div>
    </ScreenShell>
  );
}
