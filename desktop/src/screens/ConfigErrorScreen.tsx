import { useI18n } from "../i18n";
import { Card, ScreenShell } from "../components/ui";

interface ConfigErrorScreenProps {
  message: string;
}

export function ConfigErrorScreen({ message }: ConfigErrorScreenProps) {
  const { t } = useI18n();

  return (
    <ScreenShell title={t("configError.title")} subtitle={t("configError.subtitle")}>
      <Card className="space-y-4">
        <p className="text-sm text-rose-200">{message}</p>
        <p className="text-sm text-slate-400">{t("configError.hint")}</p>
      </Card>
    </ScreenShell>
  );
}
