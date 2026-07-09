import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { truncateError } from "../lib/validation";
import { useI18n } from "../i18n";
import type { AppConfig } from "../types";
import { Button, Card, ScreenShell } from "../components/ui";

interface EncryptionScreenProps {
  config: AppConfig;
  onSave: (config: AppConfig, encryptionKey: string) => Promise<void>;
  onBack: () => void;
}

export function EncryptionScreen({ config, onSave, onBack }: EncryptionScreenProps) {
  const { t } = useI18n();
  const [encryptionKey, setEncryptionKey] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;

    if (!encryptionKey) {
      void api
        .generateKey()
        .then((key) => {
          if (active) {
            setEncryptionKey(key);
          }
        })
        .catch((error) => {
          if (active) {
            setMessage(truncateError(error));
          }
        });
    }

    return () => {
      active = false;
    };
  }, [encryptionKey]);

  async function handleSave() {
    if (!encryptionKey.trim()) {
      setMessage(t("encryption.keyRequired"));
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      await onSave(
        {
          ...config,
          onboardingComplete: true,
          autoStartOnLaunch: true,
          openNotebookDirectly: true,
          encryptionKeyConfigured: true,
        },
        encryptionKey.trim(),
      );
    } catch (error) {
      setMessage(truncateError(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScreenShell
      title={t("encryption.title")}
      subtitle={t("encryption.subtitle")}
      actions={
        <Button variant="secondary" onClick={onBack}>
          {t("common.back")}
        </Button>
      }
    >
      <Card className="space-y-5">
        <label className="block space-y-2">
          <span className="text-sm text-slate-300">{t("encryption.keyLabel")}</span>
          <input
            className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-sky-400"
            value={encryptionKey}
            onChange={(e) => setEncryptionKey(e.target.value)}
          />
        </label>
        <div className="flex flex-wrap gap-3">
          <Button
            variant="secondary"
            onClick={() => {
              void api
                .generateKey()
                .then(setEncryptionKey)
                .catch((error) => setMessage(truncateError(error)));
            }}
          >
            {t("encryption.generate")}
          </Button>
          <Button disabled={loading} onClick={() => void handleSave()}>
            {t("encryption.save")}
          </Button>
        </div>
        <p className="text-sm text-slate-400">
          {t("encryption.dataDir")}:{" "}
          <code className="rounded bg-white/10 px-1.5 py-0.5">{config.dataDir}</code>
        </p>
        {message ? <p className="text-sm text-rose-300">{message}</p> : null}
      </Card>
    </ScreenShell>
  );
}
