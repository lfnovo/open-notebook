import { useI18n } from "../i18n";
import { Button } from "./ui";

interface UpdateBannerProps {
  latestVersion?: string;
  notes?: string;
  managed?: boolean;
  onInstall?: () => void;
  onOpenRelease?: () => void;
  onDismiss: () => void;
}

export function UpdateBanner({
  latestVersion,
  notes,
  managed = false,
  onInstall,
  onOpenRelease,
  onDismiss,
}: UpdateBannerProps) {
  const { t } = useI18n();

  return (
    <div className="border-b border-sky-400/20 bg-sky-500/10 px-6 py-4">
      <div className="mx-auto flex max-w-4xl flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-medium text-sky-100">
            {managed
              ? t("updates.bannerManaged", { version: latestVersion ?? "" })
              : t("updates.bannerAvailable", { version: latestVersion ?? "" })}
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {managed ? t("updates.bannerManagedHint") : t("updates.bannerAvailableHint")}
          </p>
          {notes ? <p className="mt-2 text-xs text-slate-400">{notes}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          {managed ? (
            <Button onClick={onOpenRelease}>{t("updates.openReleasePage")}</Button>
          ) : (
            <Button onClick={onInstall}>{t("updates.installAndRestart")}</Button>
          )}
          <Button variant="secondary" onClick={onDismiss}>
            {t("updates.dismiss")}
          </Button>
        </div>
      </div>
    </div>
  );
}
