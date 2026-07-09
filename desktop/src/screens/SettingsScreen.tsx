import { useState } from "react";
import { LanguageSelect } from "../components/LanguageSelect";
import { UpdatePanel } from "../components/UpdatePanel";
import { useAppUpdateContext } from "../contexts/AppUpdateContext";
import { useI18n } from "../i18n";
import { normalizeLanguage } from "../i18n/languages";
import type { AppConfig } from "../types";
import { Button, Card, ScreenShell } from "../components/ui";

interface SettingsScreenProps {
  config: AppConfig;
  onSave: (config: AppConfig) => Promise<void>;
  onBack: () => void;
}

export function SettingsScreen({ config, onSave, onBack }: SettingsScreenProps) {
  const { t } = useI18n();
  const {
    installContext,
    updateInfo,
    checkNow,
    installAndRestart,
    openReleasePage,
  } = useAppUpdateContext();
  const [draft, setDraft] = useState(config);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    setLoading(true);
    setMessage("");
    try {
      await onSave({
        ...draft,
        language: normalizeLanguage(draft.language),
      });
      setMessage(t("settings.saved"));
    } catch (error) {
      setMessage(String(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScreenShell
      title={t("settings.title")}
      subtitle={t("settings.subtitle")}
      actions={
        <Button variant="secondary" onClick={onBack}>
          {t("common.back")}
        </Button>
      }
    >
      <div className="space-y-6">
        <UpdatePanel
          installContext={installContext}
          updateInfo={updateInfo}
          onCheck={() => void checkNow()}
          onInstall={() => void installAndRestart()}
          onOpenRelease={() => void openReleasePage()}
        />

        <Card className="space-y-5">
        <LanguageSelect
          label={t("common.language")}
          value={normalizeLanguage(draft.language)}
          onChange={(language) => setDraft({ ...draft, language })}
        />

        <label className="block space-y-2">
          <span className="text-sm text-slate-300">{t("settings.dataDir")}</span>
          <input
            className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-sky-400"
            value={draft.dataDir}
            onChange={(e) => setDraft({ ...draft, dataDir: e.target.value })}
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-2">
            <span className="text-sm text-slate-300">{t("settings.uiPort")}</span>
            <input
              type="number"
              className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-sky-400"
              value={draft.uiPort}
              onChange={(e) => setDraft({ ...draft, uiPort: Number(e.target.value) })}
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm text-slate-300">{t("settings.apiPort")}</span>
            <input
              type="number"
              className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-sky-400"
              value={draft.apiPort}
              onChange={(e) => setDraft({ ...draft, apiPort: Number(e.target.value) })}
            />
          </label>
        </div>

        <label className="flex items-center gap-3 text-slate-300">
          <input
            type="checkbox"
            checked={draft.autoStartOnLaunch}
            onChange={(e) => setDraft({ ...draft, autoStartOnLaunch: e.target.checked })}
            className="h-4 w-4 rounded border-white/20 bg-black/30"
          />
          {t("settings.autoStartOnLaunch")}
        </label>

        <label className="flex items-center gap-3 text-slate-300">
          <input
            type="checkbox"
            checked={draft.openNotebookDirectly}
            onChange={(e) => setDraft({ ...draft, openNotebookDirectly: e.target.checked })}
            className="h-4 w-4 rounded border-white/20 bg-black/30"
          />
          {t("settings.openNotebookDirectly")}
        </label>

        <label className="flex items-center gap-3 text-slate-300">
          <input
            type="checkbox"
            checked={draft.stopOnExit}
            onChange={(e) => setDraft({ ...draft, stopOnExit: e.target.checked })}
            className="h-4 w-4 rounded border-white/20 bg-black/30"
          />
          {t("settings.stopOnExit")}
        </label>

        <div className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">
          {t("settings.encryptionSet")}: {draft.encryptionKey ? t("common.yes") : t("common.no")}
        </div>

        <div className="flex gap-3">
          <Button disabled={loading} onClick={() => void handleSave()}>
            {t("common.save")}
          </Button>
        </div>

        {message ? <p className="text-sm text-slate-300">{message}</p> : null}
        </Card>
      </div>
    </ScreenShell>
  );
}
