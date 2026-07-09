import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useI18n } from "../i18n";
import { Button, Card, ScreenShell } from "../components/ui";

interface LogsScreenProps {
  onBack: () => void;
}

export function LogsScreen({ onBack }: LogsScreenProps) {
  const { t } = useI18n();
  const [logs, setLogs] = useState(t("logs.loading"));
  const [autoRefresh, setAutoRefresh] = useState(true);

  async function refresh() {
    try {
      const content = await api.fetchLogs(300);
      setLogs(content || t("logs.empty"));
    } catch (error) {
      setLogs(String(error));
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(timer);
  }, [autoRefresh]);

  return (
    <ScreenShell
      title={t("logs.title")}
      subtitle={t("logs.subtitle")}
      actions={
        <Button variant="secondary" onClick={onBack}>
          {t("common.back")}
        </Button>
      }
    >
      <Card className="space-y-4">
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => void refresh()}>
            {t("logs.refresh")}
          </Button>
          <Button variant="secondary" onClick={() => setAutoRefresh((value) => !value)}>
            {autoRefresh ? t("logs.autoRefreshOn") : t("logs.autoRefreshOff")}
          </Button>
        </div>
        <pre className="max-h-[60vh] overflow-auto rounded-xl bg-black/40 p-4 text-xs leading-6 text-slate-300 whitespace-pre-wrap">
          {logs}
        </pre>
      </Card>
    </ScreenShell>
  );
}
