import { useI18n } from "../i18n";
import type { InstallContext, UpdateInfo } from "../types";
import { Button, Card } from "./ui";

interface UpdatePanelProps {
  installContext: InstallContext | null;
  updateInfo: UpdateInfo;
  onCheck: () => void;
  onInstall: () => void;
  onOpenRelease: () => void;
}

export function UpdatePanel({
  installContext,
  updateInfo,
  onCheck,
  onInstall,
  onOpenRelease,
}: UpdatePanelProps) {
  const { t } = useI18n();

  const statusLabel = (() => {
    switch (updateInfo.status) {
      case "checking":
        return t("updates.status.checking");
      case "uptodate":
        return t("updates.status.uptodate");
      case "available":
        return t("updates.status.available", { version: updateInfo.latestVersion ?? "" });
      case "managed":
        return t("updates.status.managed", { version: updateInfo.latestVersion ?? "" });
      case "downloading":
        return t("updates.status.downloading", {
          progress: String(updateInfo.progress ?? 0),
        });
      case "ready_restart":
        return t("updates.status.readyRestart");
      case "error":
        return t("updates.status.error");
      case "unsupported":
        return t("updates.status.unsupported");
      default:
        return t("updates.status.idle");
    }
  })();

  const channelLabel =
    installContext?.channel === "appimage"
      ? t("updates.channel.appimage")
      : installContext?.channel === "deb"
        ? t("updates.channel.deb")
        : installContext?.channel === "development"
          ? t("updates.channel.development")
          : t("updates.channel.unknown");

  return (
    <Card className="space-y-4">
      <div>
        <h3 className="text-lg font-medium text-white">{t("updates.title")}</h3>
        <p className="mt-1 text-sm text-slate-400">{t("updates.subtitle")}</p>
      </div>

      <div className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300 space-y-2">
        <p>
          {t("updates.currentVersion")}: <strong>{updateInfo.currentVersion}</strong>
        </p>
        <p>
          {t("updates.installType")}: {channelLabel}
        </p>
        <p>{statusLabel}</p>
        {updateInfo.notes ? <p className="text-slate-400">{updateInfo.notes}</p> : null}
        {updateInfo.error ? <p className="text-rose-300">{updateInfo.error}</p> : null}
      </div>

      <div className="flex flex-wrap gap-3">
        <Button
          variant="secondary"
          disabled={updateInfo.status === "checking" || updateInfo.status === "downloading"}
          onClick={onCheck}
        >
          {t("updates.checkNow")}
        </Button>

        {updateInfo.status === "available" && installContext?.canSelfUpdate ? (
          <Button onClick={onInstall}>{t("updates.installAndRestart")}</Button>
        ) : null}

        {updateInfo.status === "managed" || installContext?.channel === "deb" ? (
          <Button variant="secondary" onClick={onOpenRelease}>
            {t("updates.openReleasePage")}
          </Button>
        ) : null}
      </div>

      {installContext?.channel === "deb" ? (
        <p className="text-xs text-slate-500">{t("updates.debHint")}</p>
      ) : null}
    </Card>
  );
}
