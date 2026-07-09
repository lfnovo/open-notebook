import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { getDockerGuidance, type DockerPrimaryAction } from "../lib/dockerGuidance";
import { getInstallInstructions } from "../lib/statusMessages";
import { useI18n } from "../i18n";
import type { DistroInfo, DockerStatus } from "../types";
import {
  Button,
  Card,
  ChecklistItem,
  GuidanceCard,
  ScreenShell,
} from "../components/ui";

interface DockerSetupScreenProps {
  onContinue: () => void;
  onBack: () => void;
}

export function DockerSetupScreen({ onContinue, onBack }: DockerSetupScreenProps) {
  const { t } = useI18n();
  const [status, setStatus] = useState<DockerStatus | null>(null);
  const [distro, setDistro] = useState<DistroInfo | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  async function refresh() {
    const [docker, detected] = await Promise.all([api.checkDocker(), api.detectDistro()]);
    setStatus(docker);
    setDistro(detected);
  }

  useEffect(() => {
    void refresh();
  }, []);

  const guidance = status ? getDockerGuidance(status, t) : null;
  const ready = guidance?.situation === "ready";

  async function runAction(action: () => Promise<string>, successHint?: string) {
    setLoading(true);
    setMessage("");
    try {
      const result = await action();
      setMessage(result || successHint || t("common.actionSuccess"));
      await refresh();
    } catch (error) {
      setMessage(String(error));
    } finally {
      setLoading(false);
    }
  }

  async function handlePrimaryAction(action: DockerPrimaryAction) {
    switch (action) {
      case "continue":
        onContinue();
        return;
      case "install_engine":
        await runAction(() => api.installEngine());
        return;
      case "install_desktop":
        await runAction(() => api.installDesktop());
        return;
      case "start_daemon":
        await runAction(() => api.startDockerDaemon(), t("docker.daemonStarted"));
        return;
      case "refresh":
        setLoading(true);
        setMessage("");
        try {
          await refresh();
          setMessage(t("common.success"));
        } finally {
          setLoading(false);
        }
        return;
    }
  }

  const instructions = distro ? getInstallInstructions(distro.family, t) : "";

  if (!status || !guidance) {
    return (
      <ScreenShell title={t("docker.title")} subtitle={t("docker.subtitle")}>
        <Card>
          <p className="text-slate-300">{t("docker.loadingStatus")}</p>
        </Card>
      </ScreenShell>
    );
  }

  return (
    <ScreenShell
      title={t("docker.title")}
      subtitle={t("docker.subtitle")}
      actions={
        <Button variant="secondary" onClick={onBack}>
          {t("common.back")}
        </Button>
      }
    >
      <div className="space-y-6">
        <GuidanceCard
          ready={ready}
          stepLabel={
            ready
              ? undefined
              : t("docker.stepProgress", {
                  current: String(guidance.stepNumber),
                  total: String(guidance.totalSteps),
                })
          }
          headline={guidance.headline}
          description={guidance.description}
          hint={guidance.secondaryHint}
        >
          <div className="pt-2">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-slate-400">
              {t("docker.recommendedAction")}
            </p>
            <Button
              disabled={loading}
              className={ready ? "px-6 py-3 text-base" : "px-5 py-3"}
              onClick={() => void handlePrimaryAction(guidance.primaryAction)}
            >
              {guidance.primaryLabel}
            </Button>
          </div>
        </GuidanceCard>

        <Card className="space-y-3">
          <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-slate-400">
            {t("docker.checklistTitle")}
          </h3>
          <div className="space-y-2">
            {guidance.checklist.map((item) => (
              <ChecklistItem key={item.id} ok={item.ok} label={item.label} />
            ))}
          </div>
        </Card>

        {message ? (
          <Card className="border-sky-400/20 bg-sky-500/5">
            <pre className="whitespace-pre-wrap text-sm text-slate-300">{message}</pre>
          </Card>
        ) : null}

        {!ready && guidance.showAdvanced ? (
          <Card className="space-y-4">
            <button
              type="button"
              className="text-sm font-medium text-sky-300 hover:text-sky-200"
              onClick={() => setShowAdvanced((value) => !value)}
            >
              {showAdvanced ? t("docker.hideAdvanced") : t("docker.showAdvanced")}
            </button>

            {showAdvanced ? (
              <div className="space-y-4 border-t border-white/10 pt-4">
                <h3 className="text-sm font-semibold text-white">{t("docker.advancedOptions")}</h3>
                <div className="flex flex-wrap gap-3">
                  {guidance.situation === "cli_missing" ? (
                    <Button
                      variant="secondary"
                      disabled={loading}
                      onClick={() => runAction(() => api.installDesktop())}
                    >
                      {t("docker.installDesktop")}
                    </Button>
                  ) : null}
                  {guidance.situation !== "daemon_stopped" ? (
                    <Button
                      variant="secondary"
                      disabled={loading}
                      onClick={() => runAction(() => api.startDockerDaemon(), t("docker.daemonStarted"))}
                    >
                      {t("docker.startDaemon")}
                    </Button>
                  ) : null}
                  <Button variant="secondary" disabled={loading} onClick={() => void refresh()}>
                    {t("docker.refreshStatus")}
                  </Button>
                  <Button variant="secondary" onClick={() => void api.openDockerDocs()}>
                    {t("docker.openDocs")}
                  </Button>
                </div>

                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-slate-300">{t("docker.manualTitle")}</h4>
                  <pre className="overflow-x-auto rounded-xl bg-black/30 p-4 text-sm text-slate-300 whitespace-pre-wrap">
                    {instructions}
                  </pre>
                </div>
              </div>
            ) : null}
          </Card>
        ) : null}

        {ready ? (
          <Card className="border-white/5 bg-black/10">
            <details>
              <summary className="cursor-pointer text-sm text-slate-400 hover:text-slate-300">
                {t("docker.technicalDetails")}
              </summary>
              <div className="mt-3 space-y-1 text-sm text-slate-500">
                {status.version ? (
                  <p>
                    {t("common.version")}: {status.version}
                  </p>
                ) : null}
                {distro ? (
                  <p>{t("docker.detectedSystem", { name: distro.name, family: distro.family })}</p>
                ) : null}
              </div>
            </details>
          </Card>
        ) : null}
      </div>
    </ScreenShell>
  );
}
